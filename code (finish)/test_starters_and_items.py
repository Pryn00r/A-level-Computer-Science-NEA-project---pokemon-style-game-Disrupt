# test_starters_and_items.py
# Automated tests for Iteration 13: starter choice, nicknames, held items, badges, zone tiers and saving.
# Run with:  python test_starters_and_items.py   (no window or assets are needed)

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'   # run pygame without opening a window
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from monster import Monster
from main import Game
from game_data import TRAINER_DATA, BADGE_DATA, WILD_ENCOUNTERS, MONSTER_DATA
from save_system import serialise_monster, deserialise_monster

results = []   # list of (test name, expected, actual, passed)

# Records one test result. Parameters: name, expected value, actual value
def check(name, expected, actual):
	results.append((name, expected, actual, expected == actual))

# Runs func and returns the name of the exception it raises, or 'no error'
def error_of(func):
	try:
		func()
		return 'no error'
	except Exception as error:
		return type(error).__name__

# A Game without opening a window or loading any images
game = Game.__new__(Game)
game.inventory = {'potion': 5, 'ether': 3}
game.toasts = []
game.reset_progress()   # Iteration 16: monster index and quests

# ---------- STARTER CHOICE ----------
party = game.create_starting_party('Sparchu', 'Blaze')
check('starting party has only the starter', [('Sparchu', 5)], [(m.name, m.level) for m in party.values()])
check('starter keeps its nickname', 'Blaze', party[0].display_name)
check('starter "Atrox" rejected (not a starter)', 'ValueError', error_of(lambda: game.create_starting_party('Atrox')))

# ---------- NICKNAMES ----------
monster = Monster('Finsta', 10)
check('nickname "Bubbles" accepted', (True, 'Bubbles'), (monster.set_nickname('Bubbles'), monster.display_name))
check('nickname 13 characters rejected', (False, 'Bubbles'), (monster.set_nickname('A' * 13), monster.display_name))
check('nickname 12 characters accepted', True, monster.set_nickname('A' * 12))
check('empty nickname goes back to species name', (True, 'Finsta'), (monster.set_nickname('   '), monster.display_name))
check('nickname of a number rejected', False, monster.set_nickname(123))

# ---------- HELD ITEMS ----------
plain, held = Monster('Sparchu', 10), Monster('Sparchu', 10)
held.held_item = 'power_band'
check('power band: 25% more damage', round(plain.get_base_damage('scratch') * 1.25, 2), round(held.get_base_damage('scratch'), 2))
held.held_item = 'vital_charm'
check('vital charm: 20% more max health', round(plain.get_stat('max_health') * 1.2, 2), round(held.get_stat('max_health'), 2))
held.held_item = 'focus_ring'
check('focus ring: attack costs 25% less', 15.0, held.attack_cost('scratch'))
held.held_item = 'wise_feather'
held.update_xp(100)
check('wise feather: 50% more xp', 150, held.xp)

game.player_monsters = {0: Monster('Sparchu', 10)}
game.inventory = {'power_band': 1, 'focus_ring': 1}
target = game.player_monsters[0]
game.give_held_item('power_band', target)
check('give item: monster holds it, bag goes down', ('power_band', 0), (target.held_item, game.inventory['power_band']))
game.give_held_item('focus_ring', target)
check('give second item: old item goes back to the bag', ('focus_ring', 1, 0), (target.held_item, game.inventory['power_band'], game.inventory['focus_ring']))
check('give item you do not own: nothing changes', 'focus_ring', (game.give_held_item('vital_charm', target), target.held_item)[1])
game.take_held_item(target)
check('take item: back in the bag', (None, 1), (target.held_item, game.inventory['focus_ring']))

# ---------- BADGES ----------
for data in TRAINER_DATA.values():
	data['defeated'] = False
check('next badge trainer at the start is o1', 'o1', game.next_badge_trainer())
game.inventory = {}
game.award_badge('o1')
TRAINER_DATA['o1']['defeated'] = True
check('beating o1 gives its held item', 1, game.inventory.get(BADGE_DATA['o1']['reward']['held']))
check('earned badges', ['o1'], game.earned_badges())
check('next badge trainer after o1 is o3', 'o3', game.next_badge_trainer())
check('ordinary trainer gives no badge', 'no error', error_of(lambda: game.award_badge('p1')))
check('every badge trainer exists in TRAINER_DATA', True, all(trainer in TRAINER_DATA for trainer in BADGE_DATA))

# ---------- ZONE TIERS ----------
class Patch:   # stands in for a grass patch sprite
	def __init__(self, biome):
		self.biome, self.monsters, self.level = biome, ['Atrox'], 10

for biome, data in WILD_ENCOUNTERS.items():
	monsters = [m for _ in range(200) for m in game.create_wild_monsters(Patch(biome)).values()]
	check(f'{biome}: only monsters from its tier', True, all(m.name in data['monsters'] for m in monsters))
	check(f'{biome}: levels inside {data["levels"]}', True, all(data['levels'][0] <= m.level <= data['levels'][1] for m in monsters))
	check(f'{biome}: 1 to {data["pick"]} monsters per battle', True, all(1 <= len(game.create_wild_monsters(Patch(biome))) <= data['pick'] for _ in range(50)))
check('forest only has first-stage monsters', True, all(not any(d['evolve'] and d['evolve'][0] == name for d in MONSTER_DATA.values()) for name in WILD_ENCOUNTERS['forest']['monsters']))

# ---------- SAVING ----------
saved = Monster('Gulfin', 12)
saved.set_nickname('Finn')
saved.held_item = 'vital_charm'
loaded = deserialise_monster(serialise_monster(saved))
check('nickname and held item are saved and loaded', ('Finn', 'vital_charm'), (loaded.nickname, loaded.held_item))
old = {'name': 'Gulfin', 'level': 12, 'xp': 0, 'health': 10, 'energy': 5}
check('save from before Iteration 13 still loads', ('Gulfin', None), (deserialise_monster(old).display_name, deserialise_monster(old).held_item))
check('unknown held item in a save rejected', 'ValueError', error_of(lambda: deserialise_monster(dict(old, held_item = 'cheat_item'))))
check('nickname too long in a save rejected', 'ValueError', error_of(lambda: deserialise_monster(dict(old, nickname = 'X' * 40))))

# ---------- print results ----------
for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
