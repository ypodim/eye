import asyncio
import time
import tornado
import json
import os
import glob
import aiofiles

import busio
import board
import digitalio
import adafruit_rfm9x
import adafruit_mcp9808
import digitalio
import pwmio

import adafruit_ads7830.ads7830 as ADC
from adafruit_ads7830.analog_in import AnalogIn
# import adafruit_mcp3xxx.mcp3008 as MCP
# from adafruit_mcp3xxx.analog_in import AnalogIn
from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20
from adafruit_seesaw.seesaw import Seesaw
from cloud_io import Feeder

# spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
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

class Sensor(object):
    def __init__(self, name=""):
        self.name = name
        self.instant_value = 0
        self.instatnt_values_sum = 0
        self.instatnt_values_tot = 0
    async def get_measurement(self):
        raise NotImplementedError
    async def update(self):
        await self.get_measurement()
        self.instatnt_values_sum += self.instant_value
        self.instatnt_values_tot += 1
        # print(self.name, self.instatnt_values_sum)
        future = asyncio.create_task(self.update())
    async def test(self):
        print(self.get())
        await asyncio.sleep(1)
        future = asyncio.create_task(self.test())
    def get(self):
        if self.instatnt_values_tot:
            value = self.instatnt_values_sum/self.instatnt_values_tot
            self.instatnt_values_sum = 0
            self.instatnt_values_tot = 0
            return value
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
            pass
        # Find the index of 't=' in a string.
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            # Read the temperature .
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            temp_f = temp_c * 9.0 / 5.0 + 32.0
            self.instant_value = temp_f
            # self.instatnt_values_tot += 1

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

class Manager(object):
    def __init__(self, sensors):
        self.sensors = sensors
        self.feeder = Feeder(actions_clb=self.action)
    def action(self, action_name, action_value):
        print("action:", action_name, action_value)
    async def send(self):
        for s in self.sensors:
            self.feeder.publish(s.name, s.get())
            await asyncio.sleep(2)

        future = asyncio.create_task(self.send()) 

async def main():
    LIGHT_PIN = 0

    i2c = board.I2C()
    adc = ADC.ADS7830(i2c)

    # soil_conductivity = SoilConductivity()
    # await soil_conductivity.update()

    # temp = Temperature()
    # await temp.update()

    light = Light(adc, LIGHT_PIN)
    await light.update()

    # mic = Microphone(mcp, MCP.P1)
    # await mic.update()

    # sensors = [temp, light, mic, soil_conductivity]
    sensors = [light]
    sender = Manager(sensors)
    await sender.send()

    await asyncio.Event().wait()


async def test():
    soil_conductivity = SoilConductivity()
    await soil_conductivity.update()
    sensors = [soil_conductivity]
    sender = Manager(sensors)
    await sender.send()

    try:
        await asyncio.Event().wait()
    except:
        print("bye")

def test_relay():
    r = Relay(set_pin, unset_pin)
    while 1:
        r.toggle()
        time.sleep(1)

def test_internal_therm():
    with board.I2C() as i2c:
        t = adafruit_mcp9808.MCP9808(i2c)

        # Finally, read the temperature property and print it out
        print(t.temperature)


async def testADC():
    soil_conductivity = SoilConductivity()
    await soil_conductivity.update()

    while 1:
        await soil_conductivity.update()
        print(soil_conductivity.get())
        time.sleep(0.01)

    i2c = board.I2C()
    adc = ADC.ADS7830(i2c)
    chan = AnalogIn(adc, 0)

    while True:
        print(f"ADC channel 0 = {chan.value}")
        time.sleep(0.1)

    await asyncio.Event().wait()

if __name__=="__main__":
    try:
        test_internal_therm()
        # asyncio.run(main())
        # asyncio.run(testADC())
    except KeyboardInterrupt:
        print("exiting")





