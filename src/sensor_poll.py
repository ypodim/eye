import requests
import asyncio
import time
import tornado
import json
import os
import glob
import random
import datetime
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

class Sensor(object):
    def __init__(self, name=""):
        self.name = name
        self.instant_value = 0
        self.instant_values_sum = 0
        self.instant_values_tot = 0
        self.last_datapoint = 0
        self.store = dict(minutes=[], hours=[])
        self.datapoint_interval = 60 #seconds

        self.minutes = 60*24 # last 24h in minutes
        self.hours = 24*365 # 1 year in hours
        self.minutes_buffer = []

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


            self.last_datapoint = now

        await asyncio.sleep(0.001)
        future = asyncio.create_task(self.update())
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

        # future = asyncio.create_task(self.update())

class Light(Sensor):
    def __init__(self, adc, pin):
        super(Light, self).__init__(name="light")
        self.pin = AnalogIn(adc, pin)
    async def get_measurement(self):
        self.instant_value = self.pin.value

class Microphone(Sensor):
    def __init__(self, mcp, pin):
        super(Microphone, self).__init__(name="mic")
        self.pin = AnalogIn(mcp, pin)
        self.past_values = []
        self.past_values_size = 10
    async def get_measurement(self):
        val = self.pin.value/65536
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

        await asyncio.sleep(5)

        future = asyncio.create_task(self.send())


async def main(i2c):
    
    LIGHT_PIN = 0
    MIC_PIN = 1
    sensors = []

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

    # soil_conductivity = SoilConductivity()
    # await soil_conductivity.update()
    # sensors.append(soil_conductivity)

    # temp = Temperature()
    # await temp.update()
    # sensors.append(temp)

    sensor = TestSensor()
    await sensor.update()
    sensors.append(sensor)

    manager = Manager(sensors)
    await manager.send()

    tornado.options.parse_command_line()
    tornado.log.enable_pretty_logging()

    # store = Store()
    # await store.load_from_local_file()
    
    app = Application(manager)
    logger = logging.getLogger("tornado.access")
    # logger.propagate = False

    io_loop = tornado.ioloop.IOLoop.current()
    # pc = tornado.ioloop.PeriodicCallback(brain.periodic, 1000)
    # pc.start()
    app.listen(options.port)

    shutdown_event = asyncio.Event()
    await shutdown_event.wait()
    


if __name__ == "__main__":
    # try:
    #     with board.I2C() as i2c:
    #         asyncio.run(main(i2c))
    # except KeyboardInterrupt:
    #     print("time to die")


    try:
        asyncio.run(main(None))
    except KeyboardInterrupt:
        print("time to die")









