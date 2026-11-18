# test_core_subroutines.py
# Automated tests for the key subroutines, using the test data planned in section 2.6.
# Run with:  python test_core_subroutines.py   (no window or assets are needed)

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'   # run pygame without opening a window
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
from game_data import ATTACK_DATA
pygame.init()
pygame.display.set_mode((1, 1))

from monster import Monster
from battle import Battle
from game_data import MONSTER_DATA

results = []   # list of (test name, expected, actual, passed)

# Records one test result. Parameters: name, expected value, actual value
def check(name, expected, actual):
	passed = expected == actual
	results.append((name, expected, actual, passed))

# Runs func and returns the name of the exception it raises, or 'no error'
def error_of(func):
	try:
		func()
		return 'no error'
	except Exception as error:
		return type(error).__name__

# ---------- MONSTER STATS SYSTEM ----------
finsta = Monster('Finsta', 15)
check('Monster("Finsta", 15) health', 195, finsta.health)
check('Monster("Finsta", 15) energy', 255, finsta.energy)
check('Monster("Finsta", 15) level_up', 2250, finsta.level_up)
check('Monster("Finsta", 15) evolution', ('Gulfin', 34), finsta.evolution)
low = Monster('Finsta', 1)
check('Monster("Finsta", 1) health', 13, low.health)
check('Monster("Finsta", 1) level_up', 150, low.level_up)
check('Monster("Finsta", 0) rejected', 'ValueError', error_of(lambda: Monster('Finsta', 0)))
check('Monster("Finsta", "ten") rejected', 'TypeError', error_of(lambda: Monster('Finsta', 'ten')))
check('Monster("Pikachu", 15) rejected', 'ValueError', error_of(lambda: Monster('Pikachu', 15)))
finsta.health = -20; finsta.stat_limiter()
check('stat_limiter health -20', 0, finsta.health)
finsta.health = 250; finsta.stat_limiter()
check('stat_limiter health 250 (max 195)', 195, finsta.health)

# ---------- EXP & LEVEL SYSTEM (level 10, xp 0, level_up 1500) ----------
def xp_test(amount):
	m = Monster('Jacana', 10)
	m.update_xp(amount)
	return (m.level, round(m.xp, 2), m.level_up)
check('update_xp 500', (10, 500, 1500), xp_test(500))
check('update_xp 1499', (10, 1499, 1500), xp_test(1499))
check('update_xp 1500', (11, 0, 1650), xp_test(1500))
check('update_xp 4000 (two levels)', (12, 850, 1800), xp_test(4000))
check('update_xp -100 ignored', (10, 0, 1500), xp_test(-100))
check('update_xp "xp" rejected', 'TypeError', error_of(lambda: xp_test('xp')))

# fake battle with only the parts award_xp / apply_attack need
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
	battle.monster_frames = {'attacks': {data['animation']: [pygame.Surface((4, 4))] for data in ATTACK_DATA.values()}}
	battle.sounds = {name: FakeSound() for name in battle.monster_frames['attacks']}
	battle.check_death = lambda: None
	battle.crit_chance = 0   # Iteration 24: no random critical hits, so the damage is exact
	return battle

battle = make_battle()
team = [FakeSprite(Monster('Jacana', 10), battle.player_sprites) for _ in range(3)]
battle.award_xp(Monster('Cleaf', 14))
check('award_xp level 14, 3 active monsters', 466.67, round(team[0].monster.xp, 2))
empty = make_battle()
check('award_xp with 0 active monsters', 'no error', error_of(lambda: empty.award_xp(Monster('Cleaf', 14))))

# ---------- DAMAGE FORMULA (level 50 Charmadillo, fire, base 400) ----------
def damage(target_name, attack, amount, defending = False):
	battle = make_battle()
	target = FakeSprite(Monster(target_name, 50), battle.opponent_sprites)
	target.monster.defending = defending
	before = target.monster.health
	battle.apply_attack(target, attack, amount)
	return round(before - target.monster.health, 2)
check('fire vs Pluma (strong, x1.5 and damage scale 0.6, Iteration 32)', 252, damage('Pluma', 'flame burst', 400))
check('fire vs Finiette (water/ice: weak x strong = normal, Iteration 27)', 138, damage('Finiette', 'flame burst', 400))
check('scratch vs Pluma (neutral)', 100.8, damage('Pluma', 'scratch', 240))
check('fire vs Pluma defending', 180, damage('Pluma', 'flame burst', 400, defending = True))
check('attack "mega blast" rejected safely', 'no error', error_of(lambda: damage('Pluma', 'mega blast', 400)))
check('target None rejected safely', 'no error', error_of(lambda: make_battle().apply_attack(None, 'flame burst', 400)))
# Iteration 24: a critical hit does 1.5 times the damage
def critical_damage():
	battle = make_battle()
	battle.crit_chance = 1
	battle.timers, battle.log = {}, []
	target = FakeSprite(Monster('Pluma', 50), battle.opponent_sprites)
	before = target.monster.health
	battle.apply_attack(target, 'flame burst', 400)
	return round(before - target.monster.health, 2)
check('a critical hit does 1.5x damage', 378, critical_damage())

# ---------- TURN ORDER: opponent with no affordable attacks ----------
battle = make_battle()
tired = FakeSprite(Monster('Jacana', 10), battle.opponent_sprites)
FakeSprite(Monster('Pluma', 50), battle.player_sprites)
tired.monster.energy = 0
battle.current_monster = tired
battle.update_all_monsters = lambda option: None
battle.opponent_attack()
check('opponent with 0 energy defends instead', True, tired.monster.defending)

# ---------- LOSING A BATTLE (Iteration 12) ----------
from main import Game
lost_calls = []
battle = make_battle()
FakeSprite(Monster('Jacana', 10), battle.opponent_sprites)   # opponent still has a monster, player has none
battle.battle_over = False
battle.character = None
battle.monster_data = {'player': {0: Monster('Pluma', 50)}, 'opponent': {}}
battle.end_battle = lambda character, lost = False: lost_calls.append(lost)
battle.check_end_battle()
battle.check_end_battle()   # called again on the next frame
check('all player monsters fainted: end_battle called once with lost = True', [True], lost_calls)

class FakeSound:
	def stop(self): pass
	def play(self, *args): pass
game = Game.__new__(Game)   # a Game without opening a window, only to test end_battle and heal_party
game.audio = {'battle': FakeSound(), 'overworld': FakeSound()}
game.tint_mode = 'untint'
game.player_monsters = {0: Monster('Pluma', 50)}
game.player_monsters[0].health, game.player_monsters[0].energy = 0, 0
game.end_battle(None, lost = True)
check('lost battle starts the defeat fade', ('defeat', 'tint'), (game.transition_target, game.tint_mode))
game.heal_party()
check('heal_party restores health and energy', (1150, 1300), (game.player_monsters[0].health, game.player_monsters[0].energy))

# ---------- print results ----------
for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
