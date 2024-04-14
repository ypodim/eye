from requests import get

class IPmanager(object):
	def __init__(self):
		self._ip = ""
		self.check()
	def check(self):
		ip = get('https://api.ipify.org').content.decode('utf8')
		if self._ip != ip:
			self._ip = ip
			print('My new IP address is: {}'.format(ip))