# test_online_battle.py
# Iteration 37: two copies of the online battle screen (one for each player) play whole battles against a
# real server on this computer. After every battle both games must show exactly what the server says:
# the same health, energy, status and the same monsters on the field (no "desync").
# Run with:  python test_online_battle.py

import importlib.util, sys
if importlib.util.find_spec('websockets') is None:   # the online tests need:  pip install websockets
	print('SKIPPED - websockets is not installed (pip install websockets)')
	sys.exit(0)
import asyncio
import os
import tempfile
import threading
import time

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import main
import save_system
import online_server
from online_client import OnlineClient
from online_db import Database
from online_screens import NetBattle
from game_data import ATTACK_DATA

PORT = 8798
results = []

def check(name, expected, actual):
	passed = expected == actual
	results.append(passed)
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected!r} | actual {actual!r}")

def start_server():
	online_server.TURN_SECONDS = 30
	ready = threading.Event()
	database = Database(os.path.join(tempfile.mkdtemp(), 'battle.db'))
	def run():
		asyncio.new_event_loop().run_until_complete(online_server.main(PORT, database, lambda *_: ready.set()))
	threading.Thread(target = run, daemon = True).start()
	ready.wait(10)

def wait_for(client, kind, store, seconds = 8):
	end = time.time() + seconds
	while time.time() < end:
		store.extend(client.pump())
		for message in store:
			if message.get('type') == kind:
				store.remove(message)
				return message
		time.sleep(0.02)
	raise AssertionError(f'no {kind}')

# Picks a move like a player would, through the same methods the battle menu uses.
def choose(net):
	sprite = net.current_monster
	abilities = sprite.monster.get_abilities(all = False)
	if not abilities:
		net.choose_defend()
		return
	attack = abilities[len(net.log) % len(abilities)]
	group = net.player_sprites if ATTACK_DATA[attack]['target'] == 'player' else net.opponent_sprites
	target = sorted(group.sprites(), key = lambda s: s.pos_index)[0]
	net.use_move(sprite, target, attack)

def play(game, a, b, format_name):
	inbox = {'a': [], 'b': []}
	a.send({'type': 'challenge', 'to': 'Bravo', 'format': format_name, 'rule': 'random'})
	invite = wait_for(b, 'challenge_in', inbox['b'])
	b.send({'type': 'answer', 'id': invite['id'], 'accept': True})
	start_a, start_b = wait_for(a, 'battle_start', inbox['a']), wait_for(b, 'battle_start', inbox['b'])
	nets = {'a': NetBattle(game, start_a, a.send), 'b': NetBattle(game, start_b, b.send)}
	clients = {'a': a, 'b': b}
	final, ends, choices = None, {}, 0
	deadline = time.time() + 240
	while time.time() < deadline:
		for side in ('a', 'b'):
			for message in clients[side].pump() + inbox[side]:
				if message['type'] == 'events':
					nets[side].events.extend(message['events'])
					final = message['events'][-1]['state']
				elif message['type'] == 'battle_end':
					ends[side] = message
			inbox[side] = []
			net = nets[side]
			net.update(0.1)
			if net.current_monster is not None and net.selection_mode == 'general' and not net.events:
				choose(net)
				choices += 1
		if len(ends) == 2 and all(n.ended and not n.events and not n.busy() for n in nets.values()):
			break
		time.sleep(0.005)
	return nets, final, ends, choices, start_a

def compare(name, nets, state):
	for side, net in nets.items():
		same = True
		for team_side in ('a', 'b'):
			for monster, data in zip(net.teams[team_side], state['teams'][team_side]):
				same &= abs(monster.health - data['health']) < 0.01 and abs(monster.energy - data['energy']) < 0.01 and monster.status == data['status']
		check(f'{name}: game {side} shows the same health, energy and status as the server', True, same)
		for team_side in ('a', 'b'):
			group = net.player_sprites if team_side == net.me else net.opponent_sprites
			on_field = sorted((s.pos_index, s.index) for s in group if s.monster.health > 0)
			expected = sorted((pos, index) for pos, index in enumerate(state['field'][team_side]) if index is not None and state['teams'][team_side][index]['health'] > 0)
			check(f'{name}: game {side} has the same monsters on the field for side {team_side}', expected, on_field)


start_server()
root = tempfile.mkdtemp()
main.ProfileManager = lambda: save_system.ProfileManager(root)
game = main.Game()
a, b = OnlineClient(f'ws://localhost:{PORT}', 5), OnlineClient(f'ws://localhost:{PORT}', 5)
a.connect('Alpha', 'Strong#Pass1')
b.connect('Bravo', 'Strong#Pass1')
store = []
wait_for(a, 'welcome', store); wait_for(b, 'welcome', [])

for format_name in ('1v1', '2v2', '6v6'):
	nets, final, ends, choices, start = play(game, a, b, format_name)
	check(f'{format_name}: both games got the result', 2, len(ends))
	check(f'{format_name}: both games agree who won', True, len(ends) == 2 and ends['a']['winner'] == ends['b']['winner'] == final['winner'])
	check(f'{format_name}: players had to choose moves', True, choices > 0)
	check(f'{format_name}: the right number of monsters came out', min(3, {'1v1': 1, '2v2': 2, '6v6': 3}[format_name]), len(start['state']['field']['a']))
	compare(format_name, nets, final)
	loser = 'b' if final['winner'] == 'a' else 'a'
	check(f'{format_name}: the loser has no monsters left standing', 0, sum(1 for m in nets['a'].teams[loser] if m.health > 0))
	a.send({'type': 'leave'}); b.send({'type': 'leave'})
	time.sleep(0.2)
	a.pump(); b.pump()

print(f'\n{sum(results)}/{len(results)} tests passed')
