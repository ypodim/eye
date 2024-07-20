import requests

import time
import json
import os
import glob
import random
import threading

import busio
import board
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
class Urls:
    base="http://astrapi:8888"
    data="/data/"
    status="/status"

    @staticmethod
    def data_url():
        return Urls.base+Urls.data
    @staticmethod
    def status_url():
        return Urls.base+Urls.status

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
    def parse_action(self, action):
        if action == "set":
            self.set_on()
        if action == "unset":
            self.set_off()
        if action == "toggle":
            self.toggle()


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

    def send(self, sensor_name, sensor_value):
        data = dict(
            sensor_name=sensor_name, 
            sensor_value=sensor_value)

        datastr = json.dumps(data)
        try:
            r = requests.post(Urls.data_url(), params=dict(datastr=datastr))
        except:
            print("error connecting")
            data = dict(
                sensor_name="error_connecting", 
                sensor_value=1)
         
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
        self.running = 1
        while self.running:
            val = self.read_value()
            self.add_value(val)

            now = time.time()
            if now - self.last_send > self.send_interval:
                value = self.get_value()

                self.send(self.name, value)
                self.last_send = now

            time.sleep(self.poll_interval)

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
        return self.pin.value


class Microphone(Sensor):
    def __init__(self, mcp, pin):
        super(Microphone, self).__init__(name="mic", poll_interval=0.1, calc_avg=False)
        self.pin = AnalogIn(mcp, pin)
        self.past_values = []
        self.past_values_size = 10
    def read_value(self):
        self.past_values.append(self.pin.value)
        ret_val = max(self.past_values) - min(self.past_values)
        if len(self.past_values) > self.past_values_size:
            del self.past_values[0]
        return ret_val

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
    def read_value(self):
        t = adafruit_mcp9808.MCP9808(self.i2c)
        temp_f = t.temperature * 9.0 / 5.0 + 32.0
        return temp_f

class TestSensor(Sensor):
    def __init__(self):
        super(TestSensor, self).__init__(name="testSensor")
    def get_measurement(self):
        self.instant_value = random.random() * 100

class Manager(object):
    def __init__(self):
        self.i2c = board.I2C()
        self.sensors = []
        self.actuators = dict(relay=Relay(set_pin, unset_pin))
    def setup(self):
        LIGHT_PIN = 0
        MIC_PIN = 1

        adc = ADC.ADS7830(self.i2c)

        light2 = Light(adc, LIGHT_PIN)
        threading.Thread(target=light2.run).start()
        self.sensors.append(light2)

        # mic = Microphone(adc, MIC_PIN)
        # threading.Thread(target=mic.run).start()
        # self.sensors.append(mic)

        # internalTemp = InternalTemperature(self.i2c)
        # threading.Thread(target=internalTemp.run).start()
        # self.sensors.append(internalTemp)

        soil_conductivity = SoilConductivity()
        threading.Thread(target=soil_conductivity.run).start()
        self.sensors.append(soil_conductivity)

        temperature = Temperature()
        threading.Thread(target=temperature.run).start()
        self.sensors.append(temperature)
    def loop_once(self):
        
        response = None
        try:
            r = requests.get(Urls.data_url())
        except:
            print("error connecting to:", Urls.data_url())
            return

        if r.text:
            try:
                response = json.loads(r.text)
            except:
                return
            if response and "actions" in response:
                actions = response.get("actions")
                send_status = False

                for action in actions:
                    send_status = True
                    print(action)
                    if action.get("action") == "relay":
                        self.actuators["relay"].parse_action(action.get("value"))
                    if action.get("action") == "play":
                        # self.actuators["relay"].parse_action(action.get("value"))
                        pass

                if send_status:
                    relay_status = self.actuators["relay"].status
                    status = dict(entity="relay", value=relay_status)
                    r = requests.post(Urls.status_url(), json=status)

    def run(self):
        while 1:
            time.sleep(1)
            self.loop_once()
    def cleanup(self):
        print("time to die")
        self.i2c.deinit()
        for s in self.sensors:
            s.stop()


if __name__ == "__main__":
    manager = Manager()
    manager.setup()
    try:
        manager.run()
    except KeyboardInterrupt:
        manager.cleanup()