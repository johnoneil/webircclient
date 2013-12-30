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
import os
import re
import argparse

class IRC:
  Symbols = {
    u'\u0002':u'IRCBold', 
    u'\u001f':u'IRCUnderline', 
    u'\u001d':u'IRCItalic', 
    u'\u0012':u'IRCReverseColor', 
    u'\u000300':u'IRCWhite', 
    u'\u000301':u'IRCBlack', 
    u'\u000302':u'IRCDarkBlue', 
    u'\u000303':u'IRCDarkGreen', 
    u'\u000304':u'IRCLightRed', 
    u'\u000305':u'IRCDarkRed', 
    u'\u000306':u'IRCMagenta', 
    u'\u000307':u'IRCOrange', 
    u'\u000308':u'IRCYellow', 
    u'\u000309':u'IRCLightGreen', 
    u'\u000310':u'IRCCyan', 
    u'\u000311':u'IRCLightCyan', 
    u'\u000312':u'IRCLightBlue', 
    u'\u000313':u'IRCLightMagenta', 
    u'\u000314':u'IRCGray', 
    u'\u000315':u'IRCLightGray'
  }
  Commands = {
    u'TOPIC' : u'332',
    u'JOIN' : u'JOIN',
    u'PRIVMSG' : u'PRIVMSG',
    u'QUIT' : u'QUIT', 
  }

  @staticmethod
  def FindNextMarkup(line):
    first_hit = -1
    key_hit = ''
    for key in IRC.Symbols.iterkeys():
      #print 'looking for key ' + key + 'in string ' + line
      index = line.find(key)
      #print 'key found at index ' + str(index) 
      if index >= 0:
        #print 'found key ' + key
        if first_hit < 0:
          first_hit = index
          key_hit = key
        elif index < first_hit:
          first_hit = index
          key_hit = key
    #print 'FindNextMarkup returning ' + str(first_hit) + ' key ' + key_hit
    return (first_hit,key_hit)
    
  @staticmethod
  def MarkupToHTML(line):
    span_class_list = []
    while True:
      (first_hit,key_hit) = IRC.FindNextMarkup(line)
      if first_hit < 0 and len(span_class_list) == 0 :
        break;
      if first_hit < 0 and len(span_class_list) > 0:
        line = line + '</span>'
        break;
      value_hit = IRC.Symbols[key_hit]
      if( value_hit in span_class_list ):
        span_class_list.remove(value_hit)
      else:
        span_class_list.append(value_hit)
      if(len(span_class_list) > 0):
        span_classes = ''
        for c in span_class_list:
          span_classes = span_classes + " " + c 
        line = line.replace(key_hit,'</span><span class="' + span_classes +'">',1)
      else:
        line = line.replace(key_hit,'</span>',1)
    return line

class IRCMessage(object):
  message_id = 0
  @staticmethod
  def NextMessageID():
    IRCMessage.message_id = IRCMessage.message_id + 1
    return IRCMessage.message_id
  def __init__(self,prefix, command, args):
    self.prefix = prefix
    self.command = command
    self.args = args
    self.gmt = calendar.timegm(time.gmtime())
    self.friendly_time = time.strftime(u'%H:%M:%S')
    self.channel = ''
    self.chat = ''
    self.message_id = IRCMessage.NextMessageID()
    if(len(args)>0):
      self.channel = args[0]
    if(len(args)>1):
      self.chat = args[1]
    if(self.prefix is not None and self.prefix.find('!') != -1):
      (self.nick, self.host) = string.split(prefix,'!',maxsplit=1)
    else:
      self.nick = ''
      self.host = ''
    if self.command == u'QUIT':
      #quit messages have no channel info
      self.channel = u'HOME'
      self.chat = self.nick + u' has quit: ' + self.args[0]
      self.nick = u'<span class="IRCRed"><--</span>'
    elif self.command == u'JOIN':
      self.chat = self.nick + u' has joined ' + self.channel
      self.nick = u'<span class="IRCGreen">--></span>'
    elif self.command == u'332' or self.command == u'TOPIC':
      self.channel = self.args[1]
      self.nick = self.args[0]
      self.chat = self.args[2]

class Nick:
  def __init__(self, name):
    self.props = ''
    self.op = ''
    self.name = name

class Channel:
  def __init__(self,name, buffer_length=50):
    self.name = name
    self.nicks = []
    self.topic = ''
    self.topic_info = ''
    self.buffer = []
    self.buffer_length = buffer_length
  def Nicks(self, nicks):
    self.nicks.append(nicks)
  def Join(self, nick, msg):
    if(nick in self.nicks):
      return False
    else:
      self.nicks.append( Nick(nick) )
      return True
  def Quit(self, nick, msg=''):
    if(nick in self.nicks):
      self.nicks.remove(nick)
      return True
    else:
      return False
  def Topic(self, topic):
    if(topic != self.topic):
      self.topic = topic
      return (True, self.topic)
    else:
      return (False, self.topic)
  def TopicInfo(self, info):
    if(self.topic_info != info):
      self.topic_info = info
      return (True, self.topic_info)
    else:
      return (False, self.topic_info)
  def Privmsg(self, message):
    self.buffer.append(message)
    if(len(self.buffer) > self.buffer_length):
      self.buffer.pop(0)
  
    
class IRCClient:
  def __init__(self):
    self.channels = {}
    self.message_handlers = {
      u'PING' : self.OnPing,
    }

  def OnPing(self, msg):
    pass

  def ProcessServerMessage(self, msg):
    irc_message = self.ParseMessage(msg)
    (prefix, payload) = string.split(msg,maxsplit=1)
    if( prefix.startswith(":") ):
      pass
    else:
      if(prefix.upper() == 'PING'):
        print 'Processing PING msg for ' + payload
        return 'PONG ' + payload
    return None

  def PassMessageToClient(self, msg, write2client):
    ircMessage = self.ParseMessage(msg.strip())
    print ircMessage.command
    if (ircMessage.command == u'PRIVMSG' ):
      print ircMessage
      self.channels[ircMessage.channel].Privmsg(ircMessage.chat)
      json_data = json.dumps(vars(ircMessage),sort_keys=True, indent=4)
      print(json_data)
      write2client(json_data)
    elif(ircMessage.command == u'JOIN'):
      if( not ircMessage.channel in self.channels ):
        self.channels[ircMessage.channel] = Channel(ircMessage.channel)
      self.channels[ircMessage.channel].Join(ircMessage.nick,ircMessage.chat)
      print ircMessage
      json_data = json.dumps(vars(ircMessage),sort_keys=True, indent=4)
      print(json_data)
      write2client(json_data)
    elif(ircMessage.command == u'QUIT'):
      pass
    elif(ircMessage.command == u'332'
        or ircMessage.command == u'TOPIC'):
      self.channels[ircMessage.channel].Topic(ircMessage.chat)
      print ircMessage
      json_data = json.dumps(vars(ircMessage),sort_keys=True, indent=4)
      print(json_data)
      write2client(json_data)

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

  @staticmethod
  def decode(bytes):
    #TODO: replace IRC specific formatting (bold, underline, colors)
    #with HTML amenable markup
    try:
      text = bytes.decode('utf-8')
    except UnicodeDecodeError:
      try:
        text = bytes.decode('iso-8859-1')
      except UnicodeDecodeError:
        text = bytes.decode('cp1252')
    return text

  @staticmethod
  def encode(bytes):
    try:
      text = bytes.encode('utf-8')
    except UnicodeEncodeError:
      try:
        text = bytes.encode('iso-8859-1')
      except UnicodeEncodeError:
        text = bytes.encode('cp1252')
    return text

class MainHandler(tornado.web.RequestHandler):
	def get(self):
		self.render("main.html")

class YotsubaFrontend(tornado.web.RequestHandler):
	def get(self):
		self.render("yotsuba.html")

class SimpleFrontend(tornado.web.RequestHandler):
	def get(self):
		self.render("simple.html")

class WebSocketHandler(tornado.websocket.WebSocketHandler):
  def initialize(self):
    print 'initialize called'
    self.IRCClient = IRCClient()

  def on_connect(self):
    self.stream.read_until('\r\n', self.on_line)

  def on_line(self, data):
    #python isn't great with \r\n so replace them before anything else.
    data = data.replace('\r\n', '\n')
    #first crack at processing responses without involving clients
    #this is mainly to process PING requests (send PONG)
    response = self.IRCClient.ProcessServerMessage(data)
    if response is not None:
      self.stream.write(response)

    #decode messages, parse and form json objects
    #and pass some to client
    decoded_line = IRCClient.decode(data)
    decoded_line = IRC.MarkupToHTML(decoded_line)

    print decoded_line
    
    self.IRCClient.PassMessageToClient(decoded_line, self.write_message)
    #self.write_message(json_data)

    #initiate the next blocking read for server messages
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
  parser = argparse.ArgumentParser(description='IRC bouncer (client) that provides HTML5 websocket client interface.')
  parser.add_argument('hostname', help='IRC server URL as domain:port (e.g. www.freenode.net:6660).', type=str)
  parser.add_argument('nickname', help='Nick to use at signon. Multiple nicks not yet supported.', type=str)
  parser.add_argument('channel', help='Channel to join on server. Only supporting one channel presently.', type=str)
  parser.add_argument('-p','--server_port', help='Port this server will service html client requests on. NOT the IRC server port this server connects to.', type=int, default=8888)
  parser.add_argument('-u', '--username', help='Username this server uses at IRC server signon.', type=str, default='')
  parser.add_argument('-r', '--realname', help='Realname this server uses at IRC server signon.', type=str, default='')
  parser.add_argument('--password', help='Optional password this server uses at signon', type=str, default=None)
  parser.add_argument('-v', '--verbose', help='Run server in verbose mode.', action="store_true")
  parser.add_argument('-s', '--ssl', help='Connect to server via SSL.', action="store_true")
  args = parser.parse_args()

  if args.verbose:
    print 'Running server on port {port}'.format(port=args.server_port)
    print 'Attempting to connect to IRC server {hostname} at {nick}'.format(hostname=args.hostname, nick=args.nickname)

  stats = {}

  application = tornado.web.Application([
      (r"/", MainHandler),
      (r"/yotsuba",YotsubaFrontend),
      (r'/simple',SimpleFrontend,),
      (r"/websocket", WebSocketHandler),
      (r"/css/(.*)", tornado.web.StaticFileHandler, {'path': '/home/joneil/code/WebIRCClient/css'}),
      (r"/image/(.*)", tornado.web.StaticFileHandler, {'path': '/home/joneil/code/WebIRCClient/image'}),
  ])
  application.listen(args.server_port)
  tornado.ioloop.IOLoop.instance().start() 
 
if __name__ == "__main__":
  main()
	
