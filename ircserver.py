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

class WebSocketHandler(tornado.websocket.WebSocketHandler):
  def initialize(self):
    print 'initialize called'
    self.IRCClient = IRCClient()

  def on_connect(self):
    self.stream.read_until('\r\n', self.on_line)

  def on_line(self, data):
    #python isn't great with \r\n so replace them before anything else.
    data = data.replace('\r\n', '\n')
    decoded_line = IRCClient.decode(data)

    decoded_line = IRC.MarkupToHTML(decoded_line)

    #decoded_line = re.sub(ur"\u0002(.*?)\u0002", ur'<span class="IRCBold">\1</span>', decoded_line)
    #decoded_line = re.sub(ur"\u0002(.*?)$", ur'<span class="IRCBold">\1</span>', decoded_line)
    #decoded_line = re.sub(ur"\u001f(.*?)\u001f", ur'<span class="IRCUnderline">\1</span>', decoded_line)
    #decoded_line = re.sub(ur"\u001f(.*?)$", ur'<span class="IRCUnderline">\1</span>', decoded_line)

    #define a dictionary of irc binary tags:
    #dic['\u0002] = "IRCBold"
    #start search through document for all keys. Upon key, add the key to our current key group
    #at the first key, replace as <span class="key">
    #if no more found, add </span>
    #if more found, add next key switch to current key group (e.g. IRCBold IRCUnderlined)
    #replce with closing and then opening span at tag change </span><span class="IRCBold IRCUnderlined">
    #note that keys can both turn on and off some properties (like colors)
    #if no more found, add </span>
    #repeat

    print decoded_line
    
    ircMessage = self.IRCClient.ParseMessage(decoded_line.strip())
    print ircMessage.command
    if ircMessage.command == 'PRIVMSG':
      print ircMessage
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
      (r"/yotsuba",YotsubaFrontend),
      (r"/websocket", WebSocketHandler),
      (r"/css/(.*)", tornado.web.StaticFileHandler, {'path': '/home/joneil/code/WebIRCClient/css'}),
      (r"/image/(.*)", tornado.web.StaticFileHandler, {'path': '/home/joneil/code/WebIRCClient/image'}),
  ])
  application.listen(8888)
  tornado.ioloop.IOLoop.instance().start() 
 
if __name__ == "__main__":
  main()
	
