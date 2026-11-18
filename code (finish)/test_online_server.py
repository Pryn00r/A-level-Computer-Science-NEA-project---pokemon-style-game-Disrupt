# test_online_server.py
# Iteration 37: tests for the online server. A real server is started on this computer (with its own empty
# database) and test players connect to it over WebSockets, exactly like two copies of the game would.
# Set TEST_DATABASE_URL to a postgres:// address to run the same tests against PostgreSQL.
# Run with:  python -m unittest test_online_server

import importlib.util, sys
if importlib.util.find_spec('websockets') is None:   # the online tests need:  pip install websockets
	print('SKIPPED - websockets is not installed (pip install websockets)')
	sys.exit(0)
import asyncio
import os
import tempfile
import threading
import time
import unittest

import online_server
from online_client import OnlineClient
from online_db import Database
import online_engine as engine
from game_data import ATTACK_DATA

PORT = 8799
ADDRESS = f'ws://localhost:{PORT}'
STATE = {}


def start_server():
	online_server.TURN_SECONDS = 1.5
	online_server.CHALLENGE_SECONDS = 1.5
	online_server.RECONNECT_SECONDS = 1.5
	address = os.environ.get('TEST_DATABASE_URL') or os.path.join(tempfile.mkdtemp(), 'test.db')
	database = Database(address)
	if database.postgres:
		database.run('DELETE FROM battles')
		database.run('DELETE FROM users')
	ready = threading.Event()
	def run():
		loop = asyncio.new_event_loop()
		STATE['loop'] = loop
		loop.run_until_complete(online_server.main(PORT, database, lambda server, running: (STATE.update(server = server), ready.set())))
	threading.Thread(target = run, daemon = True).start()
	ready.wait(10)


# A test player: connects, then waits for the messages it expects.
class Tester:
	def __init__(self, username, password = 'Strong#Pass1', token = None):
		self.client = OnlineClient(ADDRESS, open_timeout = 5)
		self.messages = []
		self.client.connect(username, password if token is None else None, token)

	def wait(self, kind, seconds = 5, **match):
		end = time.time() + seconds
		while time.time() < end:
			self.messages += self.client.pump()
			for index, message in enumerate(self.messages):
				if message.get('type') == kind and all(message.get(k) == v for k, v in match.items()):
					return self.messages.pop(index)
			time.sleep(0.02)
		raise AssertionError(f'no {kind} message (had {[m.get("type") for m in self.messages]})')

	def send(self, **message):
		self.client.send(message)

	def close(self):
		self.client.close()
		time.sleep(0.1)


def battle(a, b, format_name = '1v1', rule = 'random', team = None):
	a.send(type = 'challenge', to = b.client.me['username'], format = format_name, rule = rule, team = team)
	challenge = b.wait('challenge_in')
	b.send(type = 'answer', id = challenge['id'], accept = True, team = team)
	return a.wait('battle_start'), b.wait('battle_start')

# Plays the battle to the end with the first affordable move on the first possible target.
def play_out(players, starts, limit = 400):
	state = starts[0]['state']
	sides = {start['side']: player for player, start in zip(players, starts)}
	teams = starts[0]['teams']
	for _ in range(limit):
		if state['winner']:
			return state
		side, pos = state['waiting']
		player = sides[side]
		index = state['field'][side][pos]
		moves = teams[side][index]['moves']
		energy = state['teams'][side][index]['energy']
		usable = [m for m in moves if ATTACK_DATA[m]['cost'] < energy]
		if usable:
			move = usable[0]
			target_side = side if ATTACK_DATA[move]['target'] == 'player' else engine.other(side)
			target = next(p for p, i in enumerate(state['field'][target_side]) if i is not None and state['teams'][target_side][i]['health'] > 0)
			player.send(type = 'action', battle = starts[0]['battle'], action = {'type': 'move', 'move': move, 'target': [target_side, target]})
		else:
			player.send(type = 'action', battle = starts[0]['battle'], action = {'type': 'defend'})
		for p in players:
			events = p.wait('events')['events']
		state = events[-1]['state']
	raise AssertionError('battle did not finish')


class OnlineServerTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		start_server()

	def test_01_first_sign_in_registers_the_name(self):
		a = Tester('Simran')
		welcome = a.wait('welcome')
		self.assertEqual((welcome['username'], welcome['rating']), ('Simran', 1000))
		self.assertEqual(len(welcome['token']), 64)
		STATE['token'] = welcome['token']
		a.close()

	def test_02_token_signs_in_without_password(self):
		a = Tester('simran', token = STATE['token'])   # capitals do not matter
		self.assertEqual(a.wait('welcome')['username'], 'Simran')
		a.close()

	def test_03_wrong_password_is_rejected(self):
		a = Tester('Simran', password = 'Wrong#Pass9')
		self.assertEqual(a.wait('error')['code'], 'name_taken')
		self.assertEqual(a.client.status, 'failed')

	def test_04_bad_username_is_rejected(self):
		a = Tester("x'; DROP TABLE users;--")
		self.assertEqual(a.wait('error')['code'], 'bad_username')

	def test_05_search_shows_online_and_offline(self):
		a, b = Tester('Searcher'), Tester('Speedy')
		a.wait('welcome'); b.wait('welcome')
		a.send(type = 'search', username = 'speedy')
		found = a.wait('search_result')
		self.assertEqual((found['found'], found['online'], found['username']), (True, True, 'Speedy'))
		b.close()
		a.send(type = 'search', username = 'Speedy')
		self.assertEqual(a.wait('search_result')['online'], False)
		a.send(type = 'search', username = 'Nobody99')
		self.assertEqual(a.wait('search_result')['found'], False)
		a.close()

	def test_06_decline(self):
		a, b = Tester('Alpha1'), Tester('Bravo1')
		a.wait('welcome'); b.wait('welcome')
		a.send(type = 'challenge', to = 'Bravo1', format = '2v2', rule = 'random')
		challenge = b.wait('challenge_in')
		self.assertEqual((challenge['from'], challenge['format']), ('Alpha1', '2v2'))
		b.send(type = 'answer', id = challenge['id'], accept = False)
		self.assertEqual(a.wait('challenge_declined')['by'], 'Bravo1')
		a.close(); b.close()

	def test_07_challenge_offline_player_and_self(self):
		a = Tester('Alpha2')
		a.wait('welcome')
		a.send(type = 'challenge', to = 'Speedy', format = '1v1', rule = 'random')
		self.assertEqual(a.wait('error')['code'], 'player_offline')
		a.send(type = 'challenge', to = 'alpha2', format = '1v1', rule = 'random')
		self.assertEqual(a.wait('error')['code'], 'challenge_self')
		a.close()

	def test_08_full_battle_rating_and_history(self):
		a, b = Tester('Alpha3'), Tester('Bravo3')
		a.wait('welcome'); b.wait('welcome')
		start_a, start_b = battle(a, b, '3v3')
		self.assertEqual((start_a['side'], start_b['side'], start_a['field']), ('a', 'b', 3))
		self.assertEqual(start_a['teams'], start_b['teams'])   # both games build the same battle
		self.assertEqual(len(start_a['teams']['a']), 3)
		state = play_out([a, b], [start_a, start_b])
		end_a, end_b = a.wait('battle_end'), b.wait('battle_end')
		self.assertEqual(end_a['winner'], state['winner'])
		winner = a if state['winner'] == 'a' else b
		self.assertGreater(end_a['ratings'][state['winner']][1], 1000)
		self.assertEqual(sum(r[1] for r in end_a['ratings'].values()), 2000)   # points move from the loser to the winner
		winner.send(type = 'history')
		rows = winner.wait('history')['rows']
		self.assertTrue(rows[0]['won'])
		self.assertEqual(rows[0]['format'], '3v3')
		winner.send(type = 'leaderboard')
		board = winner.wait('leaderboard')['rows']
		self.assertEqual(board[0][0], winner.client.me['username'])
		winner.send(type = 'battle_log', id = rows[0]['id'])
		self.assertTrue(winner.wait('battle_log')['log'])
		STATE['pair'] = (a, b, start_a)

	def test_09_rematch(self):
		a, b, start = STATE['pair']
		a.send(type = 'rematch')
		self.assertEqual(b.wait('rematch_asked')['by'], 'Alpha3')
		b.send(type = 'rematch')
		new_a, new_b = a.wait('battle_start'), b.wait('battle_start')
		self.assertNotEqual(new_a['battle'], start['battle'])
		self.assertEqual(new_a['format'], '3v3')
		a.send(type = 'forfeit')
		self.assertEqual(b.wait('battle_end')['reason'], 'forfeit')
		a.send(type = 'leave'); b.send(type = 'leave')
		a.close(); b.close()

	def test_10_cheating_moves_are_rejected(self):
		a, b = Tester('Alpha4'), Tester('Bravo4')
		a.wait('welcome'); b.wait('welcome')
		start_a, start_b = battle(a, b, '1v1')
		state = start_a['state']
		side = state['waiting'][0]
		mover, waiter = (a, b) if side == 'a' else (b, a)
		other = engine.other(side)
		mover.send(type = 'action', battle = start_a['battle'], action = {'type': 'move', 'move': 'annihilate', 'target': [other, 0]})
		self.assertIn(mover.wait('action_rejected')['reason'], ('bad_move',))
		waiter.send(type = 'action', battle = start_a['battle'], action = {'type': 'defend'})
		self.assertEqual(waiter.wait('action_rejected')['reason'], 'not_your_turn')
		mover.send(type = 'action', battle = start_a['battle'], action = {'type': 'switch', 'index': 5})
		self.assertEqual(mover.wait('action_rejected')['reason'], 'bad_switch')
		STATE['slow'] = (a, b, start_a, mover)

	def test_11_time_runs_out_and_monster_defends(self):
		a, b, start, mover = STATE['slow']
		events = mover.wait('events', seconds = 4)['events']
		self.assertEqual(events[0]['kind'], 'defend')

	def test_12_disconnect_loses_after_grace_time(self):
		a, b, start, mover = STATE['slow']
		a.close()
		self.assertEqual(b.wait('opponent_left')['seconds'], 1.5)
		end = b.wait('battle_end', seconds = 6)
		self.assertEqual((end['winner'], end['reason']), ('b', 'disconnect'))
		b.close()

	def test_13_story_team_is_checked(self):
		a, b = Tester('Alpha5'), Tester('Bravo5')
		a.wait('welcome'); b.wait('welcome')
		cheat = [{'name': 'Draem', 'level': 999, 'xp': 0, 'health': 1, 'energy': 1}]
		a.send(type = 'challenge', to = 'Bravo5', format = '1v1', rule = 'story', team = cheat)
		self.assertEqual(a.wait('error')['code'], 'team_invalid')
		built = [{'name': 'Draem', 'moves': ['dark pulse']}, {'name': 'Charmadillo'}]
		start_a, start_b = battle(a, b, '2v2', 'built', built)
		self.assertEqual([m['name'] for m in start_a['teams']['a']], ['Draem', 'Charmadillo'])
		self.assertTrue(all(m['level'] == engine.ONLINE_LEVEL for m in start_a['teams']['b']))
		a.send(type = 'forfeit')
		b.wait('battle_end')
		a.close(); b.close()

	def test_14_reconnect_resumes_the_battle(self):
		a, b = Tester('Alpha6'), Tester('Bravo6')
		token = a.wait('welcome')['token']
		b.wait('welcome')
		start_a, _ = battle(a, b, '1v1')
		a.close()
		b.wait('opponent_left')
		again = Tester('Alpha6', token = token)
		again.wait('welcome')
		resumed = again.wait('battle_start')
		self.assertEqual((resumed['battle'], resumed['resume']), (start_a['battle'], True))
		again.send(type = 'forfeit')
		b.wait('battle_end')
		again.close(); b.close()

	def test_15_health_check_answers_normal_web_requests(self):
		import http.client
		connection = http.client.HTTPConnection('localhost', PORT, timeout = 5)
		connection.request('GET', '/')
		response = connection.getresponse()
		self.assertEqual(response.status, 200)
		self.assertIn(b'running', response.read())


if __name__ == '__main__':
	unittest.main()
