import pygal 
import asyncio

import tornado.ioloop
import tornado.web
import tornado.options
import tornado.websocket
import os

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


    
