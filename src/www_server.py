import pygal 
import asyncio

import tornado.ioloop
import tornado.web
import tornado.options
import tornado.log
import tornado.locks
import tornado.websocket
import json
# import datetime
import logging
import time
import os
import logging
from tornado.options import define, options


# class Store():
#     def __init__(self, *args, **kwargs):
#         self.filename = "data.json"
#         self.store = {}
#         self.last_update = 0
#         self.actions = []
#         self.store_entries = 0

#         self.logger = logging.getLogger(__name__)
#         logging.basicConfig(filename='www.log', encoding='utf-8', level=logging.DEBUG)
#         self.logger.info("Store started")
#         # try:
#         #     with open(self.filename, "r") as f:
#         #         self.store = f.read()
#         # except:
#         #     pass

#     def addAction(self, action):
#         self.actions.append(action)
#     def getActions(self, clear=True):
#         actions = self.actions
#         if clear: self.actions = []
#         return actions
#     def add(self, sensor_name, sensor_value, tstamp):
        
#         '''
#         {"sensor_name1": [
#             [sensor_val1, tstamp1]],
#         }
#         '''
        
#         self.logger.debug("%s, %s, %s" % (sensor_name, sensor_value, tstamp))

#         pair = (tstamp, sensor_value)
#         if sensor_name not in self.store:
#             self.store[sensor_name] = []
#         self.store[sensor_name].append(pair)
#         self.store_entries += 1
#         self.last_update = time.time()

#         if self.store_entries > 24*3600:
#             self.logger.info("24h window")
#             with open(self.filename, "w+") as f:
#                 f.write(json.dumps(self.store))
#                 self.store = {}
#                 self.store_entries = 0

#     def get(self):
#         return dict(data=self.store, 
#             entries=self.store_entries, 
#             last_update="%s" % self.last_update)
#     async def load_from_local_file(self):
#         pass
#     def get_stats(self):
#         stats = {}
#         for sensor in self.store:
#             stats[sensor] = len(self.store[sensor])

# class DataHandler(tornado.web.RequestHandler):
#     def initialize(self, store):
#         self.store = store
#     def put(self):
#         # params = self.request.path.split('/')[2:]
#         data = json.loads(self.get_argument("datastr"))
#         if type(data) is list:
#             for item in data:
#                 self.store.add(item["sensor_name"], item["sensor_value"], item["tstamp"])
#         else:
#             print("was expecting list, got %s" % type(data), data)

#         self.write(dict(actions=self.store.getActions()))
#     def get(self):
#         self.write(self.store.get())

class ActionHandler(tornado.web.RequestHandler):
    def initialize(self, manager):
        self.manager = manager
    def put(self):
        action = self.get_argument("action")
        self.manager.addAction(action)
        self.write(dict(result="ok", actions=self.manager.getActions(clear=False)))
    def get(self):
        self.write(dict(actions=self.manager.getActions(clear=False)))

class ChartsHandler(tornado.web.RequestHandler):
    def initialize(self, manager):
        self.manager = manager
    def get(self):
        x_format = "%I:%M %p %Z"
        datetimeline = pygal.DateTimeLine(
            x_label_rotation=35, truncate_label=-1,
            x_value_formatter=lambda dt: dt.strftime(x_format))

        for sensor_name in self.manager.get_sensor_names():
            data = self.manager.get_data(sensor_name)
            datetimeline.add(sensor_name, data)
        self.set_header('Content-Type', 'application/xhtml+xml')
        self.write(datetimeline.render())

    # def get2(self):
    #     chartName = self.request.uri.split("/")[-1]

    #     charts = {}

    #     datetimeline = pygal.DateTimeLine(
    #         x_label_rotation=35, truncate_label=-1,
    #         x_value_formatter=lambda dt: dt.strftime(x_format))

    #     for series in self.manager.get_sensor_names():
    #         x_format = "%I:%M:%S %p %Z"
            
    #         data = self.manager.get_data(series)
    #         datetimeline.add(series, data)
    #         charts[series] = datetimeline.render()
    #     print(charts)
    #     self.set_header('Content-Type', 'application/xhtml+xml')

    #     if chartName not in charts:
    #         charts[chartName] = {}
            
    #     self.write(charts[chartName])


class DefaultHandler(tornado.web.RequestHandler):
    def initialize(self, manager):
        self.manager = manager
    def get(self):
        self.render("index.html")

class StatsSocket(tornado.websocket.WebSocketHandler):
    clients = set()
    def initialize(self, manager):
        self.manager = manager
    def open(self):
        StatsSocket.clients.add(self)

    def on_message(self, message):
        # self.write_message(u"You said: " + message)
        self.manager.send()

    def on_close(self):
        StatsSocket.clients.remove(self)

    @classmethod
    def send_message(cls, message: str):
        # print(f"Sending message {message} to {len(cls.clients)} client(s).")
        for client in cls.clients:
            client.write_message(message)


class Application(tornado.web.Application):
    def __init__(self, manager):
        handlers = [
            (r"/ws", StatsSocket, dict(manager=manager)),
            # (r"/data/.*", DataHandler, dict(store=store)),
            (r"/actions", ActionHandler, dict(manager=manager)),
            (r'/favicon.ico', tornado.web.StaticFileHandler),
            (r'/static/', tornado.web.StaticFileHandler),
            (r"/charts/.*", ChartsHandler, dict(manager=manager)),
            (r"/.*", DefaultHandler, dict(manager=manager)),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "html"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            login_url="/auth/login",
            debug=True,
        )
        super(Application, self).__init__(handlers, **settings)


    
