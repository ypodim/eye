import pygal 

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

define("port", default=8888, help="run on the given port", type=int)

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
    def save_to_file(self, filename="data.json"):
        with open(self.filename, "w+") as f:
            f.write(json.dumps(self.store))
            self.store = {}
            self.store_entries = 0
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
            self.save_to_file()

    def get(self):
        return dict(data=self.store, 
            entries=self.store_entries, 
            last_update="%s" % self.last_update)


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
        datetimeline.add(series, self.store.store[series])

        path = datetimeline.render_data_uri()

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

async def main(shutdown_event):
    # tornado.options.parse_command_line()
    # tornado.log.enable_pretty_logging()
    # access_log = logging.getLogger('tornado.access')
    # access_log.info("starting up")

    store = Store()
    app = Application(store)
    logging.getLogger("tornado.access").propagate = False
    
    io_loop = tornado.ioloop.IOLoop.current()
    # pc = tornado.ioloop.PeriodicCallback(brain.periodic, 1000)
    # pc.start()
    app.listen(options.port)
    await shutdown_event.wait()

if __name__ == "__main__":
    shutdown_event = tornado.locks.Event()
    try:
        tornado.ioloop.IOLoop.current().run_sync(lambda: main(shutdown_event))
    except KeyboardInterrupt:
        print("time to die")
        shutdown_event.set()

