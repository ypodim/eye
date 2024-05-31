import requests

import time
import json
import os
import glob
import random
import datetime
import threading

import busio
import board
import digitalio
import adafruit_mcp9808
import digitalio
import pwmio

import adafruit_ads7830.ads7830 as ADC
from adafruit_ads7830.analog_in import AnalogIn
from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20
from adafruit_seesaw.seesaw import Seesaw

cs = digitalio.DigitalInOut(board.D22)
set_pin = digitalio.DigitalInOut(board.D22)
set_pin.direction = digitalio.Direction.OUTPUT
unset_pin = digitalio.DigitalInOut(board.D27)
unset_pin.direction = digitalio.Direction.OUTPUT


# os.system("play /usr/share/sounds/alsa/Noise.wav")

class Relay():
    def __init__(self, set_pin, unset_pin, name="relay"):
        self.set_pin = set_pin
        self.unset_pin = unset_pin
        self.status = None
    def set_on(self):
        self.set_pin.value = True
        time.sleep(0.015)
        self.set_pin.value = False
        self.status = True
    def set_off(self):
        self.unset_pin.value = True
        time.sleep(0.015)
        self.unset_pin.value = False
        self.status = False
    def toggle(self):
        if self.status is None:
            self.set_on()
        if self.status:
            self.set_off()
        else:
            self.set_on()


class Store(object):
    def __init__(self):
        self._store = dict(minutes=[], hours=[])
        self.minutes = 60*24 # last 24h in minutes
        self.hours = 24*365 # 1 year in hours
        self.minutes_buffer = []
    def load(self, filename):
        try:
            with open(filename, "r") as f:
                raw_data = f.read()
                self._store = json.loads(raw_data)
        except FileNotFoundError:
            print("sensor data file %s not found" % filename)
    def save(self, filename):
        with open(filename, "w+") as f:
            raw_data = json.dumps(self._store)
            f.write(raw_data)
    def insert(self, value):
        now = time.time()
        self._store["minutes"].append((now, value))
        if len(self._store["minutes"]) > self.minutes:
            del self._store["minutes"][0]

        self.minutes_buffer.append(value)
        if len(self.minutes_buffer) >= 60:
            hour_average = sum(self.minutes_buffer) / len(self.minutes_buffer)
            self.minutes_buffer = []

            self._store["hours"].append((now, hour_average))
            if len(self._store["hours"]) > self.hours:
                del self._store["hours"][0]
    def get_last_value(self):
        return self._store["minutes"][-1][1]
    def get_minutes(self):
        return self._store["minutes"]

class Sensor(Store):
    def __init__(self, name=""):
        Store.__init__(self)
        self.name = name
        self.instant_value = 0
        self.instant_values_sum = 0
        self.instant_values_tot = 0
        self.last_datapoint = 0
        self.datapoint_interval = 60 #seconds
        self.filename = "%s.json" % name
        self.load(self.filename)
    
    def get_measurement(self):
        raise NotImplementedError
    def update(self):
        self.get_measurement()
        self.instant_values_sum += self.instant_value
        self.instant_values_tot += 1

        now = time.time()
        if now - self.last_datapoint > self.datapoint_interval:
            if self.instant_values_tot > 0:
                value = self.instant_values_sum/self.instant_values_tot
                self.instant_values_sum = 0
                self.instant_values_tot = 0

            self.insert(value)
            self.last_datapoint = now

        # future = asyncio.create_task(self.update())

    def get_stats(self):
        stats = {}
        stats["store_size"] = len(self.get_minutes())
        stats["inst_total"] = self.instant_values_tot
        stats["inst_sum"] = self.instant_values_sum
        return stats
        
    def send(self, sensor_name, sensor_value):
        print(sensor_name, sensor_value)
        return
        data = dict(
            sensor_name=sensor_name, 
            sensor_value=sensor_value, 
            # sensor_stats=s.get_stats(),
            tstamp=time.time())

        datastr = json.dumps(data)
        url = "http://astrapi:8888/data/"
        try:
            requests.put(url, params=dict(datastr=datastr))
            print("success!")
        except:
            print("error connecting")
            data = dict(
                sensor_name="error_connecting", 
                sensor_value=1, 
                tstamp=time.time())
         
    def run(self):
        self.running = 1
        while self.running:
            val = self.read_value()
            self.send(self.name, val)
            time.sleep(1)
    def stop(self):
        self.running = 0

class Temperature(Sensor):
    def __init__(self):
        super(Temperature, self).__init__(name="temperature")
        os.system('modprobe w1-gpio')
        os.system('modprobe w1-therm')
        base_dir = '/sys/bus/w1/devices/'
        # Get all the filenames begin with 28 in the path base_dir.
        self.device_folder = glob.glob(base_dir + '28*')[0]
    
    def read_value(self):
        device_file = self.device_folder + '/w1_slave'
        f = open(device_file, 'r')
        lines = f.readlines()
        f.close()

        if lines[0].strip()[-3:] != 'YES':
            print("bad temp file", lines)
            return None

        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            # Read the temperature .
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            temp_f = temp_c * 9.0 / 5.0 + 32.0

        return temp_f


class Light(Sensor):
    def __init__(self, adc, pin):
        super(Light, self).__init__(name="light")
        self.pin = AnalogIn(adc, pin)
    def read_value(self):
        max_value = 65536
        # self.instant_value = 100*self.pin.value/max_value
        self.instant_value = self.pin.value
        # self.send("light2", self.pin.value)
        return self.pin.value


class Microphone(Sensor):
    def __init__(self, mcp, pin):
        super(Microphone, self).__init__(name="mic")
        self.pin = AnalogIn(mcp, pin)
        self.past_values = []
        self.past_values_size = 10
    def get_measurement(self):
        val = 100.0*self.pin.value/65536
        self.past_values.append(val)
        if len(self.past_values) > self.past_values_size:
            del self.past_values[0]
        self.instant_value = max(self.past_values) - min(self.past_values)

class SoilConductivity(Sensor):
    def __init__(self):
        super(SoilConductivity, self).__init__(name="soil_moisture")
        i2c_bus = board.I2C()
        self.pin = Seesaw(i2c_bus, addr=0x36)
    def read_value(self):
        try:
            soil_conduct = self.pin.moisture_read()
            soil_temp = 32 + self.pin.get_temp() * 9 / 5
            self.instant_value = soil_conduct
        except:
            soil_conduct = None
            soil_temp = None
            self.error = "error reading I2C from soil sensor" 

        return soil_conduct

class InternalTemperature(Sensor):
    def __init__(self, i2c):
        super(InternalTemperature, self).__init__(name="internaltemp")
        self.i2c = i2c
    def get_measurement(self):
        t = adafruit_mcp9808.MCP9808(i2c)
        temp_f = t.temperature * 9.0 / 5.0 + 32.0
        self.instant_value = temp_f

class TestSensor(Sensor):
    def __init__(self):
        super(TestSensor, self).__init__(name="testSensor")
    def get_measurement(self):
        self.instant_value = random.random() * 100


def date_cmp(pair, threshold):
    date = pair[0]
    return time.time() - date < threshold
    # return datetime.datetime.now() - date < datetime.timedelta(seconds=threshold)

class Manager(object):
    def __init__(self):
        self.sensors = []
        self.retain_threshold = 60*60*24 #seconds
        # self.feeder = Feeder(actions_clb=self.action)
        # self.buffer = []
    def set_sensors(self, sensors):
        self.sensors = sensors
    def action(self, action_name, action_value):
        print("action:", action_name, action_value)
    def get_sensor_names(self):
        return [sensor.name for sensor in self.sensors]
    def get_data(self, sensor_name):
        for sensor in self.sensors:
            if sensor.name == sensor_name:
                func = lambda datalist: date_cmp(datalist, self.retain_threshold)
                date_tranform = lambda x: (datetime.datetime.fromtimestamp(x[0]), x[1])
                result = list(filter(func, sensor.get_minutes()))
                result = list(map(date_tranform, result))
                return result
        return (0,0)

    def save_to_file(self):
        for sensor in self.sensors:
            sensor.save(sensor.filename)
        # asyncio.get_event_loop().call_later(30, self.save_to_file)

    def stop(self):
        for s in self.sensors:
            s.stop()



if __name__ == "__main__":
    manager = Manager()
    try:
        with board.I2C() as i2c:
            LIGHT_PIN = 0
            LIGHT_PIN2 = 2
            MIC_PIN = 1
            sensors = []

            adc = ADC.ADS7830(i2c)

            # light = Light(adc, LIGHT_PIN)
            # light.update()
            # sensors.append(light)

            light2 = Light(adc, LIGHT_PIN2)
            threading.Thread(target=light2.run).start()
            sensors.append(light2)

            # mic = Microphone(adc, MIC_PIN)
            # mic.update()
            # sensors.append(mic)

            # internalTemp = InternalTemperature(i2c)
            # internalTemp.update()
            # sensors.append(internalTemp)

            soil_conductivity = SoilConductivity()
            threading.Thread(target=soil_conductivity.run).start()
            sensors.append(soil_conductivity)

            # temp = Temperature()
            # temp.update()
            # sensors.append(temp)
            temperature = Temperature()
            threading.Thread(target=temperature.run).start()
            sensors.append(temperature)

            # sensor = TestSensor()
            # await sensor.update()
            # sensors.append(sensor)
            manager.set_sensors(sensors)
            
            while 1:
                time.sleep(1)

    except KeyboardInterrupt:
        print("time to die")
        manager.stop()



