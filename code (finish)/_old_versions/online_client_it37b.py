# online_client.py
# Iteration 37: the game's side of the connection to the online server.
# The connection runs on a separate thread, so the game never freezes while it waits for the internet
# (the free server can take up to a minute to wake up). Messages that arrive are put in a queue, and the
# game takes them out once a frame in pump(). Sending is done straight from the game.

import json
import queue
import threading
from os.path import abspath, dirname, exists, join

PROTOCOL = 1
DEFAULT_SERVER = 'ws://localhost:8765'
SERVER_FILE = join(dirname(abspath(__file__)), 'online_server.txt')   # one line: the server's address


# The address of the server. online_server.txt (next to the code) can change it without editing any code.
def server_address():
	if exists(SERVER_FILE):
		text = open(SERVER_FILE, encoding = 'utf-8').read().strip()
		if text.startswith(('ws://', 'wss://')):
			return text
	return DEFAULT_SERVER


class OnlineClient:
	def __init__(self, address = None, open_timeout = 75):
		self.address = address or server_address()
		self.open_timeout = open_timeout
		self.inbox = queue.Queue()
		self.connection = None
		self.thread = None
		self.status = 'offline'     # offline / connecting / online / failed
		self.error = None           # last error code from the server, or 'no_connection'
		self.me = None              # the welcome message: username, rating, wins, losses
		self.listeners = []         # functions called with every message (online screens add themselves)
		self.battle = None          # the battle_start message of the battle being played, if any

	@property
	def online(self):
		return self.status == 'online'

	# Connects and signs in (with a password the first time, then with the saved token).
	def connect(self, username, password = None, token = None):
		if self.status in ('connecting', 'online'):
			return
		self.status, self.error, self.me = 'connecting', None, None
		hello = {'type': 'hello', 'version': PROTOCOL, 'username': username}
		if token:
			hello['token'] = token
		if password:
			hello['password'] = password
		self.thread = threading.Thread(target = self.run, args = (hello,), daemon = True)
		self.thread.start()

	def run(self, hello):
		try:
			from websockets.sync.client import connect
		except ImportError:
			self.inbox.put({'type': 'error', 'code': 'no_websockets'})
			self.status = 'failed'
			return
		try:
			proxy = None if '://localhost' in self.address or '://127.0.0.1' in self.address else True
			with connect(self.address, open_timeout = self.open_timeout, proxy = proxy, max_size = 2 ** 20) as connection:
				self.connection = connection
				connection.send(json.dumps(hello))
				for raw in connection:
					try:
						message = json.loads(raw)
					except ValueError:
						continue
					if message.get('type') == 'welcome':
						self.me, self.status = message, 'online'
					self.inbox.put(message)
		except Exception as problem:   # no internet, the server is down, the connection dropped...
			self.inbox.put({'type': 'disconnected', 'reason': type(problem).__name__})
		finally:
			self.connection = None
			if self.status != 'failed':
				self.status = 'offline'

	def send(self, message):
		connection = self.connection
		if connection is None:
			return False
		try:
			connection.send(json.dumps(message))
			return True
		except Exception:
			return False

	def close(self):
		connection = self.connection
		self.status = 'offline'
		if connection is not None:
			try:
				connection.close()
			except Exception:
				pass

	# Takes every message that has arrived and returns them (oldest first). Errors from signing in also set
	# status to 'failed' so the screen can say what went wrong.
	def pump(self):
		messages = []
		while True:
			try:
				message = self.inbox.get_nowait()
			except queue.Empty:
				break
			if message.get('type') == 'error' and self.status != 'online':
				self.status, self.error = 'failed', message.get('code')
			if message.get('type') == 'error' and message.get('code') == 'signed_in_elsewhere':
				self.error = 'signed_in_elsewhere'
			if message.get('type') == 'disconnected' and self.status != 'failed' and self.error is None:
				self.error = 'no_connection'
			if message.get('type') in ('me', 'battle_end') and self.me:
				self.update_me(message)
			messages.append(message)
			for listener in list(self.listeners):
				listener(message)
		return messages

	def update_me(self, message):
		if message['type'] == 'me':
			self.me.update(rating = message['rating'], wins = message['wins'], losses = message['losses'])
