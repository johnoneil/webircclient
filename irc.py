# vim: set ts=2 expandtab:
"""

Module: irc.py
Desc: Helpers for IRC clients (msg decoding, paring, formatting)
Author: John O'Neil
Email: oneil.john@gmail.com
DATE: Tuesday, Dec 24th 2013
  
""" 

import re
import string

class JSONTagged(object):
  def __init__(self):
    self.type = self.__class__.__name__

class PrivMessage(JSONTagged):
  '''message encapsulating an IRC PRIVMSG.
  Really just meant to be used converting to json
  '''
  def __init__(self, user, channel, msg):
    super(PrivMessage, self).__init__()
    self.user = user
    self.channel = channel
    self.msg = msg
    nick, vhost = split_speaker(user)
    self.nick = nick
    self.vhost = vhost

class TopicMessage(JSONTagged):
  def __init__(self, channel, topic):
    super(TopicMessage, self).__init__()
    self.channel = channel
    self.topic = topic

class JoinedMessage(JSONTagged):
  def __init__(self, channel):
    super(JoinedMessage, self).__init__()
    self.channel = channel

class LeftMessage(JSONTagged):
  def __init__(self, channel):
    super(LeftMessage, self).__init__()
    self.channel = channel

class NoticedMessage(JSONTagged):
  def __init__(self, user, channel, msg):
    super(NoticedMessage, self).__init__()
    self.user = user
    self.channel = channel
    self.msg = msg

class ModeChangedMessage(JSONTagged):
  def __init__(self, user, channel, set, modes, args):
    super(ModeChangedMessage, self).__init__()
    self.user = user
    self.set = set
    self.modes = modes
    self.args = args

class KickedFromMessage(JSONTagged):
  def __init__(self,  channel, kicker, message):
    super(KickedFromMessage, self).__init__()
    self.channel = channel
    self.kicker = kicker
    self.message = message

class NickChangedMessage(JSONTagged):
  def __init__(self,  nick):
    super(NickChangedMessage, self).__init__()
    self.nick = nick

class UserJoinedMessage(JSONTagged):
  def __init__(self,  user, channel):
    super(UserJoinedMessage, self).__init__()
    self.user = user
    self.channel = channel

class UserLeftMessage(JSONTagged):
  def __init__(self,  user, channel):
    super(UserLeftMessage, self).__init__()
    self.user = user
    self.channel = channel

class UserQuitMessage(JSONTagged):
  def __init__(self,  user, quit_message):
    super(UserQuitMessage, self).__init__()
    self.user = user
    self.quit_message = quit_message

class UserKickedMessage(JSONTagged):
  def __init__(self, kickee, channel, kicker, message):
    super(UserKickedMessage, self).__init__()
    self.kickee = kickee
    self.channel = channel
    self.kicker = kicker
    self.message = message

class ActionMessage(JSONTagged):
  def __init__(self, user, channel, data):
    super(ActionMessage, self).__init__()
    self.user = user
    self.channel = channel
    self.data = data

class TopicUpdatedMessage(JSONTagged):
  def __init__(self,  user, channel, new_topic):
    super(TopicUpdatedMessage, self).__init__()
    self.user = user
    self.channel = channel
    self.new_topic = new_topic

class UserRenamedMessage(JSONTagged):
  def __init__(self, oldname, newname):
    super(UserRenamedMessage, self).__init__()
    self.oldname = oldname
    self.newname = newname


def split_speaker(user):
  '''
  split a nick most likely in the form:
  "nick!~realname@vhost"
  or (nick)!~(realname)@(vhost)
  into a tuble of (nick, vhost)
  '''
  nick, vhost = string.split(user, '!', maxsplit=1)
  if not vhost:
    vhost = 'nick@unknown'
  vhost = vhost.replace('~', '', 1)
  return nick, vhost

#after http://stackoverflow.com/questions/938870/python-irc-bot-and-encoding-issue
def decode(bytes):
  try:
    text = bytes.decode('utf-8')
  except UnicodeDecodeError:
    try:
      text = bytes.decode('iso-8859-1')
    except UnicodeDecodeError:
      text = bytes.decode('cp1252')
  return text


def encode(bytes):
  try:
    text = bytes.encode('utf-8')
  except UnicodeEncodeError:
    try:
      text = bytes.encode('iso-8859-1')
    except UnicodeEncodeError:
      text = bytes.encode('cp1252')
  return text

color_dict = {
  0 : 'white',
  1 : 'black',
  2 : 'dark blue',
  3 : 'dark green',
  4 : 'red',
  5 : 'dark red',
  6 : 'dark violet',
  7 : 'dark orange',
  8 : 'yellow',
  9 : 'light green',
  10 : 'cyan',
  11 : 'light cyan',
  12 : 'blue',
  13 : 'violet',
  14 : 'dark gray',
  15 : 'light gray',
  }

html_color_dict = {
  0 : 'White',
  1 : 'Black',
  2 : 'DarkBlue',
  3 : 'DarkGreen',
  4 : 'Red',
  5 : 'DarkRed',
  6 : 'DarkViolet',
  7 : 'DarkOrange',
  8 : 'Yellow',
  9 : 'LightGreen',
  10 : 'Cyan',
  11 : 'LightCyan',
  12 : 'Blue',
  13 : 'Violet',
  14 : 'DarkGray',
  15 : 'LightGray',
  }

def color_code_to_X11(code):
  if not type(code) == int:
    return 'black'
  if code<0:
    return 'black'
  if code>15:
    return 'black'
  return color_dict[code]

def color_code_to_html(code):
  if not type(code) == int:
    return 'Black'
  if code<0:
    return 'Black'
  if code>15:
    return 'Black'
  return html_color_dict[code]

def formatting_to_pango_markup(msg):
  '''
  Take an irc message already decoded from utf-8/latin1 etc
  and replace typical binary irc color code formatting with
  pango markup.
  '''
  msg = decode(msg)
  msg = re.sub(r'&','&amp;', msg)
  msg = re.sub(r'\<','&lt;', msg)
  msg = re.sub(r'\>','&gt;', msg)
  class MarkupFunctor(object):
    def __init__(self):
      self.match_found = False
      self.bold = False
      self.underline = False
      self.fg_color = -1
      self.bg_color = -1
      self.italic = False
      
    def __call__(self, match):
      '''
      function call operator called by regex replace
      upon the finding of a match in msg sring
      '''
      if match.groupdict()['reset'] is not None:
        self.bold = False
        self.underline = False
        self.fg_color = -1
        self.bg_color = -1
        self.italic = False

      if match.groupdict()['reverse'] is not None:
        c = self.bg_color
        self.bg_color = self.fg_color
        self.fg_color = c

      if match.groupdict()['bold'] is not None:
        self.bold = not self.bold

      if match.groupdict()['underline'] is not None:
        self.underline = not self.underline

      if match.groupdict()['italic'] is not None:
        self.italic = not self.italic

      if match.groupdict()['color'] is not None:
        if match.groupdict()['fg'] is not None:
          self.fg_color = int(match.groupdict()['fg'])
        if match.groupdict()['bg'] is not None:
          self.bg_color = int(match.groupdict()['bg'])
        if match.groupdict()['fg'] is None and match.groupdict()['bg'] is None:
          self.fg_color = -1
          self.bg_color = -1

      output = ''

      if not self.match_found:
        self.match_found=True
        output = '<span '
      else:
        output = '</span><span '

      if self.bold:
        output += 'weight="bold" '

      if self.underline:
        output += 'underline="single" '

      if self.italic:
        output += 'style="italic" '

      if self.fg_color >=0:
        output += 'color="' + color_code_to_X11(self.fg_color) + '" '

      if self.bg_color >=0:
        output += 'background="' +color_code_to_X11(self.bg_color) + '" '

      output += '>'

      return output

  #TODO: it would be best to refactor this to match not only the IRC binary markup
  #but also the text between this markup and the next instance/eol. That
  #would be easier to turn into ideal pango (HTML-like) markup tags.
  regex = r'((?P<reset>\x0f)|(?P<underline>\x1f)|(?P<bold>\x02)|(?P<italic>\x1d)|(?P<reverse>\x12)|(?P<color>\x03(?P<fg>\d{1,2})?(,(?P<bg>\d{1,2}))?))+'
  markup_transform = MarkupFunctor()
  msg = re.sub(regex, markup_transform, msg)
  if markup_transform.match_found:
    msg += '</span>'
  return msg

def markup_to_html(message):
  '''
  Take an irc message and ensure it's encoded in UTF-8.
  Then replace typical IRC binary tags with html <span> tags
  It's up to clients to have proper styles to interpret
  these <span class='X'> tags properly
  '''
  msg = decode(message)
  msg = re.sub(r'&','&amp;', msg)
  msg = re.sub(r'\<','&lt;', msg)
  msg = re.sub(r'\>','&gt;', msg)
  class MarkupFunctor(object):
    def __init__(self):
      self.match_found = False
      self.bold = False
      self.underline = False
      self.fg_color = -1
      self.bg_color = -1
      self.italic = False
      
    def __call__(self, match):
      '''
      function call operator called by regex replace
      upon the finding of a match in msg sring
      '''
      if match.groupdict()['reset'] is not None:
        self.bold = False
        self.underline = False
        self.fg_color = -1
        self.bg_color = -1
        self.italic = False

      if match.groupdict()['reverse'] is not None:
        c = self.bg_color
        self.bg_color = self.fg_color
        self.fg_color = c

      if match.groupdict()['bold'] is not None:
        self.bold = not self.bold

      if match.groupdict()['underline'] is not None:
        self.underline = not self.underline

      if match.groupdict()['italic'] is not None:
        self.italic = not self.italic

      if match.groupdict()['color'] is not None:
        if match.groupdict()['fg'] is not None:
          self.fg_color = int(match.groupdict()['fg'])
        if match.groupdict()['bg'] is not None:
          self.bg_color = int(match.groupdict()['bg'])
        if match.groupdict()['fg'] is None and match.groupdict()['bg'] is None:
          self.fg_color = -1
          self.bg_color = -1

      output = ''

      if not self.match_found:
        self.match_found=True
        output = '<span '
      else:
        output = '</span><span '

      if self.bold:
        output += 'class="IRCBold" '

      if self.underline:
        output += 'class="URCUnderline" '

      if self.italic:
        output += 'class="IRCItalic" '

      if self.fg_color >=0:
        output += 'class="IRCForegroundColor' + color_code_to_html(self.fg_color) + '" '

      if self.bg_color >=0:
        output += 'class="BackgroundColor' + color_code_to_html(self.bg_color) + '" '

      output += '>'

      return output

  #TODO: it would be best to refactor this to match not only the IRC binary markup
  #but also the text between this markup and the next instance/eol. That
  #would be easier to turn into ideal pango (HTML-like) markup tags.
  regex = r'((?P<reset>\x0f)|(?P<underline>\x1f)|(?P<bold>\x02)|(?P<italic>\x1d)|(?P<reverse>\x12)|(?P<color>\x03(?P<fg>\d{1,2})?(,(?P<bg>\d{1,2}))?))+'
  markup_transform = MarkupFunctor()
  msg = re.sub(regex, markup_transform, msg)
  if markup_transform.match_found:
    msg += '</span>'
  return msg


def to_hex(msg):
  '''
  Helper to Dump hex of message to screen
  '''
  line = decode(msg)
  print ':'.join(x.encode('hex') for x in line)
  print '----------------------------------'
  print ':'.join(unicode(x) for x in line)

