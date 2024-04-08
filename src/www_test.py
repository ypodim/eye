import pygal 
import asyncio

import tornado.ioloop
import tornado.web
import tornado.options
import tornado.log
import tornado.locks
import tornado.websocket
import json
import datetime
import logging
import time
import os
import logging
from tornado.options import define, options

class Store():
    def __init__(self, *args, **kwargs):
        self.filename = "data.json"
        self.store = {}
        self.last_update = 0
        self.actions = []
        self.store_entries = 0

        self.logger = logging.getLogger(__name__)
        logging.basicConfig(filename='www.log', encoding='utf-8', level=logging.DEBUG)
        self.logger.info("Store started")
        # try:
        #     with open(self.filename, "r") as f:
        #         self.store = f.read()
        # except:
        #     pass

    def addAction(self, action):
        self.actions.append(action)
    def getActions(self, clear=True):
        actions = self.actions
        if clear: self.actions = []
        return actions
    def add(self, sensor_name, sensor_value, tstamp):
        
        '''
        {"sensor_name1": [
            [sensor_val1, tstamp1]],
        }
        '''
        
        self.logger.debug("%s, %s, %s" % (sensor_name, sensor_value, tstamp))

        pair = (tstamp, sensor_value)
        if sensor_name not in self.store:
            self.store[sensor_name] = []
        self.store[sensor_name].append(pair)
        self.store_entries += 1
        self.last_update = time.time()

        if self.store_entries > 24*3600:
            self.logger.info("24h window")
            with open(self.filename, "w+") as f:
                f.write(json.dumps(self.store))
                self.store = {}
                self.store_entries = 0

    def get(self):
        return dict(data=self.store, 
            entries=self.store_entries, 
            last_update="%s" % self.last_update)
    async def load_from_local_file(self):
        pass
    def get_stats(self):
        stats = {}
        for sensor in self.store:
            stats[sensor] = len(self.store[sensor])



class DataHandler(tornado.web.RequestHandler):
    def initialize(self, store):
        self.store = store
    def put(self):
        # params = self.request.path.split('/')[2:]
        data = json.loads(self.get_argument("datastr"))
        if type(data) is list:
            for item in data:
                self.store.add(item["sensor_name"], item["sensor_value"], item["tstamp"])
        else:
            print("was expecting list, got %s" % type(data), data)

        self.write(dict(actions=self.store.getActions()))
    def get(self):
        self.write(self.store.get())

class ActionHandler(tornado.web.RequestHandler):
    def initialize(self, store):
        self.store = store
    def put(self):
        action = self.get_argument("action")
        self.store.addAction(action)
        self.write(dict(result="ok", actions=self.store.getActions(clear=False)))
    def get(self):
        self.write(dict(actions=self.store.getActions(clear=False)))

class DefaultHandler(tornado.web.RequestHandler):
    def initialize(self, store):
        self.store = store
    def get(self):
        series = "temperature"

        x_format = "%d, %b %Y at %I:%M:%S %p"
        datetimeline = pygal.DateTimeLine(
            x_label_rotation=35, truncate_label=-1,
            x_value_formatter=lambda dt: dt.strftime(x_format))

        if series in self.store.store:
            datetimeline.add(series, self.store.store[series])
            path = datetimeline.render_data_uri()
        else:
            path = None

        self.render("raw.html", chart=path, path=path)

class Application(tornado.web.Application):
    def __init__(self, store):
        handlers = [
            (r"/data/.*", DataHandler, dict(store=store)),
            (r"/actions", ActionHandler, dict(store=store)),
            (r"/", DefaultHandler, dict(store=store)),
            (r'/favicon.ico', tornado.web.StaticFileHandler),
            (r'/static/', tornado.web.StaticFileHandler),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "html"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            login_url="/auth/login",
            # debug=True,
        )
        super(Application, self).__init__(handlers, **settings)


    
