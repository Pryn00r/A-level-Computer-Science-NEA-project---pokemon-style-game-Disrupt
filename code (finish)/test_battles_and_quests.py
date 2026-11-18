# test_battles_and_quests.py
# Automated tests for Iteration 16: battle freezes, running away, WASD controls, shiny monsters,
# the monster index and quests.
# Run with:  python test_battles_and_quests.py   (no window or assets are needed)

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'   # run pygame without opening a window
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import controls
from monster import Monster
from main import Game
from battle import Battle
from game_data import TRAINER_DATA, QUEST_DATA, MONSTER_DATA
from save_system import serialise_monster, deserialise_monster

results = []   # list of (test name, expected, actual, passed)

# Records one test result. Parameters: name, expected value, actual value
def check(name, expected, actual):
	results.append((name, expected, actual, expected == actual))

def error_of(func):
	try:
		func()
		return 'no error'
	except Exception as error:
		return type(error).__name__

# ---------- CONTROLS ----------
class FakeKeys:   # stands in for pygame's key list: only the keys in the set are pressed
	def __init__(self, pressed):
		self.pressed = pressed
	def __getitem__(self, key):
		return key in self.pressed

check('W counts as Up', True, controls.KeyState(FakeKeys({pygame.K_w}), set())[pygame.K_UP])
check('D counts as Right', True, controls.KeyState(FakeKeys({pygame.K_d}), set())[pygame.K_RIGHT])
check('arrow key still works', True, controls.KeyState(FakeKeys({pygame.K_LEFT}), set())[pygame.K_LEFT])
check('W does not count as Down', False, controls.KeyState(FakeKeys({pygame.K_w}), set())[pygame.K_DOWN])
check('touch button counts as a key', True, controls.KeyState(FakeKeys(set()), {pygame.K_SPACE})[pygame.K_SPACE])
check('menus: S key works as Down', pygame.K_DOWN, controls.menu_key(pygame.K_s))
check('menus: other keys unchanged', pygame.K_RETURN, controls.menu_key(pygame.K_RETURN))

# ---------- BATTLE FREEZES ----------
class FakeSprite(pygame.sprite.Sprite):
	def __init__(self, monster, group):
		super().__init__(group)
		self.monster = monster
		self.state = 'idle'
		self.highlight = False
	def set_highlight(self, value):
		self.highlight = value

def make_battle():
	battle = Battle.__new__(Battle)
	battle.player_sprites, battle.opponent_sprites = pygame.sprite.Group(), pygame.sprite.Group()
	battle.current_monster, battle.selection_mode = None, None
	battle.selected_attack, battle.selected_orb = None, None
	battle.stuck_time = 0
	battle.timers = {'opponent delay': type('T', (), {'active': False, 'activate': lambda self: setattr(self, 'active', True), 'deactivate': lambda self: setattr(self, 'active', False)})()}
	return battle

battle = make_battle()
fainted = FakeSprite(Monster('Sparchu', 5), battle.player_sprites)
fainted.monster.health, fainted.monster.initiative = 0, 100
battle.check_active()
check('fainted monster does not get a turn (used to freeze)', None, battle.current_monster)

battle = make_battle()
player = FakeSprite(Monster('Sparchu', 5), battle.player_sprites)
opponent = FakeSprite(Monster('Larvea', 3), battle.opponent_sprites)
player.monster.initiative = opponent.monster.initiative = 100
battle.check_active()
check('two turns at once: only one monster gets the turn', (player, 'general', 100), (battle.current_monster, battle.selection_mode, opponent.monster.initiative))

battle = make_battle()
waiting = FakeSprite(Monster('Sparchu', 5), battle.player_sprites)
gone = FakeSprite(Monster('Larvea', 3), battle.opponent_sprites)
battle.current_monster = gone
gone.kill()
waiting.monster.paused = True
battle.opponent_attack()
check('opponent that left before attacking: the other monsters carry on', False, waiting.monster.paused)

battle = make_battle()
a = FakeSprite(Monster('Sparchu', 5), battle.player_sprites)
b = FakeSprite(Monster('Larvea', 3), battle.opponent_sprites)
a.monster.paused = b.monster.paused = True
for frame in range(3):
	battle.check_stuck(1)
check('everyone paused with nobody\'s turn: resumed after 2 seconds', (False, False), (a.monster.paused, b.monster.paused))

ended = []
battle = make_battle()
battle.monster_data = {'player': {0: Monster('Sparchu', 5)}, 'opponent': {}}
battle.end_battle = lambda character, lost = False: ended.append((character, lost))
battle.run_away()
check('running away ends a wild battle without losing', ([(None, False)], True), (ended, battle.battle_over))

# ---------- SHINY ----------
shiny = Monster('Finsta', 6)
shiny.shiny = True
check('shiny is saved and loaded', True, deserialise_monster(serialise_monster(shiny)).shiny)
check('old saves are not shiny', False, deserialise_monster({'name': 'Finsta', 'level': 6, 'xp': 0, 'health': 10, 'energy': 10}).shiny)
check('only a real True makes a monster shiny', False, deserialise_monster({'name': 'Finsta', 'level': 6, 'xp': 0, 'health': 10, 'energy': 10, 'shiny': 'yes'}).shiny)

# ---------- MONSTER INDEX AND QUESTS ----------
game = Game.__new__(Game)
game.toasts, game.coins, game.inventory = [], 0, {}
game.player_monsters = {0: Monster('Sparchu', 5)}
for data in TRAINER_DATA.values():
	data['defeated'] = False
game.reset_progress()
game.record_seen({0: Monster('Larvea', 3), 1: Monster('Jacana', 4)})
check('monsters in a battle are added to "seen"', {'Larvea', 'Jacana'}, game.seen)
game.caught.update({'Sparchu', 'Larvea'})
check('quest progress: species caught', 2, game.quest_progress('catch_5'))
game.counters['catches'] = 1
check('claim a quest that is not finished', ('This quest is not complete yet', set()), (game.claim_quest('catch_5'), game.claimed))
game.claim_quest('first_catch')
check('claim a finished quest gives its reward', (3, {'first_catch'}), (game.inventory.get('capture_orb'), game.claimed))
message = game.claim_quest('first_catch')
check('a quest cannot be claimed twice', ('You already claimed this reward', 3), (message, game.inventory.get('capture_orb')))
game.toasts.clear()
game.caught.update({'Plumette', 'Finsta', 'Atrox'})
game.check_quests()
check('completing a quest shows one message', 1, len(game.toasts))
game.check_quests()
check('the message is not repeated', 1, len(game.toasts))
check('the index has every species', len(MONSTER_DATA), QUEST_DATA['complete_dex']['target'])
check('progress saves and loads', game.progress_data(), (game.reset_progress(game.progress_data()), game.progress_data())[1])
check('saved progress with an unknown monster is rejected', 'ValueError', error_of(lambda: game.check_progress({'caught': ['Pikachu']})))
check('saved progress with a negative counter is rejected', 'ValueError', error_of(lambda: game.check_progress({'counters': {'evolved': -1}})))

# ---------- print results ----------
for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
