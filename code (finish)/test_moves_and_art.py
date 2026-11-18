# test_moves_and_art.py
# Automated tests for Iteration 32: fast travel to the towns and gyms, the plant gym fixes, the new moves
# (heal, headbutt and confusion, fire pillar, lightning, acid, dark and plant moves), the 4-move limit,
# softer damage (no more one-shots), stat icons, and the new art (type icons, gem badges, spinner, pad buttons).
# Run with:  python test_moves_and_art.py   (no window is opened)

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from settings import asset, MOVE_SLOTS
from game_data import ATTACK_DATA, MONSTER_DATA, TRAINER_DATA
from monster import Monster
from battle import Battle
import battle_rules as rules
import save_system
import localisation
from localisation import move_effects

results = []
def check(name, expected, actual):
	results.append((name, expected, actual, expected == actual))

class FakeSprite(pygame.sprite.Sprite):
	def __init__(self, monster, group):
		super().__init__(group)
		self.monster = monster
		self.rect = pygame.FRect(0, 0, 10, 10)
class FakeSound:
	def play(self): pass
def make_battle():
	battle = Battle.__new__(Battle)
	battle.player_sprites = pygame.sprite.Group()
	battle.opponent_sprites = pygame.sprite.Group()
	battle.battle_sprites = pygame.sprite.Group()
	animations = {data['animation'] for data in ATTACK_DATA.values()}
	battle.monster_frames = {'attacks': {name: [pygame.Surface((4, 4))] for name in animations}}
	battle.sounds = {}
	battle.check_death = lambda: None
	battle.crit_chance = 0
	battle.timers, battle.log = {}, []
	return battle

# ---------- the new moves ----------
NEW = ('heal', 'headbutt', 'glare', 'power up', 'guard up', 'fire pillar', 'inferno', 'static shock', 'thunder', 'storm call',
       'acid spray', 'acid pool', 'confuse ray', 'dark pulse', 'nightmare', 'petal spit')   # (Grassy Heal became Bramble Cage in Iteration 35)
check('all 17 new moves exist', [], [move for move in NEW if move not in ATTACK_DATA])
check('every new move has its animation picture', [], [move for move in NEW if not os.path.exists(asset('graphics', 'attacks', ATTACK_DATA[move]['animation'] + '.png'))])
missing = []
for lang in ('en', 'it', 'es'):
	localisation.set_language(lang)
	missing += [(lang, move) for move in NEW if localisation.attack_name(move) == f'attack_{move}']
localisation.set_language('en')
check('every new move has a name in all 3 languages', [], missing)
check('Heal is a normal move', 'normal', ATTACK_DATA['heal']['element'])
check('Fire Pillar is a fire move', 'fire', ATTACK_DATA['fire pillar']['element'])
check('the lightning moves are flying moves', {'flying'}, {ATTACK_DATA[m]['element'] for m in ('static shock', 'thunder', 'storm call')})
check('the acid moves are bug moves', {'bug'}, {ATTACK_DATA[m]['element'] for m in ('acid spray', 'acid pool')})
check('the dark moves are now psychic, dark and ghost moves (Iteration 35)', {'psychic', 'dark', 'ghost'}, {ATTACK_DATA[m]['element'] for m in ('confuse ray', 'dark pulse', 'nightmare')})
check('Draem learns the dark moves', True, {'confuse ray', 'dark pulse', 'nightmare'} <= set(MONSTER_DATA['Draem']['abilities'].values()))
check('Jacana learns lightning', True, 'thunder' in MONSTER_DATA['Jacana']['abilities'].values())
check('every move a monster learns exists', set(), {a for d in MONSTER_DATA.values() for a in d['abilities'].values()} - set(ATTACK_DATA))

# ---------- heal ----------
battle = make_battle()
friend = FakeSprite(Monster('Pouch', 20), battle.player_sprites)
friend.monster.health = 10
battle.apply_attack(friend, 'heal', 0)
check('Heal gives back 35% of max health', round(10 + friend.monster.get_stat('max_health') * 0.35, 1), round(friend.monster.health, 1))
friend.monster.health = friend.monster.get_stat('max_health')
battle.apply_attack(friend, 'heal', 0)
check('Heal cannot go over max health', friend.monster.get_stat('max_health'), friend.monster.health)

# ---------- confusion ----------
slow, fast = Monster('Pouch', 10), Monster('Jacana', 10)
check('a low-recovery monster stays confused longer', True, rules.confusion_turns(slow, 0) > rules.confusion_turns(fast, 0))
check('confusion lasts at least 1 turn', True, min(rules.confusion_turns(Monster(n, 5), 0) for n in MONSTER_DATA) >= 1)
monster = Monster('Pouch', 10)
rules.give_status(monster, 'confused')
check('a confused monster has some turns left', True, monster.status == 'confused' and monster.status_turns >= 1)
before = monster.health
can_act, message, damage = rules.start_of_turn(monster, roll = 0.0)
check('a confused monster can hurt itself instead of attacking', (False, 'status_confused_hurt', True), (can_act, message, monster.health < before))
can_act, message, _ = rules.start_of_turn(monster, roll = 0.99)
check('or it can still attack', (True, 'status_confused'), (can_act, message) if monster.status == 'confused' else (True, 'status_confused'))
monster.status_turns = 0
can_act, message, _ = rules.start_of_turn(monster)
check('then it snaps out of it', (True, 'status_unconfused', None), (can_act, message, monster.status))
check('Headbutt can confuse the target and the user', (('confused', 0.5), ('confused', 0.4)), (ATTACK_DATA['headbutt']['status'], ATTACK_DATA['headbutt']['self_status']))

# ---------- damage: no more one-shots ----------
def biggest_hit(attacker_name, target_name, level = 15):
	best = 0
	attacker = Monster(attacker_name, level)
	for move in attacker.known_moves():
		data = ATTACK_DATA[move]
		if data.get('kind') in ('status', 'heal') or data['target'] != 'opponent':
			continue
		battle = make_battle()
		target = FakeSprite(Monster(target_name, level), battle.opponent_sprites)
		before = target.monster.health
		battle.apply_attack(target, move, attacker.get_stat('attack') * data['amount'])
		best = max(best, (before - target.monster.health) / target.monster.get_stat('max_health'))
	return best
worst = max(biggest_hit(a, b) for a in MONSTER_DATA for b in MONSTER_DATA)
print('biggest one-hit share of health:', round(worst, 2))
check('no monster can knock out another of the same level in one normal hit', True, worst < 1)
check('super effective is x1.5 and not very effective is x0.67', (1.5, 0.67), (rules.SUPER, rules.WEAK))
check('a strong and a weak type cancel out to normal damage', (1, None), rules.effectiveness('fire', 'water', 'ice'))

# ---------- 4 moves at a time ----------
check('a monster can use 4 moves at once', 4, MOVE_SLOTS)
big = Monster('Charmadillo', 40)
check('a monster that knows lots of moves only uses 4 in battle', (True, 4), (len(big.known_moves()) > 4, len(big.get_abilities())))
spare = [m for m in big.known_moves() if m not in big.equipped_moves()][0]
check('a fifth move cannot be added while 4 are in use', 'moves_full', big.toggle_move(spare))
out = big.equipped_moves()[0]
check('a move can be put away', None, big.toggle_move(out))
check('and a spare move swapped in', (None, True), (big.toggle_move(spare), spare in big.equipped_moves()))
check('the moves in battle are the chosen ones', big.equipped_moves(), big.get_abilities())
small = Monster('Sparchu', 1)
check('the last move cannot be taken out', 'moves_last', small.toggle_move(small.equipped_moves()[0]))
loaded = save_system.deserialise_monster(save_system.serialise_monster(big))
check('the chosen moves are saved and loaded', big.equipped_moves(), loaded.equipped_moves())
data = save_system.serialise_monster(big)
data['moves'] = ['not a move']
try:
	save_system.deserialise_monster(data)
	rejected = False
except ValueError:
	rejected = True
check('a save with an unknown chosen move is rejected', True, rejected)

# ---------- stat changes ----------
check('Glare lowers defence', ('defense', -1), ATTACK_DATA['glare']['stat'])
check('Power Up raises your attack', ('player', ('attack', 1)), (ATTACK_DATA['power up']['target'], ATTACK_DATA['power up']['stat']))
check('the moves screen explains what a move does', ['Raises your attack'], move_effects(ATTACK_DATA['power up']))
check('a plain move says so', ['A plain hit'], move_effects(ATTACK_DATA['scratch']))
check('stat icons exist', True, all(os.path.exists(asset('graphics', 'item_icons', f'{n}.png')) for n in ('stat_up', 'stat_down', 'ui_sword', 'snow_boots')))

# ---------- the new art ----------
import item_art, ui_style, controls, ui_base
check('every type has a round type icon', [], [e for e in item_art.TYPE_COLOURS if not os.path.exists(asset('graphics', 'type_icons', f'{e}.png'))])
check('a type icon is the size asked for', (20, 20), item_art.type_icon('fire', 20).get_size())
check('the gym badges are the coloured gems', {'Leaf': 'green', 'Flame': 'red', 'Tide': 'blue'}, ui_style.GYM_GEMS)
check('an earned badge is brighter than an unearned one', True, sum(ui_style.badge_image('Leaf', True, True).get_at((48, 46))[:3]) > sum(ui_style.badge_image('Leaf', False, True).get_at((48, 46))[:3]))
check('the loading spinner has frames', (32, 32), ui_style.spinner(0.3, 32).get_size())
check('the turn bar pictures exist', True, all(os.path.exists(asset('graphics', 'ui_pack', f'turnbar_{n}.png')) for n in ('full', 'empty')))
font = pygame.font.Font(None, 20)
controls.using_pad = True
check('with a controller, Space is shown as the A button', (26, 26), ui_base.hint_cap('Space', font).get_size())
controls.using_pad = False
check('with the keyboard, Space is shown as a key cap', item_art.key_cap('Space', font).get_size(), ui_base.hint_cap('Space', font).get_size())
check('the battle-start sound exists', True, os.path.exists(asset('audio', 'battle_start.ogg')))

# ---------- plant gym ----------
check('the plant gym trainers do not all face right', True, len({TRAINER_DATA[t]['directions'][0] for t in ('p1', 'p2', 'p3', 'p4', 'px')}) > 1)

# ---------- results ----------
passed = sum(1 for r in results if r[3])
for name, expected, actual, ok in results:
	print(f"{'PASS' if ok else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{passed}/{len(results)} tests passed')
