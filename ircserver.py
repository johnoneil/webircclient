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
import string
import json
import time
import datetime
import calendar


class IRCMessage(object):
  def __init__(self,prefix, command, args):
    self.prefix = prefix
    self.command = command
    self.args = args
    self.gmt = calendar.timegm(time.gmtime())
    self.friendly_time = time.strftime('%H:%M:%S')
    if(self.prefix is not None and self.prefix.find('!') != -1):
      (self.nick, self.host) = string.split(prefix,'!',maxsplit=1)
    else:
      self.nick = ''
      self.host = ''

class IRCClient:
  def ProcessServerMessage(self, msg):
    #the IRC message (from server) will begin with either a user ID or
    #a command. If the first space delimited word in the message begins with ':'
    #then it's a user ID, and command is second. If not, it's a command
    (prefix, payload) = string.split(msg,maxsplit=1)
    if( prefix.startswith(":") ):
      pass
    else:
      if(prefix.upper() == 'PING'):
        print 'Processing PING msg for ' + payload
        return 'PONG ' + payload
    return None

  def ParseMessage(self, msg):
    prefix = ''
    trailing = []
    if msg[0] == ':':
        prefix, msg = msg[1:].split(' ', 1)
    if msg.find(' :') != -1:
        msg, trailing = msg.split(' :', 1)
        args = msg.split()
        args.append(trailing)
    else:
        args = msg.split()
    command = args.pop(0).upper().strip()
    return IRCMessage(prefix, command, args)

  def ProcessClientCommand(self, msg):
    if msg.startswith('/'):
      return msg[1:].strip() + '\r\n'
    else:
      #TODO: send message to current channel
      pass

class MainHandler(tornado.web.RequestHandler):
	def get(self):
		self.render("main.html")

class WebSocketHandler(tornado.websocket.WebSocketHandler):
  def initialize(self):
    print 'initialize called'
    self.IRCClient = IRCClient()

  def on_connect(self):
    self.stream.read_until('\r\n', self.on_line)

  def on_line(self, data):
    ircMessage = self.IRCClient.ParseMessage(data.strip())
    print ircMessage.command
    if ircMessage.command == 'PRIVMSG':
      json_data = json.dumps(vars(ircMessage),sort_keys=True, indent=4)
      print(json_data)
      self.write_message(json_data)
    #sometimes respond to server messages without involving the client (PING msg)
    response = self.IRCClient.ProcessServerMessage(data)
    if response is not None:
      self.stream.write(response)
    self.stream.read_until('\r\n', self.on_line)

  def on_stream_close():
    print 'socket closed'

  def open(self):
    print "WebSocket opened"
    self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    self.stream = tornado.iostream.IOStream(self.s)
    self.stream.connect(("192.168.1.6", 6660), self.on_connect)

  def on_message(self, message):
    cmd = self.IRCClient.ProcessClientCommand(message)
    if cmd is not None:
      print 'sending command ' + cmd + ' to host'
      self.stream.write(str(cmd))

  def on_close(self):
    print 'websocket close'
    self.stream.close()
 

def main():
  application = tornado.web.Application([
      (r"/", MainHandler),
      (r"/websocket", WebSocketHandler),
  ])
  application.listen(8888)
  tornado.ioloop.IOLoop.instance().start() 
 
if __name__ == "__main__":
  main()
	
