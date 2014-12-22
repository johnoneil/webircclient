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
This moves to using cyclone to leverage the twisted IRC client.

basic operation as follows:

   -------------                 --------------              -----------------------
  |             |               |              |            |                       |
  | web browser |<--websocket-->|  this server |<--TCP/IP-->| IRC Server or bouncer |
  |             |               |              |            |                       |
   -------------                 --------------              -----------------------

  1) Currently this server is configured to log into an IRC server and some channels
  (this may changes or be enhanced with client initiation of this login process
  in the future)

  2) Web brorser retrieves page from this browser, that page initiates a websocket
  connection to this server from the browser.

  3) Once the websocke connection is established, this server feeds IRC protocol
  messages down the websocket to browser as a series of JSON messages. Clients
  can interpret and display these JSON messages in any way they want.

  4) Clients can also feed JSON messages up the websocket up to the server. The
  format for these messages is not yet described as I'm refactoring.
  
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
		self.render("main.html", host=self.settings.hostname, port=self.settings.port)

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
    self.application.clients.append(self)

  def connectionLost(self, reason):
    print 'WebSocketHandler::connectionLost'
    self.application.clients.remove(self)

  def messageReceived(self, messageReceived):
    print 'WebSocketHandler::connectionMade. msg:' + messageReceived
    log.msg("got message %s" %messageReceived)
    #parsed = cyclone.escape.json_decode(message)

  def update(self, msg):
    '''Push json msg out to client.
    '''
    self.sendMessage(msg)
    


class IRCWebChatFrontend(cyclone.web.Application):
  clients = []

  def __init__(self, hostname='localhost', port='8888'):
    self.irc_socket = None 


    settings = dict(
      cookie_secret="43oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
      template_path=os.path.join(os.path.dirname(__file__), "templates"),
      static_path=os.path.join(os.path.dirname(__file__), "static"),
      xsrf_cookies=True,
      autoescape=None,
      hostname=hostname,
      port=port,
    )
    #stats = Stats()
    handlers = [
          (r"/", MainHandler),
          (r"/yotsuba",YotsubaFrontend),
          (r'/simple',SimpleFrontend),
          (r"/websocket", WebSocketHandler, dict(data=self)),
          (r"/css/(.*)", cyclone.web.StaticFileHandler, {'path': settings['static_path']}),
          (r"/image/(.*)", cyclone.web.StaticFileHandler, {'path': settings['static_path']}),
      ]

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
    #i want utf-8 encoded strings, not escaped unicode
    m = pickled.decode('unicode-escape').encode('utf-8')
    print m
    for client in IRCWebChatFrontend.clients:
      client.update(m)


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

    if network['identity']['nickserv_password']:
      self.msg('NickServ', 
            'IDENTIFY %s' % network['identity']['nickserv_password'])

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
    Since we're feeding these messages to web clients we do the following:
    1) ensure encoding is utf-8
    2) replace IRC type binary markup (bold, colors) with html <span> tags
    '''
    message = irc.markup_to_html(msg)
    priv_message = irc.PrivMessage(user, channel, message)
    self.factory.web_frontend.update_clients(priv_message)

  def left(self, channel):
    left_message = irc.LeftMessage(channel)
    self.factory.web_frontend.update_clients(left_message)

  def noticed(self, user, channel, message):
    notieced_msg = irc.NoticedMessage(user, channel, message)
    self.factory.web_frontend.update_clients(notieced_msg)

  def modeChanged(self, user, channel, set, modes, args):
    mode_changed_msg = irc.ModeChangedMessage(user, channel, set, modes, args)
    self.factory.web_frontend.update_clients(mode_changed_msg)
    
  def kickedFrom(self, channel, kicker, message):
    kicked_from_msg = irc.KickedFromMessage(channel, kicker, message)
    self.factory.web_frontend.update_clients(kicked_from_msg)

  def NickChanged(self, nick):
    nick_changed_msg = irc.NickChangedMessage(nick)
    self.factory.web_frontend.update_clients(nick_changed_msg)

  def userJoined(self, user, channel):
    user_joined_msg = irc.UserJoinedMessage(user, channel)
    self.factory.web_frontend.update_clients(user_joined_msg)

  def userLeft(self, user, channel):
    user_left_msg = irc.UserLeftMessage(user, channel)
    self.factory.web_frontend.update_clients(user_left_msg)

  def userQuit(self, user, quit_message):
    user_quit_msg = irc.UserQuitMessage(user, quit_message)
    self.factory.web_frontend.update_clients(user_quit_msg)

  def userKicked(self, kickee, channel, kicker, message):
    user_kicked_msg = irc.UserKickedMessage(kickee, channel, kicker, message)
    self.factory.web_frontend.update_clients(user_kicked_msg)

  def action(self, user, channel, data):
    action_msg = irc.ActionMessage(user, channel, data)
    self.factory.web_frontend.update_clients(action_msg)

  def topicUpdated(self, user, channel, new_topic):
    topic_updated_msg = irc.TopicUpdatedMessage(user, channel, new_topic)
    self.factory.web_frontend.update_clients(topic_updated_msg)

  def userRenamed(self, oldname, newname):
    user_renamed_msg = irc.UserRenamedMessage(oldname, newname)
    self.factory.web_frontend.update_clients(user_renamed_msg)

  '''
  def irc_RPL_TOPIC(self, prefix, params):
    """
    Called when the topic for a channel is initially reported or when it      subsequently changes.
    params[0] is your nick
    params[1] is channel joined
    params[2] is topic for channel

    """
    print 'IRCWebChatClient::irc_RPL_TOPIC'
    channel = params[1]
    topic = params[2]
    #topic = irc.formatting_to_pango_markup(topic)

    topic_message = irc.TopicMessage(channel, topic)
    self.factory.web_frontend.update_clients(topic_message)
'''
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
  parser.add_argument('--nickserv_pw', help='Optional password to use with nickserv after IRC server connect.', type=str, default=None)
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
    'password': args.password,
    'nickserv_password': args.nickserv_pw
  }
  #we've got to add thise to the client, which is odd as fuq
  IRCWebChatClient.nickname = credentials['nickname']
  IRCWebChatClient.realname = credentials['realname']
  IRCWebChatClient.username = credentials['username']
  IRCWebChatClient.password = credentials['password']
    
  channels = (args.channel,)

  network = {
    'host': hostname,
    'port': port,
    'ssl': args.ssl,
    'identity': credentials,
    'autojoin': channels
  }

  web_frontend = IRCWebChatFrontend()
  factory = IRCWebChatClientFactory(hostname, network, web_frontend)
  if args.ssl:
    reactor.connectSSL(hostname, port, factory, ssl.ClientContextFactory())
  else:
    reactor.connectTCP(hostname, port, factory)

  reactor.listenTCP(args.server_port, web_frontend)
  
  reactor.run()


if __name__ == "__main__":
  log.startLogging(sys.stdout)
  main()
