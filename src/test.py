import json
import datetime

class StatUnit:
    def __init__(self):
        self.total = 0
        self.number = 0
        self.max = 0
        self.min = 0
    def insert(self, value):
        self.total += value
        self.number += 1
        self.max = max(value, self.max)
        self.min = min(value, self.min)
    def get_val(self):
        if self.number > 0:
            return self.total/self.number
        return 0
    def get_dict(self):
    	return dict(total=self.total, number=self.number, min=self.min, max=self.max)
    def __repr__(self):
    	return json.dumps(self.get_dict())


s = StatUnit()
s.insert(5)
s.insert(7)
print(str(s))


now = datetime.datetime.now()

print("year is", now.year)
print("year is", now.month)
print("year is", now.day)
print("year is", now.hour)
print("year is", now.minute)