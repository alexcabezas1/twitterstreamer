# coding=utf-8
import os
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from requests_oauthlib import OAuth1Session
import threading

from tornado.options import define, options

define("port", default=8080, help="run on the given port", type=int)
define("domain", default="localhost", help="serve from this domain", type=str)
define("refresh", default=3, help="time in seconds to refresh the updates", type=int)
define("debug", default=0, help="debug mode", type=int)

sockets = list()
streamer = None

# Twitter Credentials 
consumer_key = 'vcyB8y6pUXufytplpFuA'
consumer_secret = '6hWOGaMeY6nQjMECFS6FR7sQRlNC0NVsGyAoI7oxP44'
access_token = '68724842-kR2NdVzJUOWozhv4oyEOrlQLYUqHyscw6EcCILfvZ'
access_token_secret = 'vsM2Ye7GMWqQNuHQeEUWB1eHNQKfXJz5zFmUKflt1g'

def set_interval(func, sec):
    def func_wrapper():
        set_interval(func, sec)
        func()
    t = threading.Timer(sec, func_wrapper)
    t.start()
    return t

class Publisher(object):
    def __init__(self, refresh = 3):
        self.refresh = refresh
        self.updates = list()
        self.last_published = 0

    def start(self):
        set_interval(self.spread, self.refresh)

    def gossip(self, message):
        self.updates.append(message)

    def spread(self):
        global sockets
        message = ""

        if self.last_published < len(self.updates):
            message = self.updates[self.last_published]
            self.last_published += 1
        else:
            if len(self.updates) != 0:
                import random
                message = self.updates[random.randint(0,len(self.updates)-1)]

        if message != "":
            for socket in sockets:
                socket.write_message(message)


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html', domain = options.domain, port = options.port)
 
class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        global streamer, sockets
        print "WebSocket opened ..."
        sockets.append(self)
        if streamer is None:
            streamer = TwitterStreamer(Publisher(refresh = options.refresh))
            print "TwitterStreamer is running ..."
            streamer.run()
 
    def on_close(self):
        print "WebSocket closed ..."
        sockets.remove(self)

class TwitterStreamer(object):
    def __init__(self, publisher):
        self.publisher = publisher

    def run(self):
        publisher = self.publisher 
        publisher.start()

        if options.debug:
            msg = ["Rosalind Elsie Franklin (25 July 1920 – 16 April 1958)[1] was a British biophysicist and X-ray crystallographer who made critical contributions to the understanding of the fine molecular structures of DNA, RNA, viruses, coal, and graphite."
                ,"Franklin is best known for her work on the X-ray diffraction images of DNA which led to the discovery of the DNA double helix."
                ,"Unpublished drafts of her papers (written just as she was arranging to leave King's College London) show that she had independently determined the overall B-form of the DNA helix and the location of the phosphate groups on the outside of the structure."
                ,"After finishing her portion of the work on DNA, Franklin led pioneering work on the tobacco mosaic virus and the polio virus"
                ,"From early childhood, Franklin showed exceptional scholastic abilities."
                ,"Mering was an X-ray crystallographer who applied X-ray diffraction to the study of rayon and other amorphous substances, in contrast to the thousands of regular crystals that had been studied by this method for many years"]

            for message in msg:
                publisher.gossip({'text':message})
        else:
            global consumer_key, consumer_secret, access_token, access_token_secret
            twitter = OAuth1Session(consumer_key,
                                    client_secret = consumer_secret,
                                    resource_owner_key = access_token,
                                    resource_owner_secret = access_token_secret)
            #url = 'https://api.twitter.com/1.1/statuses/home_timeline.json'
            url = 'https://userstream.twitter.com/1.1/user.json?stall_warnings=true' 
            r = twitter.get(url, stream = True)
            for line in r.iter_lines():
                if line:
                    print line
                    publisher.gossip(line)


if __name__ == "__main__":
    tornado.options.parse_command_line()
    app = tornado.web.Application(
        handlers=[
            (r"/", IndexHandler),
            (r"/socket", WebSocketHandler),
            (r'/static/(.*)', tornado.web.StaticFileHandler, {"path": "%s/static" % os.getcwd()})
        ]
    )
    httpServer = tornado.httpserver.HTTPServer(app)
    httpServer.listen(options.port)
    print "Listening on port:", options.port
    tornado.ioloop.IOLoop.instance().start()
