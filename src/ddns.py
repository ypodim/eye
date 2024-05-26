import datetime 
import asyncio
import tornado.web

class ResolveHandler(tornado.web.RequestHandler):
    def initialize(self, store):
        self.store = store
    def get(self):
        response = "oops"
        if len(self.store["ips"]):
            response = "http://%s:5433/" % self.store["ips"][-1][0]
        
        self.write(response)

class DefaultHandler(tornado.web.RequestHandler):
    def initialize(self, store):
        self.store = store
        
    def save(self, ip):
        if len(self.store["ips"]):
            last_ip = self.store["ips"][-1][0]
            if ip == last_ip:
                return
        pair = (ip, datetime.datetime.now().isoformat(' '))
        self.store["ips"].append(pair)

    def get(self):
        path = list(filter(lambda x: len(x)>0, self.request.uri.split("/")))
        if path:
            host = self.request.remote_ip
            self.save(host)
        
        self.write(self.store)

class Application(tornado.web.Application):
    def __init__(self, store):
        handlers = [
            (r"/skatoules", ResolveHandler, dict(store=store)),
            (r"/.*", DefaultHandler, dict(store=store)),
        ]
        settings = dict(
            debug=True,
        )
        super(Application, self).__init__(handlers, **settings)

async def main():
    store = dict(ips=[])
    app = Application(store)
    app.listen(9000)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())