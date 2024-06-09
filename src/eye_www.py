import pygal 
import asyncio
import tornado.ioloop
import tornado.web
import tornado.options
import tornado.websocket
import os
import json
import datetime

import random

def date_cmp(pair, threshold):
    date = pair[0]
    return time.time() - date < threshold
    # return datetime.datetime.now() - date < datetime.timedelta(seconds=threshold)


# class Manager(object):
#     def __init__(self):
#         self.sensors = []
#         self.retain_threshold = 60*60*24 #seconds
#     def set_sensors(self, sensors):
#         self.sensors = sensors
#     def action(self, action_name, action_value):
#         print("action:", action_name, action_value)
#     def get_data(self, sensor_name):
#         for sensor in self.sensors:
#             if sensor.name == sensor_name:
#                 func = lambda datalist: date_cmp(datalist, self.retain_threshold)
#                 date_tranform = lambda x: (datetime.datetime.fromtimestamp(x[0]), x[1])
#                 result = list(filter(func, sensor.get_minutes()))
#                 result = list(map(date_tranform, result))
#                 return result
#         return (0,0)

#     def stop(self):
#         for s in self.sensors:
#             s.stop()

class StatUnit:
    def __init__(self, stat_json=None):
        self.total = 0
        self.number = 0
        self.max = 0
        self.min = 0
        if stat_json: self.fromJSON(stat_json)
    def insert(self, value):
        self.total += value
        self.number += 1
        self.max = max(value, self.max)
        self.min = min(value, self.min)
    def get_val(self):
        if self.number > 0:
            return self.total/self.number
        return 0
    def toJSON(self):
        dic = dict(total=self.total, number=self.number, min=self.min, max=self.max)
        return dic
    def fromJSON(self, dic):
        self.total = dic["total"]
        self.number = dic["number"]
        self.max = dic["max"]
        self.min = dic["min"]
    def __repr__(self):
        return json.dumps(self.toJSON())


class Store(object):
    def __init__(self, name):
        self.name = name
        self._store = {}
        self.buffer = []
        self.filename = "data_%s.json" % name
        print("store for %s created" % name)

    def load(self):
        try:
            with open(self.filename, "r") as f:
                line = f.readline()
                count = 0
                while line:
                    count += 1
                    entry = line.strip().split(" ")
                    print("read line:", entry)
                    year, month, day, hour, minute, sensor_value = entry
                    now = datetime.datetime(
                        year=int(year), 
                        month=int(month), 
                        day=int(day), 
                        hour=int(hour), 
                        minute=int(minute))
                    self.insert(float(sensor_value), now=now)
                    line = f.readline()
            print("store for %s loaded from file: %s" % (self.name, count))
        except FileNotFoundError:
            print("sensor data file %s not found" % self.filename)


    def save(self, entry):
        self.buffer.append(entry)
        if len(self.buffer) < 1:
            return

        with open(self.filename, "a") as f:
            for entry in self.buffer:
                entry_str = " ".join([str(x) for x in entry])
                raw_str = "%s\n" % entry_str
                f.write(raw_str)
            self.buffer = []

    def insert(self, sensor_value, now=None):
        now = now or datetime.datetime.now()
        if now.year not in self._store: 
            self._store[now.year] = {}
        if now.month not in self._store[now.year]: 
            self._store[now.year][now.month] = {}
        if now.day not in self._store[now.year][now.month]: 
            self._store[now.year][now.month][now.day] = {}
        if now.hour not in self._store[now.year][now.month][now.day]: 
            self._store[now.year][now.month][now.day][now.hour] = {}
        # if now.minute not in self._store[now.year][now.month][now.day][now.hour]: 
        
        self._store[now.year][now.month][now.day][now.hour][now.minute] = sensor_value
        entry = [now.year, now.month, now.day, now.hour, now.minute, sensor_value]
        return entry

    def get_today(self, now=None):
        now = now or datetime.datetime.now()

        ret_list = []
        max_value = 0
        for hour in range(24):
            for minute in range(60):
                value = 0
                if hour in self._store[now.year][now.month][now.day]:
                    if minute in self._store[now.year][now.month][now.day][hour]:
                        value = self._store[now.year][now.month][now.day][hour][minute]
                        max_value = max(max_value, value)
                x = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                ret_list.append([x, value])

        if max_value > 100:
            for i, items in enumerate(ret_list):
                ret_list[i] = [items[0], 100*items[1]/max_value]
             
        return ret_list

class Manager:
    def __init__(self):
        self.sensors = {}
        self.sensor_names_filename = "data_sensor_names.json"
        self.load_sensor_names()
        
    def load_sensor_names(self):
        names = []
        try:
            with open(self.sensor_names_filename) as f:
                names = f.read().split(' ')
        except FileNotFoundError:
            print("sensor names file not found")


        for sensor_name in names:
            self.sensors[sensor_name] = Store(sensor_name)
            self.sensors[sensor_name].load()
        
    def save_sensor_names(self):
        with open(self.sensor_names_filename, "w+") as f:
            output = " ".join([name for name in self.get_sensor_names()])
            f.write(output)

    def insert(self, sensor_name, sensor_value):
        if sensor_name not in self.sensors:
            self.sensors[sensor_name] = Store(sensor_name)
            self.save_sensor_names()

        entry = self.sensors[sensor_name].insert(sensor_value)
        self.sensors[sensor_name].save(entry)
        
    def get_sensor_names(self):
        return self.sensors.keys()
    def get_sensor_data(self, sensor_name):
        # return self.sensors.get(sensor_name)
        return self.sensors[sensor_name].get_today()
    def __repr__(self):
        ret_dict = {}
        for sensor in self.sensors:
            ret_dict[sensor] = str(self.sensors[sensor])
        return json.dumps(ret_dict)

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
        sensors_to_show = self.manager.get_sensor_names()
        if self.request.arguments:
            sensors_to_show = []
            for sensor_name in self.request.arguments:
                val = self.request.arguments.get(sensor_name)
                val = val[0].decode("utf-8")
                if val == "1":
                    sensors_to_show.append(sensor_name)
                
        x_format = "%I:%M %p %Z"
        datetimeline = pygal.DateTimeLine(
            x_label_rotation=35, truncate_label=-1,
            x_value_formatter=lambda dt: dt.strftime(x_format),
            width=1500)

        for sensor_name in sensors_to_show:
            data = self.manager.get_sensor_data(sensor_name)
            datetimeline.add(sensor_name, data)
        self.set_header('Content-Type', 'application/xhtml+xml')
        self.write(datetimeline.render())

class DefaultHandler(tornado.web.RequestHandler):
    def initialize(self, manager):
        self.manager = manager
    def get(self):
        self.render("index.html")

class DataHandler(tornado.web.RequestHandler):
    def initialize(self, manager):
        self.manager = manager
    def get(self):
        response = dict(action="set", actuator="relay")
        self.write(response)
    def post(self):
        param_str = self.get_arguments("datastr")
        if param_str:
            params = json.loads(param_str[0])
            sensor_name = params.get("sensor_name")
            sensor_value = params.get("sensor_value")
            self.manager.insert(sensor_name, sensor_value)

            msg = "%s %s" % (sensor_name, sensor_value)
            StatsSocket.send_message(msg)

        self.write(dict(result="ok", action="gfy"))

class StatsSocket(tornado.websocket.WebSocketHandler):
    clients = set()
    def initialize(self, manager):
        self.manager = manager

    def open(self):
        StatsSocket.clients.add(self)

    def on_message(self, message):
        # self.write_message(u"You said: " + message)
        print("got", message)
        # self.manager.send()

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
            (r"/data/.*", DataHandler, dict(manager=manager)),
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

async def main():
    manager = Manager()
    app = Application(manager)
    app.listen(8888)
    shutdown_event = asyncio.Event()
    await shutdown_event.wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("exiting")

    
