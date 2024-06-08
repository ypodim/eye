
import ssl
import wifi
import socketpool
import adafruit_requests

import time
import json

import board
import adafruit_mcp9808

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

options = dict(url="http://astrapi:8888/data/")

class Sensor(object):
    def __init__(self, name="", poll_interval=1, send_interval=60, calc_avg=True):
        self.name = name
        self.instant_values_sum = 0
        self.instant_values_tot = 0
        self.last_send = 0
        self.send_interval = send_interval #seconds
        self.poll_interval = poll_interval #seconds
        self.calc_avg = calc_avg
        self.max_val = 0

        wifi.radio.connect(secrets["ssid"], secrets["password"])
        pool = socketpool.SocketPool(wifi.radio)
        self.requests = adafruit_requests.Session(pool, ssl.create_default_context())

    def send(self, sensor_name, sensor_value):
        data = dict(
            sensor_name=sensor_name, 
            sensor_value=sensor_value)

        datastr = json.dumps(data)
        try:
            response = self.requests.post(options.get("url"), data=dict(datastr=datastr))        
            print(f" | ✅ JSON 'value' Response: {response.json()}")
        except:
            print("error connecting, is astrapi running?")
         
    def add_value(self, val):
        self.max_val = max(val, self.max_val)
        self.instant_values_sum += val
        self.instant_values_tot += 1
    def get_value(self):
        value = None

        if self.calc_avg:
            value = self.instant_values_sum/self.instant_values_tot
        else:
            value = self.max_val
            self.max_val = 0

        self.instant_values_sum = 0
        self.instant_values_tot = 0
        return value

    def run(self):
        while 1:
            val = self.read_value()
            self.add_value(val)

            now = time.monotonic()
            if now - self.last_send > self.send_interval:
                value = self.get_value()

                self.send(self.name, value)
                self.last_send = now

            time.sleep(self.poll_interval)

class Thermometer(Sensor):
    def __init__(self):
        super(Thermometer, self).__init__(name="attic_thermo")
        self.i2c = board.STEMMA_I2C()
        self.thermo = adafruit_mcp9808.MCP9808(self.i2c)

    def read_value(self):
        temp_f = self.thermo.temperature * 9.0 / 5.0 + 32.0
        return temp_f


if __name__ == "__main__":
    thermo = Thermometer()
    thermo.run()

