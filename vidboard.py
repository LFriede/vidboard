#!/bin/env python

# v0.1.0 from 24.06.2026

import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import re
import ipaddress # For subnet/host filtering
import json      # for config file

# README:
# - Make sure mpv is installed and in path.
# - Make sure to set the charset to UTF-8 in the template.html. Just use the
#   following definition in head: <meta charset="UTF-8">

# Installation:
# - Copy everything to ~/vidboard/
# - Use install_service.sh to install the service for the current user
# - Use "systemctl --user enable vidboard" if you want the service to start on boot.
# - Add videos by putting the files in the vids subdir and add a png as thumbnail
#   with the same filename as the video.

# Returns True if our IP is in one of the subnets
def ipfilter(ipaddr):
  ipparsed = ipaddress.ip_address(ipaddr)
  for net in g_config['clientfilter']:
    if ipparsed in ipaddress.ip_network(net):
      return True
  return False

def cutext(filename):
  return os.path.splitext(filename)[0]

class MyHandler(BaseHTTPRequestHandler):
  def valid_index(self, id):
    if abs(id) < len(g_videos):
      return True
    self.send_response(404)
    self.end_headers()
    return False

  def servimg(self, id):
    if self.valid_index(id) == False:
      return
    self.send_response(200)
    self.end_headers()
    with open(directory + '/' + cutext(g_videos[id]) + '.png', 'rb') as pngfile:
      self.wfile.write(pngfile.read())

  def play(self, id):
    if self.valid_index(id) == False:
      return
    os.system('mpv --fullscreen "' + directory + '/' + g_videos[id] + '"')
    self.send_response(200)
    self.end_headers()
    self.wfile.write(b'{"status": "ok"}')

  def pagehandler(self):
    self.send_response(200)
    self.end_headers()

    self.wfile.write(g_splittext[0])
    for index, video in enumerate(g_videos):
      self.wfile.write(g_splittext[1]
        .replace(b'%videotitle%', cutext(video).encode())
        .replace(b'%videoid%', str(index).encode())
      )
    self.wfile.write(g_splittext[2])

  def do_GET(self):
    # Filter access by subnets
    if ipfilter(self.client_address[0]) == False:
      self.send_response(503)
      self.end_headers()
      self.wfile.write(b'piss dich...')
      return

    if self.path == '/':
      self.pagehandler()
      return

    if self.path == '/reindex':
      refreshvids()
      self.send_response(200)
      self.end_headers()
      self.wfile.write(b'{"status": "ok"}')
      return

    reg = re.match('/play/([0-9]{1,3})', self.path)
    if reg:
      self.play(int(reg.group(1)))
      return

    reg = re.match('/img/([0-9]{1,3}).png', self.path)
    if reg:
      self.servimg(int(reg.group(1)))
      return

    self.send_response(404)
    self.end_headers()
    self.wfile.write(b'404 un wat nich...')
    print(self.path)

# We index our video directory and include all videos for which there is
# a PNG file with the same name.
def refreshvids():
  global g_videos
  g_videos = []
  for file in os.listdir(directory):
    filename = os.fsdecode(file)
    if os.path.splitext(filename)[1] == '.png':
      continue
    if os.path.isfile(directory + '/' + cutext(filename) + '.png'):
      g_videos.append(filename)
      print(filename)

# Read config file
g_config = {} # global declaration
try:
  with open('./settings.json') as fjson:
    g_config = json.load(fjson)
except:
  pass # the following code handles non existing configs, so we just swallow

# Validate config or replace with defaults
defaultport = 1337
if 'port' not in g_config:
  g_config['port'] = defaultport
  print('No port configured, using default.')
if isinstance(g_config['port'], int):
  if (g_config['port'] < 1) or (g_config['port'] > 65535):
    print('Port is not in valid range 1-65535, using default.')
    g_config['port'] = defaultport
else:
  print('Configured port is not an int, using default.')
  g_config['port'] = defaultport

# Validate host/net filter
defaultfilter = [ipaddress.ip_network('127.0.0.1')] # allow only localhost per default
if 'clientfilter' not in g_config:
  g_config['clientfilter'] = defaultfilter
  print('No clientfilter configured, using default.')
if isinstance(g_config['clientfilter'], list):
  for filteritem in g_config['clientfilter']:
    # try to convert all items, if we fail we use defaults
    try:
      ipaddress.ip_network(filteritem)
    except:
      print('Invalid client filter item "' + filteritem + '", using default.')
      g_config['clientfilter'] = defaultfilter
      break
else:
  print('Configured clientfilter is not a list, using default.')
  g_config['clientfilter'] = defaultfilter

print(g_config)

# Read the whole template file to a binary string. Will be reused in a global var.
html = b''
with open('./template.html', 'rb') as file:
  html = file.read()

# The html template is splitted in three parts. The html comment seperates the
# parts. We need a header, a repeating part for each video and a footer.
g_splittext = html.split(b'<!--split-->')

# Iterate videodir
directory = "./vids"
g_videos = [] # declare variable once in global scope
refreshvids()

httpd = HTTPServer(('', g_config['port']), MyHandler)
httpd.serve_forever()
