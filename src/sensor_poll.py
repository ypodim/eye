import requests
import asyncio
import time
import tornado
import json
import os
import glob
import random
import datetime
<<<<<<< HEAD
# import aiofiles

# import busio
# import board
# import digitalio
# import adafruit_rfm9x
# import adafruit_mcp9808
# import digitalio
# import pwmio
import logging
from tornado.options import define, options

# import adafruit_ads7830.ads7830 as ADC
# from adafruit_ads7830.analog_in import AnalogIn
# from adafruit_onewire.bus import OneWireBus
# from adafruit_ds18x20 import DS18X20
# from adafruit_seesaw.seesaw import Seesaw
from www_server import Application, StatsSocket

# cs = digitalio.DigitalInOut(board.D22)
# set_pin = digitalio.DigitalInOut(board.D22)
# set_pin.direction = digitalio.Direction.OUTPUT
# unset_pin = digitalio.DigitalInOut(board.D27)
# unset_pin.direction = digitalio.Direction.OUTPUT
=======
import aiofiles

import busio
import board
import digitalio
import adafruit_rfm9x
import adafruit_mcp9808
import digitalio
import pwmio
import logging
from tornado.options import define, options

import adafruit_ads7830.ads7830 as ADC
from adafruit_ads7830.analog_in import AnalogIn
from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20
from adafruit_seesaw.seesaw import Seesaw
from www_server import Application, StatsSocket
from ip import IPmanager

cs = digitalio.DigitalInOut(board.D22)
set_pin = digitalio.DigitalInOut(board.D22)
set_pin.direction = digitalio.Direction.OUTPUT
unset_pin = digitalio.DigitalInOut(board.D27)
unset_pin.direction = digitalio.Direction.OUTPUT
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba


# os.system("play /usr/share/sounds/alsa/Noise.wav")

define("port", default=8888, help="run on the given port", type=int)

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

<<<<<<< HEAD
class Sensor(object):
    def __init__(self, name=""):
=======

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
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba
        self.name = name
        self.instant_value = 0
        self.instant_values_sum = 0
        self.instant_values_tot = 0
        self.last_datapoint = 0
<<<<<<< HEAD
        self.store = dict(minutes=[], hours=[])
        self.datapoint_interval = 60 #seconds

        self.minutes = 60*24 # last 24h in minutes
        self.hours = 24*365 # 1 year in hours
        self.minutes_buffer = []

=======
        self.datapoint_interval = 60 #seconds
        self.filename = "%s.json" % name
        self.load(self.filename)
    
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba
    async def get_measurement(self):
        raise NotImplementedError
    async def update(self):
        await self.get_measurement()
        self.instant_values_sum += self.instant_value
        self.instant_values_tot += 1

        now = time.time()
        if now - self.last_datapoint > self.datapoint_interval:
            if self.instant_values_tot > 0:
                value = self.instant_values_sum/self.instant_values_tot
                self.instant_values_sum = 0
                self.instant_values_tot = 0

<<<<<<< HEAD
                self.store["minutes"].append((now, value))
                if len(self.store["minutes"]) > self.minutes:
                    del self.store["minutes"][0]

                self.minutes_buffer.append(value)
                if len(self.minutes_buffer) >= 60:
                    hour_average = sum(self.minutes_buffer) / len(self.minutes_buffer)
                    self.store["hours"].append((now, hour_average))
                    self.minutes_buffer = []

                    if len(self.store["hours"]) > self.hours:
                        del self.store["hours"][0]


=======
            self.insert(value)
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba
            self.last_datapoint = now

        await asyncio.sleep(0.001)
        future = asyncio.create_task(self.update())
<<<<<<< HEAD
    def get_stats(self):
        stats = {}
        stats["store_size"] = len(self.store["minutes"])
        stats["inst_total"] = self.instant_values_tot
        stats["inst_sum"] = self.instant_values_sum
        return stats
    def get(self):
        if self.store:
            return int(1000*self.store[-1][0])/1000
        else:
            return None
=======


    def get_stats(self):
        stats = {}
        stats["store_size"] = len(self.get_minutes())
        stats["inst_total"] = self.instant_values_tot
        stats["inst_sum"] = self.instant_values_sum
        return stats
    # def get(self):
    #     if self.store:
    #         return int(1000*self.store[-1][0])/1000
    #     else:
    #         return None
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba

class Temperature(Sensor):
    def __init__(self):
        super(Temperature, self).__init__(name="temperature")
        os.system('modprobe w1-gpio')
        os.system('modprobe w1-therm')
         
        base_dir = '/sys/bus/w1/devices/'
        # Get all the filenames begin with 28 in the path base_dir.
        self.device_folder = glob.glob(base_dir + '28*')[0]
        
    def read_temp_raw2(self):
        device_file = self.device_folder + '/w1_slave'
        f = open(device_file, 'r')
        lines = f.readlines()
        f.close()
        return lines
 
    async def read_temp_raw(self):
        device_file = self.device_folder + '/w1_slave'
        async with aiofiles.open(device_file, mode='r') as f:
            lines = await f.readlines()
        return lines

    async def get_measurement(self):
        lines = await self.read_temp_raw()
        # Analyze if the last 3 characters are 'YES'.
        try:
            while lines[0].strip()[-3:] != 'YES':
                # time.sleep(0.001)
                lines = await self.read_temp_raw()
        except IndexError:
            # print("************* oops, bad file")
            return
            
        # Find the index of 't=' in a string.
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            # Read the temperature .
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            temp_f = temp_c * 9.0 / 5.0 + 32.0
            self.instant_value = temp_f
            # self.instant_values_tot += 1

<<<<<<< HEAD
        # future = asyncio.create_task(self.update())

=======
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba
class Light(Sensor):
    def __init__(self, adc, pin):
        super(Light, self).__init__(name="light")
        self.pin = AnalogIn(adc, pin)
    async def get_measurement(self):
<<<<<<< HEAD
        self.instant_value = self.pin.value
=======
        max_value = 65536
        self.instant_value = 100*self.pin.value/max_value
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba

class Microphone(Sensor):
    def __init__(self, mcp, pin):
        super(Microphone, self).__init__(name="mic")
        self.pin = AnalogIn(mcp, pin)
        self.past_values = []
        self.past_values_size = 10
    async def get_measurement(self):
<<<<<<< HEAD
        val = self.pin.value/65536
=======
        val = 100.0*self.pin.value/65536
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba
        self.past_values.append(val)
        if len(self.past_values) > self.past_values_size:
            del self.past_values[0]
        self.instant_value = max(self.past_values) - min(self.past_values)

class SoilConductivity(Sensor):
    def __init__(self):
        super(SoilConductivity, self).__init__(name="soil_moisture")
        i2c_bus = board.I2C()
        self.pin = Seesaw(i2c_bus, addr=0x36)
    async def get_measurement(self):
        try:
            soil_conduct = self.pin.moisture_read()
            soil_temp = 32 + self.pin.get_temp() * 9 / 5
            self.instant_value = soil_conduct
        except:
            soil_conduct = None
            soil_temp = None
            self.error = "error reading I2C from soil sensor" 

class InternalTemperature(Sensor):
    def __init__(self, i2c):
        super(InternalTemperature, self).__init__(name="internaltemp")
        self.i2c = i2c
    async def get_measurement(self):
        t = adafruit_mcp9808.MCP9808(i2c)
        temp_f = t.temperature * 9.0 / 5.0 + 32.0
        self.instant_value = temp_f

class TestSensor(Sensor):
    def __init__(self):
        super(TestSensor, self).__init__(name="testSensor")
    async def get_measurement(self):
        self.instant_value = random.random() * 100


def date_cmp(pair, threshold):
    date = pair[0]
    return time.time() - date < threshold
<<<<<<< HEAD
=======
    # return datetime.datetime.now() - date < datetime.timedelta(seconds=threshold)
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba

class Manager(object):
    def __init__(self, sensors):
        self.sensors = sensors
        self.retain_threshold = 60*60*24 #seconds
        # self.feeder = Feeder(actions_clb=self.action)
        # self.buffer = []
    def action(self, action_name, action_value):
        print("action:", action_name, action_value)
    def get_sensor_names(self):
        return [sensor.name for sensor in self.sensors]
    def get_data(self, sensor_name):
        for sensor in self.sensors:
            if sensor.name == sensor_name:
<<<<<<< HEAD
                return list(filter(
                    lambda datalist: date_cmp(datalist, self.retain_threshold), 
                    sensor.store["minutes"]))
        return (0,0)

    async def send(self):
        for s in self.sensors:
            data = dict(
                sensor_name=s.name, 
                sensor_value=s.store["minutes"][-1][1], 
                sensor_stats=s.get_stats(),
                tstamp=time.time())
            # self.buffer.append(data)
=======
                func = lambda datalist: date_cmp(datalist, self.retain_threshold)
                date_tranform = lambda x: (datetime.datetime.fromtimestamp(x[0]), x[1])
                result = list(filter(func, sensor.get_minutes()))
                result = list(map(date_tranform, result))
                return result
        return (0,0)

    def loop(self):
        self.send()
        asyncio.get_event_loop().call_later(3, self.loop)

    def save_to_file(self):
        for sensor in self.sensors:
            sensor.save(sensor.filename)
        asyncio.get_event_loop().call_later(30, self.save_to_file)

    def send(self):
        for s in self.sensors:
            data = dict(
                sensor_name=s.name, 
                sensor_value=s.get_last_value(), 
                sensor_stats=s.get_stats(),
                tstamp=time.time())
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba
            StatsSocket.send_message(data)

        # if len(self.buffer) > 10:
        #     datastr = json.dumps(self.buffer)
        #     url = "http://astrapi:8888/data/"
        #     try:
        #         requests.put(url, params=dict(datastr=datastr))
        #         self.buffer = []
        #         print("success!")
        #     except:
        #         print("error connecting")
        #         data = dict(
        #             sensor_name="error_connecting", 
        #             sensor_value=1, 
        #             tstamp=time.time())
        #         self.buffer.append(data)

<<<<<<< HEAD
        await asyncio.sleep(5)

        future = asyncio.create_task(self.send())


=======
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba
async def main(i2c):
    
    LIGHT_PIN = 0
    MIC_PIN = 1
    sensors = []

<<<<<<< HEAD
    # adc = ADC.ADS7830(i2c)
    # light = Light(adc, LIGHT_PIN)
    # await light.update()
    # sensors.append(light)

    # mic = Microphone(adc, MIC_PIN)
    # await mic.update()
    # sensors.append(mic)

    # internalTemp = InternalTemperature(i2c)
    # await internalTemp.update()
    # sensors.append(internalTemp)
=======
    adc = ADC.ADS7830(i2c)
    light = Light(adc, LIGHT_PIN)
    await light.update()
    sensors.append(light)

    mic = Microphone(adc, MIC_PIN)
    await mic.update()
    sensors.append(mic)

    internalTemp = InternalTemperature(i2c)
    await internalTemp.update()
    sensors.append(internalTemp)
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba

    # soil_conductivity = SoilConductivity()
    # await soil_conductivity.update()
    # sensors.append(soil_conductivity)

<<<<<<< HEAD
    # temp = Temperature()
    # await temp.update()
    # sensors.append(temp)

    sensor = TestSensor()
    await sensor.update()
    sensors.append(sensor)

    manager = Manager(sensors)
    await manager.send()
=======
    temp = Temperature()
    await temp.update()
    sensors.append(temp)

    # sensor = TestSensor()
    # await sensor.update()
    # sensors.append(sensor)

    manager = Manager(sensors)
    manager.loop()
    asyncio.get_event_loop().call_later(30, manager.save_to_file)

    ipmanager = IPmanager()
    asyncio.get_event_loop().call_later(60, ipmanager.checkin)
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba

    tornado.options.parse_command_line()
    tornado.log.enable_pretty_logging()

<<<<<<< HEAD
    # store = Store()
    # await store.load_from_local_file()
    
=======
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba
    app = Application(manager)
    logger = logging.getLogger("tornado.access")
    # logger.propagate = False

    io_loop = tornado.ioloop.IOLoop.current()
<<<<<<< HEAD
    # pc = tornado.ioloop.PeriodicCallback(brain.periodic, 1000)
    # pc.start()
    app.listen(options.port)

=======
    app.listen(options.port)
    
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba
    shutdown_event = asyncio.Event()
    await shutdown_event.wait()
    


if __name__ == "__main__":
<<<<<<< HEAD
    # try:
    #     with board.I2C() as i2c:
    #         asyncio.run(main(i2c))
    # except KeyboardInterrupt:
    #     print("time to die")


    try:
        asyncio.run(main(None))
=======
    try:
        with board.I2C() as i2c:
            asyncio.run(main(i2c))
>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba
    except KeyboardInterrupt:
        print("time to die")


<<<<<<< HEAD
=======
    # try:
    #     asyncio.run(main(None))
    # except KeyboardInterrupt:
    #     print("time to die")


>>>>>>> 2a19435aeeab7c9029c782f4fc456b65e48780ba







