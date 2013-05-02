#!/usr/bin/python
 # vim: set ts=2 expandtab:
"""
Module: ircserver
Desc:
Author: John O'Neil
Email:

"""
#!/usr/bin/python
 
import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.iostream
import socket


class MainHandler(tornado.web.RequestHandler):
	def get(self):
		self.render("main.html")

class WebSocketHandler(tornado.websocket.WebSocketHandler):
  #def initialize(self, stream):
    #print 'initialize called'

  def on_connect(self):
    nick = 'nick'
    user = 'user'
    pw = 'pw'
    self.stream.write('NICK '+ nick + '\r\nUSER ' + user + '\r\nPASS ' + pw +'\r\n')
    self.stream.read_until('\r\n', self.on_line)

  def on_line(self, data):
    self.write_message(u"MSG: " + data)
    self.stream.read_until('\r\n', self.on_line)

  def on_stream_close():
    print 'socket closed'

  def open(self):
    print "WebSocket opened"
    self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    self.stream = tornado.iostream.IOStream(self.s)
    self.stream.connect(("192.168.1.6", 6660), self.on_connect)

  def on_message(self, message):
    self.write_message(u"Echo: " + message)
  def on_close(self):
    print 'websocket close'
 

def main():
  application = tornado.web.Application([
      (r"/", MainHandler),
      (r"/websocket", WebSocketHandler),
  ])
  application.listen(8888)
  tornado.ioloop.IOLoop.instance().start() 
 
if __name__ == "__main__":
  main()
	
