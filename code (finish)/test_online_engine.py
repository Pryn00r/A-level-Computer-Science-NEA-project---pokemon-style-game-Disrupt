# test_online_engine.py
# Iteration 37: unit tests for the online battle rules (online_engine.py), with no server or window.
# Run with:  python -m unittest test_online_engine

import unittest

import online_engine as engine
from monster import Monster
from game_data import ATTACK_DATA


def team(*names):
	return [engine.team_monster(name) for name in names]

def first_move(match, damaging = True):
	side, pos = match.waiting
	monster = match.monster_at(side, pos)
	for move in monster.get_abilities(all = False):
		data = ATTACK_DATA[move]
		if (data.get('kind') not in ('status', 'heal') and data['amount'] > 0) == damaging and not engine.rules.is_charge(move) and engine.rules.priority(move) >= 0:
			return move
	return None


class EngineTests(unittest.TestCase):
	def test_faster_monster_moves_first(self):
		fast, slow = engine.team_monster('Jacana'), engine.team_monster('Pouch')
		match = engine.Match([slow], [fast], 1, seed = 1)
		self.assertGreater(fast.get_stat('speed'), slow.get_stat('speed'))
		self.assertEqual(match.waiting, ('b', 0))

	def test_same_speed_goes_to_side_a(self):
		match = engine.Match(team('Draem'), team('Draem'), 1, seed = 1)
		self.assertEqual(match.waiting, ('a', 0))

	def test_wrong_player_cannot_act(self):
		match = engine.Match(team('Draem'), team('Draem'), 1, seed = 1)
		self.assertEqual(match.act('b', {'type': 'defend'}), 'not_your_turn')

	def test_move_it_does_not_know_is_rejected(self):
		match = engine.Match(team('Draem'), team('Pouch'), 1, seed = 1)
		side = match.waiting[0]
		self.assertEqual(match.act(side, {'type': 'move', 'move': 'inferno', 'target': ['b', 0]}), 'bad_move')

	def test_attack_on_own_side_is_rejected(self):
		match = engine.Match(team('Charmadillo'), team('Charmadillo'), 1, seed = 1)
		side = match.waiting[0]
		move = first_move(match)
		self.assertEqual(match.act(side, {'type': 'move', 'move': move, 'target': [side, 0]}), 'bad_target')

	def test_bad_data_is_rejected(self):
		match = engine.Match(team('Draem'), team('Pouch'), 1, seed = 1)
		for action in (None, 'defend', {'type': 'dance'}, {'type': 'move', 'move': 'x'}, {'type': 'switch', 'index': '0'}):
			self.assertIsNotNone(match.act('a', action))

	def test_damage_is_taken_and_energy_paid(self):
		match = engine.Match(team('Charmadillo'), team('Charmadillo'), 1, seed = 3)
		side = match.waiting[0]
		target = match.monster_at(engine.other(side), 0)
		attacker = match.monster_at(side, 0)
		move = first_move(match)
		energy = attacker.energy
		health = target.health
		match.take_events()
		self.assertIsNone(match.act(side, {'type': 'move', 'move': move, 'target': [engine.other(side), 0]}))
		events = match.take_events()
		attack = next(e for e in events if e['kind'] == 'attack')
		self.assertLess(attacker.energy, energy + attacker.get_stat('recovery'))
		if not attack.get('missed'):
			self.assertAlmostEqual(health - target.health, attack['damage'], places = 1)

	def test_fainted_monster_is_replaced_from_the_bench(self):
		match = engine.Match(team('Draem', 'Pouch'), team('Jacana', 'Atrox'), 1, seed = 2)
		match.monster_at('b', 0).health = 0
		match.after_action()
		self.assertEqual(match.field['b'], [1])
		self.assertTrue(any(e['kind'] == 'faint' and e['replacement'] == 1 for e in match.take_events()))

	def test_last_monster_fainting_ends_the_battle(self):
		match = engine.Match(team('Draem'), team('Pouch'), 1, seed = 2)
		match.monster_at('b', 0).health = 0
		match.after_action()
		self.assertEqual(match.winner, 'a')
		self.assertEqual(match.act('a', {'type': 'defend'}), 'battle_over')

	def test_switch(self):
		match = engine.Match(team('Draem', 'Pouch', 'Atrox'), team('Draem'), 1, seed = 1)
		self.assertEqual(match.act('a', {'type': 'switch', 'index': 2}), None)
		self.assertEqual(match.field['a'], [2])
		self.assertEqual(engine.Match(team('Draem'), team('Draem'), 1).act('a', {'type': 'switch', 'index': 0}), 'bad_switch')

	def test_forfeit_and_timeout(self):
		match = engine.Match(team('Draem'), team('Pouch'), 1, seed = 1)
		side = match.waiting[0]
		match.take_events()
		match.timeout(side)
		self.assertEqual(match.take_events()[0]['kind'], 'defend')
		match.forfeit('a')
		self.assertEqual(match.winner, 'b')

	def test_formats(self):
		for name, (size, field) in engine.FORMATS.items():
			match = engine.Match(engine.random_team(size), engine.random_team(size), field, seed = 4)
			self.assertEqual(len(match.field['a']), field)
			self.assertEqual(len(match.teams['b']), size)

	def test_whole_battles_always_finish(self):
		import random
		for seed in range(5):
			rng = random.Random(seed)
			match = engine.Match(engine.random_team(6, rng), engine.random_team(6, rng), 3, seed = seed)
			for _ in range(1000):
				if match.winner:
					break
				side, pos = match.waiting
				monster = match.monster_at(side, pos)
				usable = monster.get_abilities(all = False)
				if not usable:
					match.act(side, {'type': 'defend'})
					continue
				move = rng.choice(usable)
				target_side = side if ATTACK_DATA[move]['target'] == 'player' else engine.other(side)
				pos_target = rng.choice([p for s, p in match.active() if s == target_side])
				self.assertIsNone(match.act(side, {'type': 'move', 'move': move, 'target': [target_side, pos_target]}))
			self.assertIn(match.winner, ('a', 'b'))

	def test_team_checks(self):
		self.assertEqual(engine.build_team('built', [{'name': 'Sparchu'}], 1)[1], 'team_invalid')   # not fully evolved
		self.assertEqual(engine.build_team('built', [{'name': 'Draem'}] * 7, 6)[1], 'team_too_big')
		self.assertEqual(engine.build_team('built', [], 1)[1], 'team_empty')
		self.assertEqual(engine.build_team('story', [{'name': 'Draem', 'level': 500, 'xp': 0, 'health': 1, 'energy': 1}], 1)[1], 'team_invalid')
		built, error = engine.build_team('built', [{'name': 'Draem', 'moves': ['dark pulse', 'not a move']}], 1)
		self.assertEqual(error, 'team_invalid')
		built, error = engine.build_team('built', [{'name': 'Draem'}, {'name': 'Atrox'}, {'name': 'Pouch'}], 2)
		self.assertEqual((error, len(built), built[0].level), (None, 2, engine.ONLINE_LEVEL))

	def test_elo(self):
		self.assertEqual(engine.elo(1000, 1000), (1016, 984))
		winner, loser = engine.elo(800, 1200)    # beating a much stronger player gains more
		self.assertEqual(winner - 800, 29)
		winner, loser = engine.elo(1200, 800)
		self.assertEqual(winner - 1200, 3)
		self.assertEqual(sum(engine.elo(1100, 950)), 2050)   # points are never created or lost


class ServerAddressTests(unittest.TestCase):
	def test_addresses(self):
		from online_client import normalise_address, DEFAULT_SERVER
		self.assertEqual(normalise_address(''), DEFAULT_SERVER)
		self.assertEqual(normalise_address(' 192.168.1.20 '), 'ws://192.168.1.20:8765')
		self.assertEqual(normalise_address('10.0.0.5:9000'), 'ws://10.0.0.5:9000')
		self.assertEqual(normalise_address('wss://disrupt.onrender.com'), 'wss://disrupt.onrender.com')
		for bad in ('192.168.1', '300.1.1.1', 'hello', '1.2.3.4:99999', '1.2.3.4:abc'):
			self.assertIsNone(normalise_address(bad), bad)


if __name__ == '__main__':
	unittest.main()
