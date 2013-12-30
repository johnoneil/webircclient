#!/usr/bin/python
# vim: set ts=2 expandtab:
"""

Module: server.py
Desc: cyclone based irc bouncer to HTML5 websocket
Author: John O'Neil
Email: oneil.john@gmail.com
DATE: Saturday, December 29th 2013

Refactoring the basic setup i did last year to eliminate the need
for a specific IRC client to be coded.
This moves to using cyclone to leverage the twisted IRC client
  
""" 

import os.path
import uuid
import sys
import time
from collections import defaultdict
import argparse
import string
import jsonpickle

from twisted.internet import task
from twisted.internet import reactor
from twisted.internet import protocol
from twisted.internet import ssl
from twisted.python import log
from twisted.words.protocols import irc as twisted_irc
import irc

import cyclone.escape
import cyclone.web
import cyclone.websocket


class SocketError(Exception):
  def __init__(self, message):
    self.message = message

class MainHandler(cyclone.web.RequestHandler):
	def get(self):
		self.render("main.html")

class YotsubaFrontend(cyclone.web.RequestHandler):
	def get(self):
		self.render("yotsuba.html")

class SimpleFrontend(cyclone.web.RequestHandler):
	def get(self):
		self.render("simple.html")

class WebSocketHandler(cyclone.websocket.WebSocketHandler):

  def initialize(self, data):
    print 'WebSocketHandler::initialize'

  def connectionMade(self):
    print 'WebSocketHandler::connectionMade'

  def connectionLost(self, reason):
    print 'WebSocketHandler::connectionMade'

  #@classmethod
  #def update_cache(cls, chat):
  #  cls.cache.append(chat)
  #  if len(cls.cache) > cls.cache_size:
  #    cls.cache = cls.cache[-cls.cache_size:]

  #@classmethod
  #def send_updates(cls, chat):
  #  log.msg("sending message to %d waiters" % len(cls.waiters))
  #  for waiter in cls.waiters:
  #    try:
  #      waiter.sendMessage(chat)
  #    except Exception, e:
  #      log.err("Error sending message. %s" % str(e))

  def messageReceived(self, messageReceived):
    print 'WebSocketHandler::connectionMade. msg:' + messageReceived
    log.msg("got message %s" % message)
    #pickled = jsonpickle.encode(chat)
    parsed = cyclone.escape.json_decode(message)
    #chat = {
    #    "id": str(uuid.uuid4()),
    #    "body": parsed["body"],
    #    }
    #chat["html"] = self.render_string("message.html", message=chat)

    #ChatSocketHandler.update_cache(chat)
    #ChatSocketHandler.send_updates(chat)

  def update_clients(self, data):
    #data = dict(visits=self.stats.todaysVisits(),
    #            chatters=self.stats.chatters)
    #self.sendMessage(cyclone.escape.json_encode(data))
    #self.sendMessage(cyclone.escape.json_encode(data))
    pickled = jsonpickle.encode(data)
    print 'Websocket::update_clients()' + unicode(pickled)
    


class Application(cyclone.web.Application):
  def __init__(self):
    self.irc_socket = None 

    #stats = Stats()
    handlers = [
          (r"/", MainHandler),
          (r"/yotsuba",YotsubaFrontend),
          (r'/simple',SimpleFrontend),
          (r"/websocket", WebSocketHandler, dict(data=self)),
          (r"/css/(.*)", cyclone.web.StaticFileHandler, {'path': '/home/joneil/code/webircclient/css'}),
          (r"/image/(.*)", cyclone.web.StaticFileHandler, {'path': '/home/joneil/code/webircclient/image'}),
      ]
    '''
      handlers = [
          (r"/", MainHandler, dict(stats=stats)),
          (r"/stats", StatsPageHandler),
          (r"/statssocket", StatsSocketHandler, dict(stats=stats)),
          (r"/chatsocket", ChatSocketHandler, dict(stats=stats)),
      ]
    '''
    settings = dict(
      cookie_secret="43oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
      template_path=os.path.join(os.path.dirname(__file__), "templates"),
      static_path=os.path.join(os.path.dirname(__file__), "static"),
      xsrf_cookies=True,
      autoescape=None,
    )
    cyclone.web.Application.__init__(self, handlers, **settings)

  def set_irc_socket(self, socket):
    #TODO: perhaps it would be better to be able to maintain N server connections?
    #TODO: also, perhaps client can initiate connection to server X?
    if self.irc_socket:
      return
    #if self.irc_socket:
    #  raise SocketError('Web interface already has socket assigned. Can\'t do so twice.')
    self.irc_socket = socket

  def update_clients(self, msg):
    '''
    Send message to all clients
    '''
    #TODO: send json data via websocket to all listening clients.
    pickled = jsonpickle.encode(msg)
    print 'Websocket::update_clients()' + unicode(pickled)

'''
class MainHandler(cyclone.web.RequestHandler):
  def initialize(self, stats):
    self.stats = stats

  def get(self):
    self.stats.newVisit()
    self.render("index.html", messages=ChatSocketHandler.cache)

  def initialize(self):
    print 'initialize called'
    self.IRCClient = IRCClient()

  def on_connect(self):
    print '
    #self.stream.read_until('\r\n', self.on_line)

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

'''


'''
class StatsSocketHandler(cyclone.websocket.WebSocketHandler):
  def initialize(self, stats):
    self.stats = stats

    self._updater = task.LoopingCall(self._sendData)

  def connectionMade(self):
    self._updater.start(2)

  def connectionLost(self, reason):
    self._updater.stop()

  def _sendData(self):
    data = dict(visits=self.stats.todaysVisits(),
                chatters=self.stats.chatters)
    self.sendMessage(cyclone.escape.json_encode(data))


class Stats(object):
  def __init__(self):
    self.visits = defaultdict(int)
    self.chatters = 0

  def todaysVisits(self):
    today = time.localtime()
    key = time.strftime('%Y%m%d', today)
    return self.visits[key]

  def newChatter(self):
    self.chatters += 1

  def lostChatter(self):
    self.chatters -= 1

  def newVisit(self):
    today = time.localtime()
    key = time.strftime('%Y%m%d', today)
    self.visits[key] += 1


class StatsPageHandler(cyclone.web.RequestHandler):
  def get(self):
    self.render("stats.html")
'''

class IRCWebChatClient(twisted_irc.IRCClient):

  def connectionMade(self):
    print 'IRCWebChatClient::connectionMade'
    twisted_irc.IRCClient.connectionMade(self)
    self.factory.web_frontend.set_irc_socket(self)

  def connectionLost(self, reason):
    print 'IRCWebChatClient::connectionLost'
    twisted_irc.IRCClient.connectionLost(self, reason)
    self.factory.web_frontend.set_irc_socket(None)

  def signedOn(self):
    print 'IRCWebChatClient::signedOn'
    '''
    Called when we've connected to the IRC server.
    We can use this opportunity to communicate with nickserv
    if necessary
    '''
    network = self.factory.network

    if network['identity']['nickserv_pw']:
      self.msg('NickServ', 
            'IDENTIFY %s' % network['identity']['nickserv_pw'])

    for channel in network['autojoin']:
      print('join channel %s' % channel)
      self.join(channel)

  def joined(self, channel):
    '''
    Called when we've joined a channel. This is here used to
    Initialize a chat dialog on the screen that will later
    be updated with posts as the chat progresses.
    '''
    print 'IRCWebChatClient::joined'

    joined_message = irc.JoinedMessage(channel)
    self.factory.web_frontend.update_clients(joined_message)

  def privmsg(self, user, channel, msg):
    '''
    Invoked upon receipt of a message in channel X.
    Here it's used to pass chat posts to video overlay via dbus
    '''
    print 'IRCWebChatClient::privmsg'

    priv_message = irc.PrivMessage(user, channel, msg)
    self.factory.web_frontend.update_clients(priv_message)

  def irc_RPL_TOPIC(self, prefix, params):
    '''
    Called when the topic for a channel is initially reported or when it      subsequently changes.
    params[0] is your nick
    params[1] is channel joined
    params[2] is topic for channel

    '''
    print 'IRCWebChatClient::irc_RPL_TOPIC'
    channel = params[1]
    topic = params[2]
    #topic = irc.formatting_to_pango_markup(topic)

    topic_message = irc.TopicMessage(channel, topic)
    self.factory.web_frontend.update_clients(topic_message)

  def alterCollidedNick(self, nickname):
    print 'IRCWebChatClient::alterCollidedNick'
    return nickname+'_'

class IRCWebChatClientFactory(protocol.ClientFactory):
  protocol = IRCWebChatClient

  def __init__(self, network_name, network, web_frontend):
    self.network_name = network_name
    self.network = network
    self.web_frontend = web_frontend

  def clientConnectionLost(self, connector, reason):
    connector.connect()

  def clientConnectionFailed(self, connector, reason):
    reactor.stop()


def split_server_port(hostname):
  hostname, port = string.split(hostname, ':', maxsplit=1)
  if not port:
    port = DEFAULT_PORT
  else:
    try:
      port = int(port)
    except ValueError:
      port = DEFAULT_PORT
  return (hostname, port)


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

  hostname, port = split_server_port(args.hostname)
  if args.verbose:
    print 'Connecting to ' + hostname + ' on port ' + str(port) +'.'
    
  credentials = {
    'nickname': args.nickname,
    'realname': args.realname if len(args.realname)>0 else args.nickname,
    'username': args.username if len(args.username)>0 else args.nickname,
    'nickserv_pw': args.password
  }
  #we've got to add thise to the client, which is odd as fuq
  IRCWebChatClient.nickname = credentials['nickname']
  IRCWebChatClient.realname = credentials['realname']
  IRCWebChatClient.username = credentials['username']
  IRCWebChatClient.password = credentials['nickserv_pw']
    
  channels = (args.channel,)

  network = {
    'host': hostname,
    'port': port,
    'ssl': args.ssl,
    'identity': credentials,
    'autojoin': channels
  }

  web_frontend = Application()
  factory = IRCWebChatClientFactory(hostname, hostname, web_frontend)
  if args.ssl:
    reactor.connectSSL(hostname, port, factory, ssl.ClientContextFactory())
  else:
    reactor.connectTCP(hostname, port, factory)

  reactor.listenTCP(args.server_port, web_frontend)
  
  reactor.run()


if __name__ == "__main__":
  log.startLogging(sys.stdout)
  main()
