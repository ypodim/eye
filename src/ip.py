from requests import get
import json

class IPmanager(object):
	def __init__(self):
		self._ip = ""
		self.checkin()
		
	def checkin(self):
		raw = get('http://45.33.41.36:9000/insert').content.decode('utf8')
		data = json.loads(raw).get("ips")
		print(data[-1])

	def check(self):
		ip = get('https://api.ipify.org').content.decode('utf8')
		if self._ip != ip:
			self._ip = ip
			print('My new IP address is: {}'.format(ip))