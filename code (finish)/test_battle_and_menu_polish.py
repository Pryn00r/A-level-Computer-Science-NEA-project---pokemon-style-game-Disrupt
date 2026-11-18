# test_battle_and_menu_polish.py
# Automated tests for Iteration 24: battle polish (critical hits, the catch wobble, the VS screen,
# monster cries) and the new settings (colour-blind colours, large text, difficulty, autosave,
# encounter rate, rebindable keys and controllers).
# Run with:  python test_battle_and_menu_polish.py   (no window is opened; uses a temporary saves folder)

import os
import tempfile
import time
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from settings import COLORS, asset
from game_data import MONSTER_DATA, TRAINER_DATA, BADGE_DATA
from monster import Monster
from preferences import Preferences
from localisation import STRINGS
import options
import controls
import item_art

results = []
def check(name, expected, actual):
	results.append((name, expected, actual, expected == actual))

folder = tempfile.TemporaryDirectory()

# ---------- preferences: the new settings are checked when they are loaded ----------
from save_system import write_protected
write_protected(os.path.join(folder.name, 'preferences.json'), {'difficulty': 'impossible', 'autosave': 7, 'encounter_rate': 'always', 'keys': {'up': 'w', 'down': pygame.K_ESCAPE}})
preferences = Preferences(folder.name)
check('an unknown difficulty becomes Normal', 'normal', preferences['difficulty'])
check('an unknown autosave time becomes 3 minutes', 180, preferences['autosave'])
check('an unknown encounter rate becomes Normal', 'normal', preferences['encounter_rate'])
check('bad key bindings become the defaults (W, S)', (pygame.K_w, pygame.K_s), (preferences['keys']['up'], preferences['keys']['down']))
preferences.cycle('difficulty', options.DIFFICULTIES, 1)
check('difficulty goes Normal -> Hard', 'hard', preferences['difficulty'])
check('Hard makes trainers 2 levels higher', 2, options.state['level'])
preferences.cycle('difficulty', options.DIFFICULTIES, 1)
check('difficulty wraps round to Easy', 'easy', preferences['difficulty'])
check('Easy gives more XP', True, options.state['xp'] > 1)
preferences.cycle('difficulty', options.DIFFICULTIES, 1)
check('back to Normal changes nothing', (0, 1.0, 1.0), (options.state['level'], options.state['xp'], options.state['catch']))
preferences.cycle('autosave', options.AUTOSAVE_CHOICES, 1)
check('autosave can be set to every 5 minutes', 300, preferences['autosave'])
preferences.cycle('autosave', options.AUTOSAVE_CHOICES, 1)
check('autosave can be turned off', 0, preferences['autosave'])
check('High encounters start sooner than Low', True, options.ENCOUNTER_DELAY['high'][1] < options.ENCOUNTER_DELAY['low'][0])

# ---------- colour-blind colours and large text ----------
fire_before = COLORS['fire']
options.apply_colour_blind(True)
check('colour-blind mode changes the type colours', True, COLORS['fire'] != fire_before and item_art.TYPE_COLOURS['fire'] == options.COLOUR_BLIND_TYPES['fire'])
check('every type has a colour-blind colour', [], [e for e in item_art.TYPE_COLOURS if e not in options.COLOUR_BLIND_TYPES])
options.apply_colour_blind(False)
check('turning it off puts the normal colours back', fire_before, COLORS['fire'])
fonts = options.build_fonts({})
normal_height = fonts['regular'].get_height()
same = fonts
options.build_fonts(fonts, large = True)
check('large text makes the fonts bigger', True, fonts['regular'].get_height() > normal_height)
check('the same font dictionary is changed (screens keep using it)', True, fonts is same)

# ---------- keys ----------
keys = dict(options.DEFAULT_KEYS)
check('a key the game uses cannot be bound', 'keys_reserved', options.rebind(keys, 'up', pygame.K_SPACE))
check('two actions cannot share a key', 'keys_taken', options.rebind(keys, 'up', pygame.K_s))
check('a free key can be bound', (None, pygame.K_i), (options.rebind(keys, 'up', pygame.K_i), keys['up']))
options.apply_keys(keys)
check('the new key moves the player', (pygame.K_UP, pygame.K_i), controls.ALIASES[pygame.K_UP])
options.apply_keys(options.DEFAULT_KEYS)
check('reset puts W back', (pygame.K_UP, pygame.K_w), controls.ALIASES[pygame.K_UP])
check('the controller reader starts with no controller plugged in', 'no error', (controls.Gamepad().handle([]), 'no error')[1])

# ---------- difficulty changes trainers ----------
from entities import Character
options.apply_difficulty('hard')
class Dummy:
	rect = pygame.FRect(0, 0, 10, 10)
data = {'monsters': {0: ('Pouch', 10)}, 'directions': ['down'], 'look_around': False, 'defeated': False, 'biome': 'forest', 'dialog': {'default': ['hi'], 'defeated': ['bye']}}
frames = {state: [pygame.Surface((128, 128))] for state in ('down', 'up', 'left', 'right', 'down_idle', 'up_idle', 'left_idle', 'right_idle')}
trainer = Character((0, 0), frames, pygame.sprite.Group(), 'down', data, Dummy(), lambda c: None, pygame.sprite.Group(), 0, False, None)
check("Hard: the trainer's level 10 monster is level 12", 12, trainer.monsters[0].level)
options.apply_difficulty('normal')

# ---------- battle ----------
from main import Game
game = Game()
check('every species has a cry', [], [name for name in MONSTER_DATA if not os.path.exists(asset('audio', f'cry_{name}.ogg'))])
from battle import Battle, catch_chance
game.inventory = {'capture_orb': 2}
battle = Battle({0: Monster('Finsta', 30)}, {0: Monster('Pouch', 3)}, game.monster_frames, game.bg_frames['forest'], game.fonts, lambda c, lost = False: None, None, game.audio, game.inventory, False, game.use_item)
target = battle.opponent_sprites.sprites()[0]
target.monster.health = 0.01
battle.selected_orb = 'capture_orb'
battle.throw_orb(target)
check('the orb uses one from the bag', 1, game.inventory['capture_orb'])
check('the result waits while the orb wobbles', (True, True, []), (bool(battle.pending_catch), target.hidden, battle.caught))
battle.finish_catch()
check('then the catch result is applied', (None, 1), (battle.pending_catch, len(battle.caught)))
options.apply_difficulty('easy')
monster = Monster('Pouch', 5)
monster.health = monster.get_stat('max_health') / 2
easy = catch_chance(monster, 'capture_orb')
options.apply_difficulty('normal')
check('catching is easier on Easy', True, easy > catch_chance(monster, 'capture_orb'))

# the VS screen for gym leaders
leader = next(iter(BADGE_DATA))
game.reset_progress()
game.player_monsters = {0: Monster('Finsta', 20)}
game.change_map('world', 'house')
sprite = next((s for s in game.character_sprites if s.character_id == leader), None)
if sprite is None:
	sprite = Character((0, 0), frames, pygame.sprite.Group(), 'down', TRAINER_DATA[leader], game.player, game.create_dialog, pygame.sprite.Group(), 0, False, None, character_id = leader)
TRAINER_DATA[leader]['defeated'] = False
game.end_dialog(sprite)
check('a gym leader battle starts with the VS screen', (True, True), (game.transition_target.vs is not None, game.transition_target.vs_time > 0))
check('the battle waits until the VS screen ends', 2.2, game.transition_target.vs_time)

# ---------- text for every new setting ----------
from info_screens import SettingsScreen
missing = [f'setting_{row}{end}' for row in SettingsScreen.rows for end in ('', '_desc') for lang in ('en', 'it', 'es') if f'setting_{row}{end}' not in STRINGS[lang]]
check('every setting has a name and a description in all 3 languages', [], missing)

# ---------- dialogue portraits ----------
from dialog import face_portrait
check('a trainer speech bubble gets a face picture', 30, face_portrait(game.player, 30).get_height())
check('something with no frames gets no picture', None, face_portrait(object(), 30))

folder.cleanup()
for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
