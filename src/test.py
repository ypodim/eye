class One(object):
	def __init__(self):
		self.data = dict(s1=2)
	def __repr__(self):
		return self.data


o = One()
print(o)