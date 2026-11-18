# test_final_polish.py
# Automated tests for Iteration 18: starting from any folder, no healing moves, grass and water
# attacks, the sand zone, stat colours, the Illuminator, free first nickname, quest reminders,
# volume settings, battle music, the ending, autosave, touch controls hiding, items in battle and
# the "super effective" messages.
# Run with:  python test_final_polish.py   (no window is opened)

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'   # run pygame without opening a window
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import tempfile
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from settings import asset, BASE_DIR, GYM_LEADERS, RENAME_MONSTER_COST, FPS
from game_data import ATTACK_DATA, MONSTER_DATA, WILD_ENCOUNTERS, SHOP_PRICES, SPECIAL_ITEMS, QUEST_DATA, TRAINER_DATA
from support import stat_color
from monster import Monster
from main import Game
from battle import Battle
from preferences import Preferences
from save_system import write_protected
import controls

results = []   # list of (test name, expected, actual, passed)

# Records one test result. Parameters: name, expected value, actual value
def check(name, expected, actual):
	results.append((name, expected, actual, expected == actual))

class FakeSound:   # stands in for a pygame Sound so no audio device is needed
	def __init__(self):
		self.plays = 0
	def play(self, loops = 0, fade_ms = 0):
		self.plays += 1
	def fadeout(self, ms):
		pass
	def stop(self):
		pass
	def set_volume(self, volume):
		self.volume = volume

# ---------- STARTING FROM ANY FOLDER (fix #1) ----------
check('asset() builds paths from the game folder, not the current folder', os.path.join(BASE_DIR, 'graphics', 'fonts'), asset('graphics', 'fonts'))
old_folder = os.getcwd()
os.chdir(tempfile.gettempdir())
check('the font is still found after changing to another folder', True, os.path.exists(asset('graphics', 'fonts', 'PixeloidSans.ttf')))
os.chdir(old_folder)

# ---------- ATTACKS ----------
# Iteration 32: healing and boosting moves came back, but only these ones
check('only heal and boost moves target your own side (Iterations 32-33)', set(), {name for name, data in ATTACK_DATA.items() if data['target'] != 'opponent' and data.get('kind') not in ('heal', 'status')})
used = {attack for data in MONSTER_DATA.values() for attack in data['abilities'].values()}
check('every move a monster can learn exists', set(), used - set(ATTACK_DATA))
check('vine whip is a plant attack', 'plant', ATTACK_DATA['vine whip']['element'])
plant_monsters = [name for name, data in MONSTER_DATA.items() if data['stats']['element'] == 'plant']
check('every plant monster learns a plant attack', [], [name for name in plant_monsters if not any(ATTACK_DATA[a]['element'] == 'plant' for a in MONSTER_DATA[name]['abilities'].values())])
water_monsters = [name for name, data in MONSTER_DATA.items() if data['stats']['element'] == 'water']
check('every water monster learns a water attack', [], [name for name in water_monsters if not any(ATTACK_DATA[a]['element'] == 'water' for a in MONSTER_DATA[name]['abilities'].values())])

# ---------- SAND ZONE (fix #4) ----------
check('sand patches are levels 7-11 (not 12-18 next to the beach)', (7, 11), WILD_ENCOUNTERS['sand']['levels'])

# ---------- STAT COLOURS ----------
low, mid, high = stat_color(0.1), stat_color(0.5), stat_color(1.0)
check('low stat is red (more red than green)', True, low[0] > low[1])
check('middle stat is yellow (red and green both high)', True, mid[0] > 150 and mid[1] > 150)
check('high stat is green (more green than red)', True, high[1] > high[0])
check('stat_color clamps values outside 0-1', (stat_color(0), stat_color(1)), (stat_color(-5), stat_color(9)))

# ---------- GAME HELPERS ----------
game = Game.__new__(Game)
game.toasts, game.coins = [], 0
game.reset_progress()
game.audio = {name: FakeSound() for name in ('catch', 'overworld', 'battle_wild', 'battle_trainer', 'gym', 'boss', 'coin')}
game.inventory = {}

# Illuminator
check('the Illuminator is the most expensive item', 'illuminator', max(SHOP_PRICES, key = SHOP_PRICES.get))
check('the Illuminator is a special item', True, 'illuminator' in SPECIAL_ITEMS)
monster = Monster('Sparchu', 5)
monster.shiny = False
game.use_item('illuminator', monster)
check('Illuminator with none in the bag does nothing', False, monster.shiny)
game.inventory['illuminator'] = 1
game.use_item('illuminator', monster)
check('Illuminator makes the monster shiny and is used up', (True, 0), (monster.shiny, game.inventory['illuminator']))
game.inventory['illuminator'] = 1
game.use_item('illuminator', monster)
check('Illuminator on a shiny monster is not wasted', 1, game.inventory['illuminator'])

# nicknames
fresh = Monster('Finsta', 4)
game.coins = 0
check('first nickname is free, even later on', (None, 'Fin'), (game.rename_monster(fresh, 'Fin'), fresh.display_name))
check('renaming again costs coins', 'not_enough_coins', game.rename_monster(fresh, 'Splash'))
game.coins = RENAME_MONSTER_COST
check('renaming again works with enough coins', (None, 0), (game.rename_monster(fresh, 'Splash'), game.coins))

# quest reminder
game.player_monsters = {0: Monster('Sparchu', 5)}
game.claimed = set()
claimable = game.claimable_quests()
check('claimable quests are complete and not yet claimed', True, all(game.quest_progress(q) >= QUEST_DATA[q]['target'] for q in claimable))
if claimable:
	game.claimed.add(claimable[0])
	check('a claimed quest is no longer claimable', False, claimable[0] in game.claimable_quests())

# battle music
for character_id, expected in (('px', 'boss'), ('wx', 'boss'), ('p1', 'gym'), ('f2', 'gym'), ('o1', 'battle_trainer'), (None, 'battle_wild')):
	game.start_battle_music(character_id)
	check(f'music for {character_id}', expected, game.battle_music)

# ending: only after all three gym leaders, and only once
class FakeUI:
	def __init__(self):
		self.screens = []
	def push(self, screen):
		self.screens.append(screen)
class FakePlayer:
	def block(self):
		pass
import main as main_module
main_module.EndingScreen = lambda ui: 'ending'   # the real screen needs the images
game.ui, game.player = FakeUI(), FakePlayer()
game.playing, game.active_slot = False, None
saved_states = {leader: TRAINER_DATA[leader]['defeated'] for leader in GYM_LEADERS}
for leader in GYM_LEADERS:
	TRAINER_DATA[leader]['defeated'] = False
TRAINER_DATA['px']['defeated'] = TRAINER_DATA['fx']['defeated'] = True
game.check_ending()
check('no ending with two gym leaders beaten', [], game.ui.screens)
TRAINER_DATA['wx']['defeated'] = True
game.check_ending()
check('ending starts once all three are beaten', ['ending'], game.ui.screens)
game.check_ending()
check('the ending only plays once', ['ending'], game.ui.screens)
for leader, state in saved_states.items():
	TRAINER_DATA[leader]['defeated'] = state

# autosave
saves = []
game.save_game = lambda slot: saves.append(slot) or True
game.autosave()
check('no autosave on the title screen', [], saves)
game.playing, game.active_slot = True, 2
game.autosave()
check('autosave writes to the slot being played', [2], saves)
check('autosave shows the "Saved" sign', True, game.saved_flash > 0)

# ---------- PREFERENCES ----------
folder = tempfile.TemporaryDirectory()
write_protected(os.path.join(folder.name, 'preferences.json'), {'brightness': 110, 'sound': False, 'music': True, 'intro': 'nonsense'})
preferences = Preferences(folder.name)
check('old "sound off" becomes sound volume 0', 0, preferences['sound_volume'])
check('old "music on" keeps the default music volume', 70, preferences['music_volume'])
check('an unknown intro setting goes back to "full"', 'full', preferences['intro'])
preferences.change_volume('music_volume', 1)
preferences.change_volume('music_volume', 1)
preferences.change_volume('music_volume', 1)
preferences.change_volume('music_volume', 1)
check('volume never goes above 100', 100, preferences['music_volume'])
sound, music = FakeSound(), FakeSound()
preferences.set('muted', True)
preferences.apply_audio({'menu_move': sound, 'overworld': music})
check('mute silences everything', (0, 0), (sound.volume, music.volume))
preferences.set('muted', False)
preferences.apply_audio({'menu_move': sound, 'overworld': music})
check('volumes are used when not muted', (0, 1.0), (sound.volume, music.volume))
preferences.cycle_intro(1)
check('intro setting cycles full -> short', 'short', preferences['intro'])
folder.cleanup()

# ---------- TOUCH CONTROLS ----------
touch = controls.TouchControls({'bold': pygame.font.Font(None, 20), 'small': pygame.font.Font(None, 14), 'regular': pygame.font.Font(None, 18)})
touch.handle([pygame.event.Event(pygame.FINGERDOWN, x = 0.9, y = 0.1, finger_id = 1, dx = 0, dy = 0, touch_id = 0, pressure = 1)])
check('touching the screen shows the buttons', True, touch.enabled)
touch.handle([pygame.event.Event(pygame.KEYDOWN, key = pygame.K_SPACE, unicode = ' ', mod = 0, scancode = 0, touch = True)])
check('a key posted by the touch buttons does not hide them', True, touch.enabled)
touch.handle([pygame.event.Event(pygame.KEYDOWN, key = pygame.K_SPACE, unicode = ' ', mod = 0, scancode = 0)])
check('pressing a real key hides the buttons again', False, touch.enabled)
check('hidden buttons do not block clicks', False, touch.covers((110, 600)))

# ---------- ITEMS IN BATTLE ----------
battle = Battle.__new__(Battle)
battle.inventory = {'potion': 1, 'power_band': 1}
check('only usable items are listed in battle (not held items)', True, 'power_band' not in battle.owned_items() and 'potion' in battle.owned_items())
messages = []
battle.show_message = messages.append
battle.sounds = {}
battle.update_all_monsters = lambda state: None
hurt = Monster('Sparchu', 5)
hurt.health = 1
battle.use_item = lambda name, monster: game.use_item(name, monster)
game.inventory = battle.inventory
class Holder:   # a monster sprite only needs .monster here
	def __init__(self, monster):
		self.monster = monster
battle.selected_item, battle.selection_mode, battle.current_monster = 'potion', 'target', 'someone'
battle.give_item(Holder(hurt))
check('a potion heals in battle and uses the turn', (True, 0, None), (hurt.health > 1, battle.inventory['potion'], battle.current_monster))
full = Monster('Sparchu', 5)
battle.inventory['potion'] = 1
battle.selected_item, battle.current_monster = 'potion', 'someone'
battle.give_item(Holder(full))
check('a potion on a full-health monster is not used up and keeps the turn', (1, 'general'), (battle.inventory['potion'], battle.selection_mode))

# ---------- SUPER EFFECTIVE MESSAGES ----------
battle = Battle.__new__(Battle)
battle.battle_sprites = pygame.sprite.Group()
battle.monster_frames = {'attacks': {data['animation']: [pygame.Surface((4, 4))] for data in ATTACK_DATA.values()}}
battle.sounds = {data['animation']: FakeSound() for data in ATTACK_DATA.values()}
battle.sounds['super_hit'] = FakeSound()
battle.fonts = {'bold': pygame.font.Font(None, 20)}
battle.timers = {}
messages = []
battle.show_message = messages.append
battle.check_death = lambda: None
battle.update_all_monsters = lambda state: None
battle.shake_time = 0
target = pygame.sprite.Sprite(pygame.sprite.Group())
target.rect = pygame.FRect(0, 0, 10, 10)
target.monster = Monster('Plumette', 5)        # plant
attacker = Holder(Monster('Sparchu', 5))       # fire
battle.apply_attack(target, 'burn', 10, attacker = attacker)
check('fire on plant says "super effective"', True, any('super' in m.lower() or 'effective' in m.lower() for m in messages))
check('a super effective hit shakes the screen', True, battle.shake_time > 0)
check('a damage number floats up from the target', 1, len([s for s in battle.battle_sprites if type(s).__name__ == 'DamageNumberSprite']))

# ---------- MISC ----------
check('the frame rate is capped', 60, FPS)

# ---------- print results ----------
for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
