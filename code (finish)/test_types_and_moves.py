# test_types_and_moves.py
# Automated tests for Iteration 21: the new types, the type chart, four moves per type, priority,
# charge-up moves, accuracy, status effects, stat changes, cure items and the attack animations.
# Run with:  python test_types_and_moves.py   (no window is opened)

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from game_data import MONSTER_DATA, ATTACK_DATA, ITEM_DATA
from monster import Monster
import battle_rules as rules
from settings import asset

results = []
def check(name, expected, actual):
	results.append((name, expected, actual, expected == actual))

# ---------- new types ----------
for name, kind in (('Draem', 'psychic'), ('Cleaf', 'bug'), ('Larvea', 'bug'), ('Jacana', 'flying'), ('Atrox', 'poison'), ('Pouch', 'normal'), ('Friolera', 'ice')):
	check(f'{name} is {kind} type', kind, MONSTER_DATA[name]['stats']['element'])
check('the type chart covers all 13 types (rock added in Iteration 27; dark, ghost and fairy moves in Iteration 35)', 13, len(rules.TYPE_CHART))

# ---------- type chart ----------
check('fire is super effective on plant', (1.5, 'super'), rules.effectiveness('fire', 'plant'))
check('fire is weak against water', (0.67, 'weak'), rules.effectiveness('fire', 'water'))
check('bug is super effective on psychic', (1.5, 'super'), rules.effectiveness('bug', 'psychic'))
check('ice is super effective on flying', (1.5, 'super'), rules.effectiveness('ice', 'flying'))
check('normal is neutral against everything except rock', {(1, None)}, {rules.effectiveness('normal', other) for other in rules.TYPES if other != 'rock'})

# ---------- four moves per type ----------
by_type = {}
for name, data in ATTACK_DATA.items():
	by_type.setdefault(data['element'], []).append(name)
MAIN_TYPES = {data['stats']['element'] for data in MONSTER_DATA.values()}   # rock is only ever a second type
check('every main type has at least 4 moves', [], [kind for kind in MAIN_TYPES if len(by_type.get(kind, [])) < 4])
check('every main type has a priority move', [], [kind for kind in MAIN_TYPES if not any(rules.priority(m) > 0 for m in by_type.get(kind, []))])
check('every monster learns a move of its own type', [], [n for n, d in MONSTER_DATA.items() if not any(ATTACK_DATA[a]['element'] == d['stats']['element'] for a in d['abilities'].values())])
check('every move a monster learns exists', set(), {a for d in MONSTER_DATA.values() for a in d['abilities'].values()} - set(ATTACK_DATA))
check('Annihilate is a normal hit now; Inferno charges up instead (Iteration 34)', (0, True), (rules.priority('annihilate'), rules.is_charge('inferno')))
check('Solar Beam charges for a turn', True, rules.is_charge('solar beam'))
check('every move has an animation picture', [], [m for m, d in ATTACK_DATA.items() if not os.path.exists(asset('graphics', 'attacks', d['animation'] + '.png'))])

# ---------- accuracy ----------
check('a 100% move always hits', True, rules.hits('tackle', roll = 0.999))
check('Blizzard (75%) misses on a high roll', False, rules.hits('blizzard', roll = 0.8))
check('Blizzard hits on a low roll', True, rules.hits('blizzard', roll = 0.5))

# ---------- status effects ----------
target = Monster('Plumette', 10)
check('a burn lands on a low roll', 'burn', rules.try_status(target, 'burn', roll = 0.1))
check('only one status at a time', None, rules.try_status(target, 'poison sting', roll = 0.0))
health = target.health
can_act, message, damage = rules.start_of_turn(target)
check('a burn hurts at the start of the turn and the monster can still act', (True, 'status_hurt_burn', True), (can_act, message, target.health < health))
damage_burned = target.get_base_damage('tackle') if 'tackle' in ATTACK_DATA else 0
target.status = None
check('a burned monster hits for less', True, damage_burned < target.get_base_damage('tackle'))
fire_monster = Monster('Sparchu', 10)
check('fire monsters cannot be burned', None, rules.try_status(fire_monster, 'burn', roll = 0.0))
frozen = Monster('Finsta', 10)
frozen.status = 'freeze'
check('a frozen monster skips its turn (no thaw)', (False, 'status_frozen'), rules.start_of_turn(frozen, roll = 0.9)[:2])
check('a frozen monster can thaw', (True, 'status_thawed', None), rules.start_of_turn(frozen, roll = 0.1)[:2] + (frozen.status,))
sleepy = Monster('Finsta', 10)
rules.try_status(sleepy, 'hypnosis', roll = 0.0)
turns = 0
while sleepy.status == 'sleep' and turns < 10:
	rules.start_of_turn(sleepy)
	turns += 1
check('sleep lasts 1 to 3 turns, then the monster wakes', True, 2 <= turns <= 4 and sleepy.status is None)

# ---------- stat changes ----------
monster = Monster('Pouch', 10)
attack_before = monster.get_stat('attack')
check('Growl lowers attack by one stage', -1, rules.change_stage(monster, 'attack', -1))
check('lower attack means less attack', True, monster.get_stat('attack') < attack_before)
for _ in range(5):
	rules.change_stage(monster, 'attack', -1)
check('stages stop at -3', -3, monster.stages['attack'])
rules.end_of_battle(monster)
check('stat changes end with the battle', attack_before, monster.get_stat('attack'))

# ---------- cure items ----------
from main import Game
game = Game.__new__(Game)
game.inventory = {'antidote': 1}
poisoned = Monster('Plumette', 10)
poisoned.status = 'poison'
game.use_item('antidote', poisoned)
check('an antidote cures poison and is used up', (None, 0), (poisoned.status, game.inventory['antidote']))
game.inventory['antidote'] = 1
game.use_item('antidote', poisoned)
check('an antidote with nothing to cure is not wasted', 1, game.inventory['antidote'])
check('cure items are in the shop', True, all(name in __import__('game_data').SHOP_PRICES for name in ('burn_heal', 'thaw_spray', 'antidote', 'wake_bell', 'full_cure')))

# ---------- Iteration 27: dual types ----------
from monster import Monster
check('Charmadillo is fire and rock', ('fire', 'rock'), rules.types_of(Monster('Charmadillo', 30)))
check('water against fire/rock does 2.25 times the damage (Iteration 32)', (2.25, 'super'), rules.effectiveness('water', 'fire', 'rock'))
check('fire against water/ice is normal damage', (1, None), rules.effectiveness('fire', 'water', 'ice'))
check('a one-type monster has no second type', None, Monster('Sparchu', 5).element2)
check('Charmadillo learns Rock Throw', True, 'rock throw' in Monster('Charmadillo', 30).known_moves())

for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
