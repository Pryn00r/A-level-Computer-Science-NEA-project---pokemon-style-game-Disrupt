# main.py
# Start of the program. Contains the Game class, which loads every asset, builds the map, runs the
# game loop and connects the overworld, dialogue, battles, menus, saves, evolution and settings together.
# Run this file to play the game.

from settings import *
from game_data import *
import os
from os.path import exists, join
from random import randint, sample, random
from datetime import datetime

from sprites import Sprite, AnimatedSprite, MonsterPatchSprite, BorderSprite, CollidableSprite, TransitionSprite
from entities import Player, Character
from groups import AllSprites
from dialog import DialogTree
from monster_index import MonsterIndex
from battle import Battle
from timery import Timer
from evolution import Evolution
from intro import IntroScreen
from ending import EndingScreen

from support import *
from monster import Monster, MIN_LEVEL, MAX_LEVEL
from menus import ScreenStack, MainMenu, TitleScreen, AccountHub, StarterScreen, draw_key_hints, MapScreen, ShopScreen, NicknameScreen, draw_minimap_markers, item_name, draw_text
from preferences import Preferences
from save_system import ProfileManager, serialise_monster, deserialise_monster
from localisation import t, attack_name
from ui_style import UI, hud_tag, pixel_frame, icon, spinner
from audio_manager import AudioManager
from atmosphere import Atmosphere
import looks
import options
import outdoors
import records
import town
import postgame
import extra_screens
from outdoors import Outdoors
from math import sin, cos, tau
from story_screens import WardrobeScreen, StorageScreen
import battle_rules
import controls

# Iteration 16: returns a shiny copy of an image - the colours are rotated round the colour wheel.
# The image is copied first and kept transparent (rotating a cut-out frame directly lost its transparency).
def shiny_version(surface):
	return pygame.transform.hsl(surface.copy().convert_alpha(), SHINY_HUE, 0, 0).convert_alpha()

class Game:
	# general 
	# Constructor - opens the window, loads preferences and player profiles, creates the starting party,
	# sprite groups and overlays, builds the first map and shows the title screen. Called once at the bottom of this file.
	def __init__(self):
		pygame.init()
		# Iteration 18: SCALED keeps the game at 1280x720 inside but lets the window be resized (and F11
		# switches to fullscreen) - everything is stretched to fit, so nothing needs redrawing differently
		self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
		pygame.key.start_text_input()   # Iteration 15: typed characters arrive as TEXTINPUT events
		pygame.display.set_caption(GAME_TITLE)
		# Iteration 17: the game's own icon in the title bar and taskbar
		icon_path = asset('graphics', 'other', 'icon.png')
		if exists(icon_path):
			pygame.display.set_icon(pygame.image.load(icon_path))
		self.clock = pygame.time.Clock()
		self.encounter_timer = Timer(2000, func = self.monster_encounter)

		# players and saves
		self.preferences = Preferences()
		self.profiles = ProfileManager()
		self.active_profile = None
		self.saves = None
		self.active_slot = None
		self.playing = False
		self.play_time = 0

		# player monsters 
		self.player_monsters = self.create_starting_party(STARTER_MONSTERS[0])
		self.inventory = dict(STARTING_INVENTORY)
		self.coins = STARTING_COINS   # Iteration 14
		self.tutorial_done = False    # Iteration 14 - True once the first battle (the tutorial) is over
		self.reset_progress()         # Iteration 16 - monster index, quests and counters
		self.toasts = []           # short messages shown at the top of the screen, e.g. a badge being earned (Iteration 13)
		self.minimap_cache = {}    # map name -> (scaled picture of the map, scale) for the minimap (Iteration 13)


		# groups 
		self.all_sprites = AllSprites()
		self.collision_sprites = pygame.sprite.Group()
		self.character_sprites = pygame.sprite.Group()
		self.transition_sprites = pygame.sprite.Group()
		self.monster_sprites = pygame.sprite.Group()

		# transition / tint
		self.transition_target = None
		self.tint_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
		self.tint_mode = 'untint'
		self.tint_progress = 0
		self.tint_speed = 600

		self.atmosphere = Atmosphere(self)   # Iteration 20: weather, footprints, zone banners, night light
		self.outdoors = Outdoors(self)       # Iteration 25: day and night, fishing, digging, hidden items
		self.achievement_popups = []         # Iteration 25: [achievement id, seconds left]
		self.import_assets()
		self.change_map('world', 'house')
		self.preferences.apply_audio(self.audio)
		self.music = None          # Iteration 19: name of the music track playing now
		self.music_check = 0       # seconds until the area music is checked again
		self.set_music(MENU_MUSIC)

		# overlays 
		self.dialog_tree = None
		self.monster_index = MonsterIndex(self.player_monsters, self.fonts, self.monster_frames)
		self.index_open = False
		self.battle = None
		self.evolution = None

		# menus
		self.ui = ScreenStack(self)
		self.show_title_screen()
		# Iteration 37: still signed in from last time - straight to that player's menu
		remembered = self.profiles.restore_session()
		if remembered is not None:
			self.select_profile(remembered, remember = False)
			self.ui.push(AccountHub(self.ui))
		# Iteration 17: studio card, logo and fake loading screen first. Iteration 18: can be short or off.
		if self.preferences['intro'] != 'off':
			self.ui.push(IntroScreen(self.ui, short = self.preferences['intro'] == 'short'))
		self.autosave_time = 0       # Iteration 18: seconds since the game last saved itself
		self.saved_flash = 0         # Iteration 18: seconds left showing the 'Saved' icon

	# Returns a new party containing only the starter the player picked (Iteration 13 - before this
	# every game started with the same preset team of strong monsters).
	# Parameters: starter (species, must be in STARTER_MONSTERS), nickname (string or None).
	# Called from __init__ and start_new_game.
	def create_starting_party(self, starter, nickname = None):
		# lookup check: only the three starters can be chosen
		if starter not in STARTER_MONSTERS:
			raise ValueError(f'{starter} is not a starter monster')
		monster = Monster(starter, STARTER_LEVEL)
		monster.set_nickname(nickname or '')
		return {0: monster}

	# Loads every map, image, font and sound once into dictionaries. Called from __init__.
	def import_assets(self):
		self.tmx_maps = tmx_importer('data', 'maps')

		self.overworld_frames = {
			'water': import_folder('graphics', 'tilesets', 'water'),
			'coast': coast_importer(24, 12,'graphics', 'tilesets', 'coast'),
			'characters': all_character_import( 'graphics', 'characters')
		}

		self.monster_frames = {
			'icons': import_folder_dict('graphics', 'icons'),
			'monsters': monster_importer(4,2,'graphics', 'monsters'),
			'ui': import_folder_dict('graphics', 'ui'),
			'attacks': attack_importer('graphics', 'attacks')
		}
		self.monster_frames['outlines'] = outline_creator(self.monster_frames['monsters'], 4)
		# Iteration 17: the run icon is the cross image shrunk to the same size as the other battle icons
		self.monster_frames['ui']['run'] = pygame.transform.smoothscale(self.monster_frames['ui']['cross'], (28, 28))
		# Iteration 19: the items option is a potion bottle drawn in the same style as the other battle
		# icons (tools/make_icons.py), instead of the star, which did not fit in
		self.monster_frames['ui']['bag'] = self.monster_frames['ui']['potion']
		self.monster_frames['ui']['bag_highlight'] = self.monster_frames['ui']['potion_highlight']
		# Iteration 16: shiny versions are the normal images with the colours rotated (made once here)
		self.monster_frames['shiny'] = {name: {state: [shiny_version(frame) for frame in frames] for state, frames in states.items()} for name, states in self.monster_frames['monsters'].items()}
		self.monster_frames['shiny_icons'] = {name: shiny_version(icon) for name, icon in self.monster_frames['icons'].items()}

		# dialog, regular, small, bold and pixel (tiny "computer" text); Iteration 24: bigger with Large text on
		self.fonts = options.build_fonts({}, self.preferences['large_text'])
		self.bg_frames = import_folder_dict('graphics', 'backgrounds')
		self.touch = controls.TouchControls(self.fonts)   # Iteration 16: on-screen buttons for touch screens
		self.gamepad = controls.Gamepad()                 # Iteration 25: game controllers
		self.trainer_locations = self.find_trainers()
		self.start_animation_frames = import_folder('graphics', 'other', 'star animation')
	
		# Iteration 20: sound effects play through the audio manager so they no longer pile up
		self.audio_manager = AudioManager()
		self.audio = self.audio_manager.wrap(audio_importer('audio'))

	# Reads every map once and returns {character_id: (map name, (x, y))} so the map screen knows where
	# every trainer is, even trainers inside a gym the player is not in yet (Iteration 13).
	def find_trainers(self):
		locations = {}
		for map_name, tmx_map in self.tmx_maps.items():
			for obj in tmx_map.get_layer_by_name('Entities'):
				character_id = obj.properties.get('character_id')
				if obj.name == 'Character' and character_id in TRAINER_DATA and character_id != 'Nurse' and not TRAINER_DATA[character_id].get('npc'):
					locations[character_id] = (map_name, (obj.x, obj.y))
		return locations

	# Remembers which map and start point the player is on (needed for saving) and builds that map.
	# Parameters: map_name (key of tmx_maps), player_start_pos (string). Called from __init__, tint_screen and begin_session.
	def change_map(self, map_name, player_start_pos):
		self.current_map = map_name
		self.current_spawn = player_start_pos
		self.setup(self.tmx_maps[map_name], player_start_pos)
		# Iteration 25: bosses in the Glitch Zone, and places for fast travel
		postgame.place_bosses(self)
		if hasattr(self, 'story'):
			town.remember_visit(self, map_name, player_start_pos)
		self.atmosphere.map_loaded(map_name)
		self.all_sprites.ground_hook = self.atmosphere.draw_ground

	# Builds a map from a Tiled file: terrain, water, coast, objects, transitions, collisions, grass, player and characters.
	def setup(self, tmx_map, player_start_pos):
		# clear the map
		for group in (self.all_sprites, self.collision_sprites, self.transition_sprites, self.character_sprites):
			group.empty()

		# terrain
		for layer in ['Terrain', 'Terrain Top']:
			for x, y, surf in tmx_map.get_layer_by_name(layer).tiles():
				Sprite((x * TILE_SIZE, y * TILE_SIZE), surf, self.all_sprites, WORLD_LAYERS['bg'])

		# water 
		self.water_rects = [pygame.FRect(obj.x, obj.y, obj.width, obj.height) for obj in tmx_map.get_layer_by_name('Water')]   # Iteration 25: fishing
		for obj in tmx_map.get_layer_by_name('Water'):
			for x in range(int(obj.x), int(obj.x + obj.width), TILE_SIZE):
				for y in range(int(obj.y), int(obj.y + obj.height), TILE_SIZE):
					AnimatedSprite((x,y), self.overworld_frames['water'], self.all_sprites, WORLD_LAYERS['water'])

		# coast
		for obj in tmx_map.get_layer_by_name('Coast'):
			terrain = obj.properties['terrain']
			side = obj.properties['side']
			AnimatedSprite((obj.x, obj.y), self.overworld_frames['coast'][terrain][side], self.all_sprites, WORLD_LAYERS['bg'])
		
		# objects 
		for obj in tmx_map.get_layer_by_name('Objects'):
			if obj.name == 'top':
				Sprite((obj.x, obj.y), obj.image, self.all_sprites, WORLD_LAYERS['top'])
			else:
				CollidableSprite((obj.x, obj.y), obj.image, (self.all_sprites, self.collision_sprites))

		# transition objects
		for obj in tmx_map.get_layer_by_name('Transition'):
			TransitionSprite((obj.x, obj.y), (obj.width, obj.height), (obj.properties['target'], obj.properties['pos']), self.transition_sprites)

		# collision objects 
		for obj in tmx_map.get_layer_by_name('Collisions'):
			BorderSprite((obj.x, obj.y), pygame.Surface((obj.width, obj.height)), self.collision_sprites)

		# grass patches 
		for obj in tmx_map.get_layer_by_name('Monsters'):
			MonsterPatchSprite((obj.x, obj.y), obj.image, (self.all_sprites, self.monster_sprites), obj.properties['biome'], obj.properties['monsters'], obj.properties['level'])

		# entities 
		# Iteration 19: the player is made first. Before, characters listed in the map before the player's
		# start point were given the player from the PREVIOUS map, so they "watched" someone who was not
		# there and never noticed or walked up to the real player (e.g. after leaving the hospital).
		for obj in tmx_map.get_layer_by_name('Entities'):
			if obj.name == 'Player' and obj.properties['pos'] == player_start_pos:
				self.player = Player(
					pos = (obj.x, obj.y), 
					frames = looks.frames_for(self, getattr(self, 'look', None)),   # Iteration 22: the chosen look
					groups = self.all_sprites,
					facing_direction = obj.properties['direction'], 
					collision_sprites = self.collision_sprites)
		for obj in tmx_map.get_layer_by_name('Entities'):
			if obj.name == 'Player':
				continue
			else:
				Character(
					character_id = obj.properties['character_id'],
					pos = (obj.x, obj.y), 
					frames = looks.frames_for(self, NPC_LOOKS[obj.properties['character_id']]) if obj.properties['character_id'] in NPC_LOOKS else self.overworld_frames['characters'][obj.properties['graphic']], 
					groups = (self.all_sprites, self.collision_sprites, self.character_sprites),
					# Iteration 14: .get gives a default because the nurse in hospital2 had no direction or
					# radius in the Tiled map, which crashed the game when entering that hospital
					facing_direction = obj.properties.get('direction', 'down'),
					character_data = TRAINER_DATA[obj.properties['character_id']],
					player = self.player,
					create_dialog = self.create_dialog,
					collision_sprites = self.collision_sprites,
					radius = obj.properties.get('radius', 0),
					nurse = obj.properties['character_id'] == 'Nurse',
					notice_sound = self.audio['notice'])

	# accounts and save slots
	# Shows the title screen (Sign In / Create Account / Forgot Password ...). Iteration 14.
	def show_title_screen(self):
		self.playing = False
		if hasattr(self, 'atmosphere'):
			self.atmosphere.stop_sounds()
		self.set_music(MENU_MUSIC)
		self.ui.clear()
		self.ui.push(TitleScreen(self.ui))

	# ---------- Iteration 22: looks, storage and furniture (the professor was removed in Iteration 27) ----------
	# Changes how the player looks (from the mirror) straight away.
	def change_look(self, look):
		self.look = looks.validate(look)
		self.player.frames = looks.frames_for(self, self.look)

	# Moves a monster between the party (column 0) and the storage box (column 1). Returns a message.
	def move_storage(self, column, index):
		party = [self.player_monsters[i] for i in sorted(self.player_monsters)]
		if column == 0:
			if len(party) <= 1:
				return t('storage_keep_one')
			if len(self.storage) >= STORAGE_SIZE:
				return t('storage_box_full')
			monster = party.pop(index)
			self.storage.append(monster)
		else:
			if len(party) >= MAX_PARTY_SIZE:
				return t('storage_party_full', amount = MAX_PARTY_SIZE)
			monster = self.storage.pop(index)
			party.append(monster)
		self.player_monsters.clear()
		self.player_monsters.update(dict(enumerate(party)))
		return t('storage_moved', monster = monster.display_name)

	# Iteration 19: "Continue playing" after the ending - back in the world, on the grass between the
	# two houses where the game started (not inside the gym).
	def continue_after_ending(self):
		self.change_map('world', 'house')
		self.player.unblock()
		self.autosave()

	# Iteration 19: "Back to Main Menu" in the in-game menu. Saves, stops playing and shows the menu
	# you get after signing in (load, new game, settings, account...), still signed in.
	def back_to_hub(self):
		self.autosave()
		self.playing = False
		self.battle = None
		self.atmosphere.stop_sounds()
		self.set_music(MENU_MUSIC)
		self.ui.clear()
		self.ui.push(AccountHub(self.ui))

	# Logs out: clears the current player and slot and goes back to the title screen.
	def return_to_title(self):
		self.profiles.forget(self.active_profile)   # Iteration 37: logging out ends the saved session
		self.active_profile, self.saves, self.active_slot = None, None, None
		self.show_title_screen()

	# Sets the active player and gets their SaveManager. Parameter: profile (dict from profiles.json).
	# Iteration 37: remember = True saves the session so the player stays signed in after closing the game.
	def select_profile(self, profile, remember = True):
		self.active_profile = profile
		self.saves = self.profiles.get_saves(profile)
		if remember:
			self.profiles.remember(profile)

	# Returns a list of the ids of every trainer that has been beaten (saved and shown on the menu card).
	def defeated_trainers(self):
		return [name for name, data in TRAINER_DATA.items() if data['defeated'] and not (data.get('npc') or data.get('rival') or data.get('legendary')
		        or data.get('service') or data.get('boss') or data.get('twins'))]   # Iteration 25: town people, bosses and the twins are not counted

	# Starts playing from either a new game or a loaded save. Resets anything left over from a previous
	# session (dialogue, battle, evolution, fade) so data from one slot can never leak into another.
	# Iteration 16: an empty monster index, no quests claimed and all counters at 0.
	def reset_progress(self, progress = None):
		progress = progress or {}
		# Iteration 22: the player's look, looks bought at the mirror, the storage box and story flags
		self.look = looks.validate(progress.get('look', looks.DEFAULT_LOOK))
		self.storage = []
		for data in progress.get('storage', [])[:STORAGE_SIZE]:
			try:
				self.storage.append(deserialise_monster(data))
			except (KeyError, TypeError, ValueError):
				pass
		self.story = dict(progress.get('story', {})) if isinstance(progress.get('story', {}), dict) else {}
		self.seen = set(progress.get('seen', []))           # species met in a battle
		self.caught = set(progress.get('caught', []))       # species the player has owned
		self.claimed = set(progress.get('claimed', []))     # quests whose reward has been taken
		self.counters = {'evolved': 0, 'shiny': 0, 'catches': 0}
		self.counters.update(progress.get('counters', {}))
		self.pending_nicknames = []                         # monsters just caught, waiting to be named
		self.announced = set(self.completed_quests())       # quests already shown as complete

	# Returns the progress dictionary saved in the slot.
	def progress_data(self):
		return {'seen': sorted(self.seen), 'caught': sorted(self.caught), 'claimed': sorted(self.claimed), 'counters': self.counters,
			'look': self.look,
			'storage': [serialise_monster(monster) for monster in self.storage], 'story': self.story}   # Iteration 22

	# Iteration 14: also coins and tutorial_done. Iteration 16: also progress (index, quests).
	def begin_session(self, slot, monsters, inventory, defeated, play_time, map_name, spawn, position = None, facing = None, coins = STARTING_COINS, tutorial_done = False, progress = None):
		self.active_slot = slot
		self.player_monsters = monsters
		self.inventory = inventory
		self.coins = coins
		self.tutorial_done = tutorial_done
		self.play_time = play_time
		for name, data in TRAINER_DATA.items():
			data['defeated'] = name in defeated
		self.reset_progress(progress)
		self.caught.update(monster.name for monster in monsters.values())   # the party always counts as caught
		self.announced = set(self.completed_quests())

		# clear anything that belonged to the previous session
		self.dialog_tree, self.battle, self.evolution, self.transition_target = None, None, None, None
		self.index_open = False
		self.tint_mode, self.tint_progress = 'untint', 255
		self.monster_index = MonsterIndex(self.player_monsters, self.fonts, self.monster_frames)

		self.change_map(map_name, spawn)
		if position:
			self.player.rect.center = position
			self.player.hitbox.center = position
			self.player.y_sort = self.player.rect.centery
			self.player.facing_direction = facing

		self.ui.clear()
		self.playing = True

	# Starts a fresh playthrough in an empty slot and saves it straight away. Returns True if it saved.
	# Parameters: slot (1-3), starter (species chosen on the starter screen), nickname (string or None).
	# Iteration 27: back to how it was before Iteration 22 - the starter is chosen first and the game
	# starts outside the house (the professor's lab was removed).
	def start_new_game(self, slot, starter, nickname = None):
		party = self.create_starting_party(starter, nickname)
		self.begin_session(slot, party, dict(STARTING_INVENTORY), [], 0, 'world', 'house', coins = STARTING_COINS, tutorial_done = False, progress = {'look': looks.DEFAULT_LOOK})
		self.toast(t('welcome_1'))
		self.toast(t('welcome_2'))
		return self.save_game(slot)

	# Returns a dictionary of everything needed to restore the game (written to slot_n.json).
	def build_save_data(self):
		return {
			'profile_id': self.active_profile['id'],
			'username': self.active_profile['username'],
			'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
			'play_time': self.play_time,
			'map': self.current_map,
			'spawn': self.current_spawn,
			'position': list(self.player.rect.center),
			'facing': self.player.facing_direction,
			'party': [serialise_monster(self.player_monsters[index]) for index in sorted(self.player_monsters)],
			'inventory': self.inventory,
			'defeated_trainers': self.defeated_trainers(),
			'coins': self.coins,                   # Iteration 14
			'tutorial_done': self.tutorial_done,   # Iteration 14
			'progress': self.progress_data()}      # Iteration 16

	# Writes the current game to a slot. Returns False instead of crashing if the file cannot be written.
	def save_game(self, slot):
		try:
			self.saves.write_slot(slot, self.build_save_data())
		except OSError:
			return False
		self.active_slot = slot
		return True

	# Loads a slot. Every value is checked BEFORE the current game is changed, so a damaged or edited
	# save is rejected and the player keeps playing their current game. Returns True if it loaded.
	def load_game(self, slot):
		data = self.saves.read_slot(slot)
		try:
			# everything is checked first so that a bad save cannot change the current game
			monsters = {index: deserialise_monster(monster) for index, monster in enumerate(data['party'])}
			if not monsters or len(monsters) > MAX_PARTY_SIZE or data['map'] not in self.tmx_maps:
				return False
			# Iteration 14: saves from before coins existed get the starting coins (type and range check)
			coins = data.get('coins', STARTING_COINS)
			if not isinstance(coins, int) or isinstance(coins, bool) or coins < 0:
				return False
			save_details = ({name: amount for name, amount in dict(data['inventory']).items() if name not in REMOVED_ITEMS},   # Iteration 31: removed items are dropped
				 data['defeated_trainers'], data['play_time'], data['map'], data['spawn'], tuple(data['position']), data['facing'],
				coins, bool(data.get('tutorial_done', True)), self.check_progress(data.get('progress', {})))
		except (KeyError, TypeError, ValueError):
			return False
		self.begin_session(slot, monsters, *save_details)
		return True

	# Iteration 16: validation for the saved progress - only real species and quests are kept, and
	# counters must be whole numbers of 0 or more. Raises ValueError for anything else.
	def check_progress(self, progress):
		if not isinstance(progress, dict):
			raise ValueError('progress must be a dictionary')
		# Iteration 26: monsters renamed since the save was made get their new names
		for key in ('seen', 'caught'):
			if isinstance(progress.get(key), list):
				progress[key] = [current_name(name) if isinstance(name, str) else name for name in progress[key]]
		for key, valid in (('seen', MONSTER_DATA), ('caught', MONSTER_DATA), ('claimed', QUEST_DATA)):
			if not all(name in valid for name in progress.get(key, [])):
				raise ValueError(f'unknown name in {key}')
		for value in progress.get('counters', {}).values():
			if not isinstance(value, int) or isinstance(value, bool) or value < 0:
				raise ValueError('counters must be whole numbers')
		return progress

	# monster index and quests (Iteration 16)
	# Returns how far the player is towards a quest (a number to compare with its target).
	def quest_progress(self, quest_id):
		kind = QUEST_DATA[quest_id]['kind']
		match kind:
			case 'caught': return len(self.caught)
			case 'seen': return len(self.seen | self.caught)   # a caught monster has also been seen
			case 'badges': return len(self.earned_badges())
			case 'level': return self.party_level()
			case 'party': return len(self.player_monsters)
			case 'coins': return self.coins
			case _: return self.counters.get(kind, 0)

	# Iteration 18: quests that are complete but not claimed yet (shown with a ! so they are not missed).
	def claimable_quests(self):
		return [quest for quest in self.completed_quests() if quest not in self.claimed]

	# Returns the ids of quests that are complete (reached their target), claimed or not.
	def completed_quests(self):
		if not hasattr(self, 'player_monsters'):
			return []
		return [quest for quest, data in QUEST_DATA.items() if self.quest_progress(quest) >= data['target']]

	# Shows a message the first time each quest is completed. Called after battles, catches,
	# evolutions and purchases.
	def check_quests(self):
		# Iteration 25: achievements are checked at the same moments as quests
		if hasattr(self, 'story') and hasattr(self, 'inventory') and hasattr(self, 'player_monsters'):
			for name in records.check(self):
				self.achievement_popups.append([name, 4.0])
				self.play('unlock')
		for quest in self.completed_quests():
			if quest not in self.announced and quest not in self.claimed:
				self.announced.add(quest)
				self.toast(t('quest_complete', quest = t(f'quest_{quest}', target = QUEST_DATA[quest]['target'])), 'quest', 'quest')

	# Gives a completed quest's reward. Returns the message to show. Validation: a quest can only be
	# claimed once, and only once it is complete.
	def claim_quest(self, quest_id):
		if quest_id in self.claimed:
			return t('quest_already')
		if self.quest_progress(quest_id) < QUEST_DATA[quest_id]['target']:
			return t('quest_not_done')
		reward = QUEST_DATA[quest_id]['reward']
		self.coins += reward.get('coins', 0)
		for name, amount in reward.get('items', {}).items():
			self.inventory[name] = self.inventory.get(name, 0) + amount
		self.claimed.add(quest_id)
		return t('quest_claimed')

	# Adds every monster in a battle to the 'seen' part of the monster index.
	def record_seen(self, monsters):
		for monster in monsters.values():
			self.seen.add(monster.name)

	# Uses a potion or ether on a monster. Returns the message to show.
	# Validation: an item is not used up if the stat is already at its maximum.
	def use_item(self, name, monster):
		if name in HELD_ITEM_DATA:
			return self.give_held_item(name, monster)
		if name in SPECIAL_ITEMS:
			return self.use_special_item(name, monster)
		item = ITEM_DATA[name]
		item_name = t(f'item_{name}')
		# Iteration 21: cure items remove a status effect
		if 'cures' in item:
			if self.inventory.get(name, 0) <= 0:
				return t('item_none_left')
			if getattr(monster, 'status', None) not in item['cures']:
				return t('item_no_effect', monster = monster.display_name)
			monster.status = None
			self.inventory[name] -= 1
			return t('item_cured', monster = monster.display_name)
		maximum = monster.get_stat(item['max_stat'])
		current = getattr(monster, item['stat'])
		if current >= maximum:
			return t('item_no_effect', monster = monster.display_name)

		setattr(monster, item['stat'], min(maximum, current + maximum * item['ratio']))
		self.inventory[name] -= 1
		return t('item_used', item = item_name, monster = monster.display_name)

	# ---------- Iteration 25: items used from the bag without choosing a monster ----------
	def use_field_item(self, name):
		if self.inventory.get(name, 0) <= 0:
			return t('item_none_left')
		if name in KEY_ITEMS:
			return t(f'key_{name}_hint')
		effect = ITEM_DATA[name]['field']
		if effect == 'party_heal':
			if all(m.health >= m.get_stat('max_health') and m.energy >= m.get_stat('max_energy') and not m.status for m in self.player_monsters.values()):
				return t('item_no_effect_party')
			self.heal_party()
			self.play('heal')
		self.inventory[name] -= 1
		return t(f'field_{effect}')

	# Where the player goes after losing: the last hospital they healed at.
	def respawn_point(self):
		hospital = self.story.get('hospital')
		if isinstance(hospital, list) and len(hospital) == 2 and hospital[0] in self.tmx_maps:
			return tuple(hospital)
		return DEFEAT_RETURN

	# Walking speed multiplier (Iteration 31: the Swift Cap and Snow Boots were removed, so it is always 1).
	def speed_bonus(self):
		return 1.0

	# Iteration 25: the Shiny Charm triples the chance of a shiny monster.
	def shiny_chance(self):
		return SHINY_CHANCE * (3 if self.inventory.get('shiny_charm') else 1)

	# Iteration 25: it is dark when night mode is on or when it is night on the clock (outdoors).
	def is_dark(self):
		return self.preferences['night_mode'] or self.outdoors.dark() > 0.5

	# Iteration 18: the Illuminator makes a monster shiny (it keeps everything else). Used up only if it worked.
	def use_special_item(self, name, monster):
		if self.inventory.get(name, 0) <= 0:
			return t('item_none_left')
		if monster.shiny:
			return t('illuminator_already', monster = monster.display_name)
		monster.shiny = True
		self.inventory[name] -= 1
		self.counters['illuminated'] = self.counters.get('illuminated', 0) + 1   # Iteration 22: unlocks the Glow Jacket
		self.play('catch')
		return t('illuminator_used', monster = monster.display_name)

	# held items (Iteration 13)
	# Gives a held item from the bag to a monster. A monster can only hold one item, so any item it
	# was already holding goes back into the bag. Returns the message to show.
	def give_held_item(self, name, monster):
		# validation: the item must be a held item and the player must own at least one
		if name not in HELD_ITEM_DATA or self.inventory.get(name, 0) <= 0:
			return t('item_none_left')
		if monster.held_item == name:
			return t('held_already', monster = monster.display_name, item = t(f'held_{name}'))
		if monster.held_item:
			self.inventory[monster.held_item] = self.inventory.get(monster.held_item, 0) + 1
		self.inventory[name] -= 1
		monster.held_item = name
		monster.stat_limiter()
		return t('held_given', monster = monster.display_name, item = t(f'held_{name}'))

	# Takes a monster's held item and puts it back in the bag. Returns the message to show.
	def take_held_item(self, monster):
		if not monster.held_item:
			return t('held_nothing', monster = monster.display_name)
		name = monster.held_item
		self.inventory[name] = self.inventory.get(name, 0) + 1
		monster.held_item = None
		monster.stat_limiter()   # health may now be above the lower maximum
		return t('held_taken', monster = monster.display_name, item = t(f'held_{name}'))

	# badges (Iteration 13)
	# Returns the ids of the badge trainers that have been beaten, in BADGE_DATA order.
	def earned_badges(self):
		return [trainer for trainer in BADGE_DATA if TRAINER_DATA[trainer]['defeated']]

	# Returns the first badge trainer (in BADGE_DATA order) that has not been beaten yet, or None.
	# The map uses this to show the player where to go next.
	def next_badge_trainer(self):
		for trainer in BADGE_DATA:
			if not TRAINER_DATA[trainer]['defeated']:
				return trainer
		return None

	# coins, party limit and renaming (Iteration 14)
	# Gives coins for beating a trainer (not wild monsters): more for stronger trainers, plus a bonus for badges.
	def award_coins(self, character_id):
		if character_id not in TRAINER_DATA or 'monsters' not in TRAINER_DATA[character_id]:
			return 0
		amount = COINS_PER_TRAINER_LEVEL * self.trainer_level(character_id)
		if character_id in BADGE_DATA:
			amount += BADGE_BONUS_COINS
		# Iteration 25: a Lucky Coin held by any party monster gives 50% more
		amount = int(amount * max((monster.held_multiplier('coins') for monster in getattr(self, 'player_monsters', {}).values()), default = 1))
		self.coins += amount
		self.toast(t('coins_earned', amount = amount), 'coin')
		self.play('coin')
		return amount

	# Spends coins if the player has enough. Returns True if they were spent (validation: never below 0).
	def spend_coins(self, amount):
		if amount < 0 or self.coins < amount:
			return False
		self.coins -= amount
		self.counters['spent'] = self.counters.get('spent', 0) + amount   # Iteration 25: for the Big Spender achievement
		return True

	# Buys one item from the nurse's shop. Returns the message to show.
	# Iteration 25: the items for sale right now (more with each badge; key items only until you own one).
	def shop_stock(self):
		badges = len(self.earned_badges())
		return [name for name in SHOP_PRICES if SHOP_UNLOCK.get(name, 0) <= badges and not (name in KEY_ITEMS and self.inventory.get(name))]

	# How many more badges until something new is sold (0 if everything is already sold).
	def next_shop_unlock(self):
		badges = len(self.earned_badges())
		later = [needed for needed in SHOP_UNLOCK.values() if needed > badges]
		return min(later) - badges if later else 0

	# One item a day is cheaper: picked from the date, so it is the same all day for everyone.
	def daily_deal(self):
		stock = [name for name in self.shop_stock() if name not in KEY_ITEMS]
		if not stock:
			return None
		return stock[sum(map(ord, outdoors.today())) % len(stock)]

	def shop_price(self, name):
		price = SHOP_PRICES[name]
		return round(price * (1 - DAILY_DISCOUNT)) if name == self.daily_deal() else price

	def buy_item(self, name):
		if name not in SHOP_PRICES or name not in self.shop_stock():
			return t('shop_unknown')
		price = self.shop_price(name)
		if not self.spend_coins(price):
			return t('shop_no_coins', amount = price - self.coins)
		self.inventory[name] = self.inventory.get(name, 0) + 1
		self.check_quests()
		return t('shop_bought', item = item_name(name))

	# Renames a monster for RENAME_MONSTER_COST coins. Returns None or an error key.
	def rename_monster(self, monster, text):
		# Iteration 18: the first nickname is free (e.g. a monster that was not named when caught)
		cost = RENAME_MONSTER_COST if monster.nickname else 0
		if self.coins < cost:
			return 'not_enough_coins'
		old = monster.nickname
		if not monster.set_nickname(text):
			return 'nickname_invalid'
		if monster.nickname == old:
			return 'nickname_same'
		self.spend_coins(cost)
		return None

	# Releases a monster into the wild. The party must keep at least one monster. Any held item goes
	# back to the bag. The party is renumbered 0, 1, 2... so there are no gaps. Returns the message.
	def release_monster(self, index):
		if len(self.player_monsters) <= 1:
			return t('release_last')
		if index not in self.player_monsters:
			return t('release_failed')
		monster = self.player_monsters[index]
		if monster.held_item:
			self.inventory[monster.held_item] = self.inventory.get(monster.held_item, 0) + 1
		remaining = [self.player_monsters[key] for key in sorted(self.player_monsters) if key != index]
		# the same dictionary is changed (not replaced) because the monster index and battles share it
		self.player_monsters.clear()
		self.player_monsters.update(enumerate(remaining))
		return t('released', monster = monster.display_name)

	# Gives the badge and the reward items for beating a main trainer. Called from end_battle.
	def award_badge(self, character_id):
		if character_id not in BADGE_DATA:
			return
		reward = BADGE_DATA[character_id]['reward']
		self.inventory[reward['held']] = self.inventory.get(reward['held'], 0) + 1
		for name, amount in reward['items'].items():
			self.inventory[name] = self.inventory.get(name, 0) + amount
		self.toast(t('badge_earned', badge = BADGE_DATA[character_id]['badge']), 'badge', 'badge')
		self.toast(t('badge_reward', item = t(f"held_{reward['held']}")), 'bag')

	# Highest level in a trainer's team - used to show how strong a trainer is on the map.
	def trainer_level(self, character_id):
		return max(level for _, level in TRAINER_DATA[character_id]['monsters'].values())

	# Highest level in the player's party.
	def party_level(self):
		return max((monster.level for monster in self.player_monsters.values()), default = 0)   # (0 before the starter)

	# Adds a message to the top of the screen for a few seconds.
	# Iteration 20: an optional icon (name from ui_style ICONS) shows on the left, and a sound can play.
	def toast(self, text, icon = None, sound = None):
		self.toasts.append([text, TOAST_TIME, icon])
		if sound:
			self.play(sound)

	# Draws the messages one under another and removes them once their time is up.
	def draw_toasts(self, dt):
		if self.battle:
			return   # kept until the battle is over so they do not cover the battle screen
		for index, toast in enumerate(self.toasts[:3]):
			toast[1] -= dt
			# Iteration 18: messages slide down when they appear and fade out at the end
			age = TOAST_TIME - toast[1]
			slide = min(1, age / 0.25)
			alpha = int(255 * max(0, min(1, toast[1] / 0.4)))
			hud_tag(self.display_surface, toast[0], self.fonts['regular'], toast[2] if len(toast) > 2 else None, color = UI['gold'], alpha = alpha, midtop = (WINDOW_WIDTH / 2, 16 + index * 54 - (1 - slide) * 40))
		self.toasts = [toast for toast in self.toasts if toast[1] > 0]

	# Iteration 14: the coin counter and control hints along the bottom, shown while walking around.
	def draw_hud(self):
		if self.battle or self.evolution or self.index_open:
			return
		# Iteration 18: the number counts up/down to the real amount instead of jumping
		shown = getattr(self, 'shown_coins', self.coins)
		shown += (self.coins - shown) * 0.15
		self.shown_coins = self.coins if abs(self.coins - shown) < 1 else shown
		# Iteration 19: pixel-framed labels that match the menu buttons (were plain yellow boxes)
		coin_rect = hud_tag(self.display_surface, str(round(self.shown_coins)), self.fonts['regular'], 'coin', topleft = (16, 16))
		# Iteration 25: the time of day (a moon at night) and the steps left on a Repel
		clock_rect = hud_tag(self.display_surface, self.outdoors.clock_text(), self.fonts['regular'], 'moon' if self.outdoors.night() else 'sun', topleft = coin_rect.topright + vector(8, 0))
		# Iteration 18: a reminder when a quest reward is waiting to be claimed (its border pulses gold)
		if self.claimable_quests():
			pulse = abs(((pygame.time.get_ticks() / 600) % 2) - 1)
			border = UI['gold'] if pulse > 0.5 else UI['frame_light']
			hud_tag(self.display_surface, t('hud_quest_ready'), self.fonts['small'], 'quest', border = border, topleft = coin_rect.bottomleft + vector(0, 8))
		if self.dialog_tree:
			hint = t('hud_dialog')
		elif self.preferences['control_hints']:
			hint = t('hud_controls')
		else:
			return
		# Iteration 20: key caps instead of plain words, on a dark strip
		strip = pygame.Surface((WINDOW_WIDTH, 40), pygame.SRCALPHA)
		hint_rect = draw_key_hints(strip, self.fonts['small'], hint, COLORS['white'], center = (WINDOW_WIDTH / 2, 20))
		backing = pygame.Surface(hint_rect.inflate(24, 10).size, pygame.SRCALPHA)
		backing.fill((0, 0, 0, 150))
		self.display_surface.blit(backing, hint_rect.inflate(24, 10).move(0, WINDOW_HEIGHT - 52))
		self.display_surface.blit(strip, (0, WINDOW_HEIGHT - 52))

	# Iteration 25: a gold banner slides down from the top when an achievement unlocks.
	def draw_achievements(self, dt):
		if not self.achievement_popups:
			return
		popup = self.achievement_popups[0]
		popup[1] -= dt
		if popup[1] <= 0:
			self.achievement_popups.pop(0)
			return
		slide = min(1, (4.0 - popup[1]) / 0.3, popup[1] / 0.3)
		rect = pygame.FRect(0, 0, 460, 74).move_to(midtop = (WINDOW_WIDTH / 2, -80 + slide * 120))
		pygame.draw.rect(self.display_surface, (20, 18, 24), rect.move(4, 4), 0, 10)
		pygame.draw.rect(self.display_surface, (60, 46, 20), rect, 0, 10)
		pygame.draw.rect(self.display_surface, UI['gold'], rect, 3, 10)
		trophy = icon('trophy', 4, UI['frame_dark'], UI['gold'])
		self.display_surface.blit(trophy, trophy.get_frect(midleft = rect.midleft + vector(14, 0)))
		draw_text(self.display_surface, self.fonts['small'], t('achievement_unlocked'), UI['gold'], topleft = rect.topleft + vector(80, 12))
		draw_text(self.display_surface, self.fonts['bold'], t(f'ach_{popup[0]}'), COLORS['white'], topleft = rect.topleft + vector(80, 36))

	# minimap (Iteration 13)
	# Returns (surface, scale): a small picture of the map built from its tiles, water and objects.
	# It is only built once per map and then kept in minimap_cache because building it is slow.
	def get_minimap(self, map_name):
		if map_name not in self.minimap_cache:
			tmx_map = self.tmx_maps[map_name]
			tile = max(2, MINIMAP_SIZE // max(tmx_map.width, tmx_map.height))   # pixels per tile on the minimap
			scale = tile / TILE_SIZE
			surface = pygame.Surface((tmx_map.width * tile, tmx_map.height * tile))
			surface.fill(COLORS['water'])
			scaled_tiles = {}
			for layer in ['Terrain', 'Terrain Top']:
				for x, y, surf in tmx_map.get_layer_by_name(layer).tiles():
					if id(surf) not in scaled_tiles:
						scaled_tiles[id(surf)] = pygame.transform.smoothscale(surf, (tile, tile))
					surface.blit(scaled_tiles[id(surf)], (x * tile, y * tile))
			for obj in tmx_map.get_layer_by_name('Water'):
				pygame.draw.rect(surface, COLORS['water'], (obj.x * scale, obj.y * scale, obj.width * scale, obj.height * scale))
			for obj in tmx_map.get_layer_by_name('Objects'):
				if obj.image:
					size = (max(1, int(obj.image.get_width() * scale)), max(1, int(obj.image.get_height() * scale)))
					surface.blit(pygame.transform.smoothscale(obj.image, size), (obj.x * scale, obj.y * scale))
			self.minimap_cache[map_name] = (surface, scale)
		return self.minimap_cache[map_name]

	# Draws the small minimap in the top right corner, centred on the player. Only shown while
	# walking around and when the minimap setting is on.
	def draw_minimap(self):
		if not self.preferences['minimap'] or self.battle or self.evolution or self.index_open or self.dialog_tree:
			return
		surface, scale = self.get_minimap(self.current_map)
		size = MINIMAP_HUD_SIZE
		frame = pygame.FRect(WINDOW_WIDTH - size - 16, 16, size, size)
		centre = vector(self.player.rect.center) * scale
		# the part of the map around the player, kept inside the edges of the map
		view = pygame.FRect(0, 0, size, size).move_to(center = centre).clamp(surface.get_frect())
		self.display_surface.blit(surface, frame.topleft, view)
		draw_minimap_markers(self, self.display_surface, scale, frame.topleft - vector(view.topleft), frame, small = True)
		pixel_frame(self.display_surface, frame.inflate(14, 14), 4, fill = (0, 0, 0, 0))   # Iteration 19: same frame as the menus
		key_surf = self.fonts['small'].render(t('minimap_key'), False, COLORS['white'])
		key_rect = key_surf.get_frect(midtop = frame.midbottom + vector(0, 12))
		pygame.draw.rect(self.display_surface, (40, 38, 46), key_rect.inflate(12, 6))
		self.display_surface.blit(key_surf, key_rect)
	# central menu
	# Returns True only when nothing else is happening, so the menu cannot open during a battle,
	# dialogue, evolution, fade or while the monster index is open.
	def can_open_menu(self):
		busy = self.dialog_tree or self.battle or self.evolution or self.transition_target or self.index_open
		return not busy and not self.player.blocked and bool(self.player_monsters)

	# Blocks the player and opens the main menu.
	def open_menu(self):
		self.player.block()
		self.ui.push(MainMenu(self.ui))

	# Called by ScreenStack when the last menu screen closes - gives control back to the player.
	def menu_closed(self):
		self.player.unblock()

	# Closes pygame and the program.
	def quit_game(self):
		pygame.quit()
		exit()

	# dialog system
	# Overworld keys: Esc opens the menu (or closes the index), Space talks to a character the player
	# is facing, Return opens/closes the monster index. Parameter: events (this frame's pygame events).
	def input(self, events):
		escape_pressed = any(event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE for event in events)
		if escape_pressed:
			if self.index_open:
				self.index_open = False
				self.player.unblock()
			elif self.can_open_menu():
				self.open_menu()
				return

		# M opens the full map (Iteration 13). Checked with events, like Esc, so the same key press
		# cannot also close the map in the same frame.
		map_pressed = any(event.type == pygame.KEYDOWN and event.key == pygame.K_m for event in events)
		if map_pressed and self.can_open_menu():
			self.player.block()
			self.ui.push(MapScreen(self.ui))
			return
		# Iteration 25: T = fast travel (Iteration 31: photo mode was removed)
		for key, screen in ((pygame.K_t, extra_screens.TravelScreen),):
			if any(event.type == pygame.KEYDOWN and event.key == key for event in events) and self.can_open_menu():
				self.player.block()
				self.ui.push(screen(self.ui))
				return

		if not self.dialog_tree and not self.battle:
			keys = controls.get_just_pressed()
			if keys[pygame.K_SPACE]:
				for character in self.character_sprites:
					if check_connections(100, self.player, character):
						self.player.block()
						character.change_facing_direction(self.player.rect.center)
						self.create_dialog(character)
						character.can_rotate = False

			if keys[pygame.K_RETURN] and self.player_monsters:
				self.index_open = not self.index_open
				self.player.blocked = not self.player.blocked


	# Opens a dialogue with a character, as long as one is not already open.
	def create_dialog(self, character):
		# Iteration 25: after the ending, beaten badge trainers offer a rematch once a day
		character.rematch = postgame.rematch_ready(self, character)
		if character.rematch:
			character.character_data['dialog']['defeated_saved'] = character.character_data['dialog'].get('defeated_saved', character.character_data['dialog']['defeated'])
			character.character_data['dialog']['defeated'] = [t('rematch_offer'), ('player', t('rematch_accept'))]
		elif 'defeated_saved' in character.character_data['dialog']:
			character.character_data['dialog']['defeated'] = character.character_data['dialog'].pop('defeated_saved')
		if not self.dialog_tree:
			self.dialog_tree = DialogTree(character, self.player, self.all_sprites, self.fonts['dialog'], self.end_dialog)
			# Iteration 16: tell the player how strong they should be before the battle starts
			if character.monsters and not character.character_data['defeated'] and character.character_id in TRAINER_DATA:
				self.toast(t('recommended_level', level = self.trainer_level(character.character_id), yours = self.party_level()))

	# Runs after the last line of dialogue: the nurse heals, an undefeated trainer starts a battle,
	# a defeated trainer lets the player move again.
	def end_dialog(self, character):
		self.dialog_tree = None
		if getattr(character, 'rematch', False):
			character.monsters = postgame.rematch_team(self, character)   # Iteration 25: a rematch at your level
			self.rematch_battle = character.character_id
			character.character_data['defeated'] = False
			character.rematch = False
		if character.character_data.get('boss'):
			postgame.make_boss(character)
		if character.nurse:
			self.story['hospital'] = [self.current_map, self.current_spawn]   # Iteration 25: you come back here after losing
			self.heal_party()
			self.play('heal')
			self.autosave()
			self.ui.push(ShopScreen(self.ui))   # Iteration 14: the nurse also runs the shop
		elif not character.character_data['defeated']:
			self.record_seen(character.monsters)   # Iteration 16: the trainer's monsters go in the index
			self.start_battle_music(character.character_id)
			self.transition_target = Battle(
				player_monsters = self.player_monsters, 
				opponent_monsters = character.monsters, 
				monster_frames = self.monster_frames, 
				bg_surf = self.bg_frames[character.character_data['biome']], 
				fonts = self.fonts, 
				end_battle = self.end_battle,
				character = character, 
				sounds = self.audio,
				inventory = self.inventory,
				tutorial = not self.tutorial_done,
				use_item = self.use_item)
			# Iteration 24: a VS screen before the big battles (the gym leaders)
			cid = character.character_id
			if cid in BADGE_DATA:
				label = t('badge_name', badge = BADGE_DATA[cid]['badge'])
				self.transition_target.vs = (self.player.frames, character.frames, label)
				self.transition_target.vs_time = 2.2
			self.tint_mode = 'tint'
		else:
			self.player.unblock()
			self.check_evolution()
			self.leave_gym()
			self.check_ending()

	# Iteration 19: after a gym leader is beaten (and any evolution has finished), fades out and puts the
	# player outside that gym's door on the world map, so they do not have to walk back out.
	def leave_gym(self):
		if getattr(self, 'leaving_gym', None) and not self.evolution:
			self.player.block()
			self.transition_target = ('world', self.leaving_gym)
			self.tint_mode = 'tint'
			self.leaving_gym = None

	# Iteration 18: after the last of the three gym leaders has been beaten (and their dialogue has
	# finished), the ending plays once. It is remembered in the save so it does not play again.
	def check_ending(self):
		if all(TRAINER_DATA[leader]['defeated'] for leader in GYM_LEADERS) and not self.counters.get('ending'):
			self.counters['ending'] = 1
			self.story.setdefault('finish_time', int(getattr(self, 'play_time', 0)))   # Iteration 25: the speedrun time
			self.player.block()
			# Iteration 19: the ending replaces the walk out of the gym (the player chooses where to go after)
			self.transition_target, self.tint_mode, self.leaving_gym = None, 'untint', None
			self.ui.push(EndingScreen(self.ui))
			self.autosave()

	# Iteration 18: saves to the slot being played, quietly, after battles, healing and changing map,
	# and every AUTOSAVE_SECONDS. A small 'Saved' sign shows in the corner.
	def autosave(self):
		if not getattr(self, 'player_monsters', None):
			return   # Iteration 22: nothing is saved until the professor has given the starter
		if self.playing and self.active_slot and self.save_game(self.active_slot):
			self.autosave_time = 0
			self.saved_flash = 1.5

	# transition system
	# Starts a fade if the player walks into a transition zone.
	def transition_check(self):
		sprites = [sprite for sprite in self.transition_sprites if sprite.rect.colliderect(self.player.hitbox)]
		if sprites and not self.player_monsters:
			# Iteration 22: the professor will not let you leave without a monster
			self.player.rect.y -= 48
			self.player.hitbox.center = self.player.rect.center
			if not self.toasts:
				self.toast(t('prof_wait'), 'person')
			return
		if sprites:
			self.player.block()
			self.transition_target = sprites[0].target
			self.tint_mode = 'tint'

	# Fades the screen to black and back, loading the next map/battle while the screen is black.
	# tint_progress is clamped between 0 and 255 (range check).
	def tint_screen(self, dt):
		if self.tint_mode == 'untint':
			self.tint_progress -= self.tint_speed * dt

		if self.tint_mode == 'tint':
			self.tint_progress += self.tint_speed * dt
			if self.tint_progress >= 255:
				if type(self.transition_target) == Battle:
					self.battle = self.transition_target
					self.battle.storage = self.storage   # Iteration 22: catches go to the PC box when the party is full
				elif self.transition_target == 'level':
					self.battle = None
					# Iteration 32: tell the player about new moves that did not fit in the 4 battle slots
					for monster in self.player_monsters.values():
						for move in monster.__dict__.pop('learned_spare', []):
							self.toast(t('move_learned_spare', monster = monster.display_name, attack = attack_name(move)), 'book')
					self.ask_nicknames()
					self.check_quests()
					self.autosave()
				elif self.transition_target == 'defeat':
					# the player lost: close the battle, heal the party and send the player back to DEFEAT_RETURN
					self.battle = None
					self.heal_party()
					self.change_map(*self.respawn_point())   # Iteration 25: the last hospital you healed at
					self.autosave()
				else:
					self.change_map(self.transition_target[0], self.transition_target[1])
					self.play('door')   # Iteration 20
					self.autosave()
				self.tint_mode = 'untint'
				self.transition_target = None

		self.tint_progress = max(0, min(self.tint_progress, 255))
		# Iteration 24: going into a battle, black wedges spin in from the edges before the fade
		if self.tint_mode == 'tint' and type(self.transition_target) == Battle:
			self.draw_swirl(self.tint_progress / 255)
			self.tint_surf.set_alpha(max(0, self.tint_progress * 2 - 255))
		else:
			self.tint_surf.set_alpha(self.tint_progress)
		self.display_surface.blit(self.tint_surf, (0,0))

	def draw_swirl(self, progress):
		centre = vector(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
		radius = WINDOW_WIDTH
		turn = progress * 3
		for wedge in range(8):
			start = wedge * tau / 8 + turn
			points = [centre]
			for step in range(7):
				angle = start + progress * (tau / 8) * step / 6
				points.append(centre + vector(cos(angle), sin(angle)) * radius)
			pygame.draw.polygon(self.display_surface, COLORS['black'], points)
	
	# Called by Battle when it finishes. Parameters: character (the trainer, or None for a wild battle),
	# lost (True if every player monster fainted). A win fades back to the map and marks a trainer as defeated;
	# a loss fades out and sends the player to DEFEAT_RETURN with a healed party (handled in tint_screen).
	def end_battle(self, character, lost = False):
		self.set_music(None, 400)
		self.cooldown = BATTLE_COOLDOWN   # Iteration 25: a short break before anything else can start a battle
		for monster in self.player_monsters.values():
			battle_rules.end_of_battle(monster)   # Iteration 21: statuses and stat changes only last one battle
		if not lost:
			self.play('victory')   # Iteration 18
		self.tint_mode = 'tint'
		self.tutorial_done = True   # the tutorial only runs in the first battle
		# Iteration 16: monsters caught in this battle go in the index and get offered a free nickname
		battle = getattr(self, 'battle', None)
		if battle:
			# Iteration 25: counters for the stats screen, achievements and daily quests
			self.counters['crits'] = self.counters.get('crits', 0) + getattr(battle, 'crits', 0)
			if not lost:
				self.counters['wins'] = self.counters.get('wins', 0) + 1
			# Iteration 25: happiness for winning together
			if not lost:
				for monster in getattr(self, 'player_monsters', {}).values():
					monster.change_happiness(2)
			for monster in battle.caught:
				if hasattr(self, 'outdoors') and self.outdoors.night():
					self.counters['night_catches'] = self.counters.get('night_catches', 0) + 1
				self.caught.add(monster.name)
				self.counters['catches'] = self.counters.get('catches', 0) + 1
				self.counters['shiny'] += 1 if monster.shiny else 0
				self.pending_nicknames.append(monster)
		if lost:
			self.transition_target = 'defeat'
			return
		# Iteration 24: a short victory summary - XP earned and any level-ups
		if battle and getattr(battle, 'xp_gained', 0):
			levels = ', '.join(f'{name} Lv {level}' for name, level in battle.level_ups[-3:])
			self.toast(t('victory_summary', xp = int(battle.xp_gained)) + (f'  ({levels})' if levels else ''), 'badge')
		self.transition_target = 'level'
		if character:
			first_win = not character.character_data['defeated']
			character.character_data['defeated'] = True
			# Iteration 25: rematches and bosses
			if getattr(self, 'rematch_battle', None) == character.character_id:
				first_win = False
				postgame.rematch_done(self, character.character_id)
				self.award_coins(character.character_id)
				self.rematch_battle = None
			if character.character_data.get('boss'):
				postgame.boss_beaten(self, character.character_id)
			if first_win:
				self.award_coins(character.character_id)
				self.award_badge(character.character_id)
				# Iteration 19: after beating a gym leader the player is taken outside the gym's door
				if character.character_id in GYM_OF_LEADER:
					self.leaving_gym = GYM_OF_LEADER[character.character_id]
			self.create_dialog(character)
		elif not self.evolution:
			self.player.unblock()
			self.check_evolution()

	# Iteration 16: after catching, asks for a nickname for each new monster (free, Enter skips).
	def ask_nicknames(self):
		if not self.pending_nicknames:
			return
		monster = self.pending_nicknames.pop(0)
		self.player.block()
		def name_it(text):
			if not monster.set_nickname(text):
				return 'nickname_invalid'
			self.ui.pop()
			self.ask_nicknames()   # the next monster caught in the same battle, if any
			return None
		self.ui.push(NicknameScreen(self.ui, monster, name_it))

	# Iteration 18: plays a sound effect by name, if it exists (tests run without any sounds loaded).
	def play(self, name):
		audio = getattr(self, 'audio', {})
		if name in audio:
			audio[name].play()

	# Iteration 18: gym trainers get the gym music, the three gym leaders get the boss music and
	# everyone else (and wild monsters) the normal battle music.
	# Iteration 19: other trainers get their own (more tense) track, and wild monsters another.
	def start_battle_music(self, character_id):
		if character_id in GYM_LEADERS:
			self.battle_music = 'boss'
		elif character_id and character_id[0] in 'pfw' and character_id[1:].isdigit():
			self.battle_music = 'gym'
		elif character_id:
			self.battle_music = 'battle_trainer'
		else:
			self.battle_music = 'battle_wild'
		self.set_music(self.battle_music, 300)

	# Iteration 19: changes the music with a short fade, unless that track is already playing.
	# name None just fades the music out. Parameters: name (key of self.audio or None), fade in ms.
	def set_music(self, name, fade = MUSIC_FADE_MS):
		audio = getattr(self, 'audio', {})
		current = getattr(self, 'music', None)
		def is_playing(track):
			sound = audio.get(track)
			if sound is None:
				return False
			if hasattr(sound, 'get_num_channels'):
				return sound.get_num_channels() > 0
			return track == current   # (sounds that cannot tell us, e.g. in the tests)
		playing = is_playing(name)
		if name == current and (playing or name is None):
			return
		# Iteration 28: every other song is faded out, not just the one we think is playing, so two songs
		# can never play on top of each other
		for track in MUSIC_TRACKS:
			if track != name and is_playing(track):
				audio[track].fadeout(fade)
		if name in audio and not playing:
			audio[name].play(-1, fade_ms = fade)
		self.music = name

	# Iteration 19: the music for where the player is. Inside a building it depends on the map; outside
	# it depends on the ground around the player: green grass, yellow sand or white snow/ice (worked out
	# from the average colour of the ground tile, remembered for each tile type).
	def area_music(self):
		if self.current_map in MAP_MUSIC:
			return MAP_MUSIC[self.current_map]
		biome = self.current_biome()
		if not biome:
			return self.music if self.music in BIOME_MUSIC.values() else BIOME_MUSIC['forest']
		return BIOME_MUSIC[biome]

	# Iteration 20 (moved out of area_music): 'forest', 'sand' or 'ice' for where the player stands
	# outdoors, or None. The ground in a 9 x 9 square around the player votes, so walking on a path
	# (which looks like sand) through the grass does not count as the desert. Remembered per tile.
	def current_biome(self):
		tmx_map = self.tmx_maps[self.current_map]
		x, y = int(self.player.rect.centerx // TILE_SIZE), int(self.player.rect.centery // TILE_SIZE)
		key = (self.current_map, x, y)
		if getattr(self, 'biome_key', None) == key:
			return self.biome_here
		layer = tmx_map.get_layer_by_name('Terrain')
		votes = {}
		for row in range(max(0, y - 4), min(len(layer.data), y + 5)):
			for column in range(max(0, x - 4), min(len(layer.data[0]), x + 5)):
				biome = self.ground_biome(tmx_map, layer.data[row][column])
				if biome:
					votes[biome] = votes.get(biome, 0) + 1
		self.biome_key, self.biome_here = key, (max(votes, key = votes.get) if votes else None)
		return self.biome_here

	# Returns 'forest', 'sand', 'ice' or None (not sure, e.g. a cliff) for a ground tile.
	ground_cache = {}
	def ground_biome(self, tmx_map, gid):
		if gid not in self.ground_cache:
			image = tmx_map.get_tile_image_by_gid(gid) if gid else None
			biome = None
			if image:
				red, green, blue = pygame.transform.average_color(image)[:3]
				if blue > 200:
					biome = 'ice'                     # snow and frozen water
				elif red > 230 and blue > 80:
					biome = 'sand'
				elif blue < 80 and green > 150:
					biome = 'forest'                  # the yellow-green grass
			self.ground_cache[gid] = biome
		return self.ground_cache[gid]

	# Called every frame while playing: twice a second, switches to the area's music when walking
	# around (not during battles, evolutions or the ending, which have their own music).
	def update_music(self, dt):
		self.music_check -= dt
		if self.music_check > 0:
			return
		self.music_check = 0.5
		if not self.battle and not self.evolution and self.transition_target is None and self.music != 'ending':
			self.set_music(self.area_music())

	battle_music = 'battle'

	# Restores every party monster to full health and energy. Used by the nurse and after losing a battle,
	# so the healing rule is only written once.
	def heal_party(self):
		for monster in self.player_monsters.values():
			monster.health = monster.get_stat('max_health')
			monster.energy = monster.get_stat('max_energy')

	# Checks every party monster and starts an evolution if it has reached its evolution level.
	# Uses >= (not ==) so a monster that skips its evolution level still evolves (Iteration 6).
	def check_evolution(self):
		for index, monster in self.player_monsters.items():
			if monster.evolution and not self.evolution:
				# Iteration 25: a monster whose evolution was stopped waits until its next level
				if monster.level >= monster.evolution[1] and monster.level > getattr(monster, 'declined', 0):
					self.set_music(None, 300)
					self.audio['evolution'].play()
					self.player.block()
					self.evolution = Evolution(self.monster_frames['monsters'], monster.name, monster.evolution[0], self.fonts['bold'], self.end_evolution, self.start_animation_frames, monster.display_name, self.cancel_evolution)
					self.evolving = (index, monster, monster.evolution[0] in self.caught)
					evolved = Monster(monster.evolution[0], monster.level)
					# Iteration 13: the nickname, held item and experience carry over to the evolved monster
					evolved.nickname, evolved.held_item, evolved.xp = monster.nickname, monster.held_item, monster.xp
					evolved.shiny = monster.shiny   # Iteration 16: a shiny monster stays shiny
					self.player_monsters[index] = evolved
					self.caught.add(evolved.name)
					self.counters['evolved'] += 1
					self.check_quests()
		# Iteration 28: this used to start the menu song again here, on top of the area music, after every
		# battle - so songs piled up. The area music now comes back by itself (update_music).
		pass

	# Iteration 25: Esc (or B) while the monster is still glowing stops the evolution. It tries again
	# the next time the monster levels up.
	def cancel_evolution(self):
		index, monster, already_caught = self.evolving
		evolved = self.player_monsters[index]
		self.player_monsters[index] = monster
		monster.declined = monster.level
		self.counters['evolved'] = max(0, self.counters['evolved'] - 1)
		if not already_caught:
			self.caught.discard(evolved.name)
		self.toast(t('evolution_stopped', monster = monster.display_name), 'heal')
		self.end_evolution()

	# Called when the evolution animation finishes - gives control back to the player.
	def end_evolution(self):
		self.evolution = None
		self.player.unblock()
		self.audio['evolution'].stop()
		self.leave_gym()

	# monster encounters 
	# Starts the encounter timer while the player walks through grass.
	def check_monster(self):
		if [sprite for sprite in self.monster_sprites if sprite.rect.colliderect(self.player.hitbox)] and not self.battle and self.player.direction:
			if not self.encounter_timer.active:
				self.encounter_timer.activate()

	# Starts a wild battle against the patch's monsters at a random level near the patch level.
	def monster_encounter(self):
		if not self.player_monsters:
			return
		sprites = [sprite for sprite in self.monster_sprites if sprite.rect.colliderect(self.player.hitbox)]
		if getattr(self, 'cooldown', 0) > 0:
			return
		if sprites and self.player.direction:
			self.encounter_timer.duration = randint(*options.encounter_delay(self.preferences))   # Iteration 25: encounter rate
			monsters = self.create_wild_monsters(sprites[0])
			self.start_wild_battle(monsters, sprites[0].biome)

	# Starts a battle against wild monsters (from the grass or from fishing). Iteration 25: split out.
	def start_wild_battle(self, monsters, biome):
		self.record_seen(monsters)
		self.player.block()
		self.start_battle_music(None)
		self.transition_target = Battle(
			player_monsters = self.player_monsters, 
			opponent_monsters = monsters, 
			monster_frames = self.monster_frames, 
			bg_surf = self.bg_frames[biome], 
			fonts = self.fonts, 
			end_battle = self.end_battle,
			character = None, 
			sounds = self.audio,
			inventory = self.inventory,
			tutorial = not self.tutorial_done,
			use_item = self.use_item)
		self.tint_mode = 'tint'

	# Returns the wild monsters for a grass patch (Iteration 13). Each zone has its own tier of monsters
	# and levels from WILD_ENCOUNTERS, so the grass zone has first-stage monsters, the sand zone
	# second-stage and the ice zone final-stage. A zone missing from WILD_ENCOUNTERS uses the Tiled values.
	def create_wild_monsters(self, patch):
		encounter = WILD_ENCOUNTERS.get(patch.biome)
		if encounter:
			# Iteration 25: some monsters only come out at night
			night = hasattr(self, 'outdoors') and self.outdoors.night()
			pool = [name for name in encounter['monsters'] if night or name not in NIGHT_ONLY]
			if night:
				pool += [name for name in NIGHT_ENCOUNTERS.get(patch.biome, ()) if name not in pool]
			names = sample(pool, randint(1, encounter['pick']))
			low, high = encounter['levels']
			monsters = {index: Monster(name, randint(low, high)) for index, name in enumerate(names)}
			for monster in monsters.values():
				monster.shiny = random() < (self.shiny_chance() if hasattr(self, 'inventory') else SHINY_CHANCE)   # Iteration 16 (Iteration 25: the Shiny Charm)
			return monsters
		# range check: the random level is kept between MIN_LEVEL and MAX_LEVEL
		return {index: Monster(name, max(MIN_LEVEL, min(MAX_LEVEL, patch.level + randint(-3,3)))) for index, name in enumerate(patch.monsters)}

	# Runs one frame: events, updates (paused while a menu is open), drawing, overlays, fade,
	# night mode, menus and brightness. Parameter: dt (seconds since the last frame).
	def frame(self, dt):
		self.display_surface.fill('black')

		# event loop 
		events = pygame.event.get()
		self.touch.handle(events)
		self.gamepad.handle(events)
		for event in events:
			if event.type == pygame.QUIT:
				self.quit_game()
			# Iteration 18: F11 switches between a window and fullscreen
			if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
				pygame.display.toggle_fullscreen()

		# the game world is paused while a menu is open
		menu_open = self.ui.active

		if self.playing:
			# update 
			self.update_music(dt)
			if not menu_open:
				self.play_time += dt
				self.encounter_timer.update()
				self.input(events)
				self.transition_check()
				self.all_sprites.update(dt)
				self.check_monster()
			self.cooldown = max(0, getattr(self, 'cooldown', 0) - (0 if menu_open else dt))
			# Iteration 22: no battles before the starter; Iteration 25: nor straight after another battle
			self.player.can_be_challenged = bool(self.player_monsters) and self.cooldown <= 0

			# Iteration 25: the clock and the steps walked
			moved = vector(self.player.rect.center).distance_to(getattr(self, 'last_player_pos', self.player.rect.center))
			self.last_player_pos = vector(self.player.rect.center)
			if not menu_open and moved < 200:
				self.outdoors.walked(moved)
			self.outdoors.update(dt, active = not menu_open and not self.battle and not self.evolution and not self.dialog_tree)
			self.player.speed_bonus = self.speed_bonus()

			# drawing
			self.all_sprites.draw(self.player)
			# Iteration 20: weather, footprints and zone banners
			quiet = self.battle or self.evolution or self.index_open
			self.atmosphere.update(dt, active = not menu_open and not quiet and not self.dialog_tree)
			if not quiet:
				self.atmosphere.draw_sky(self.display_surface, self.all_sprites.offset)
				self.outdoors.draw_night(self.display_surface)   # Iteration 25
				postgame.draw_glitch(self, self.display_surface)
			
			# overlays 
			if self.dialog_tree: self.dialog_tree.update()
			if self.index_open:  self.monster_index.update(dt)
			if self.battle:      self.battle.update(dt)
			if self.evolution:   self.evolution.update(dt)
			if not menu_open:    self.draw_minimap()
			if not menu_open:    self.draw_hud()
			if not menu_open and not quiet: self.atmosphere.draw_banner(self.display_surface, self.fonts['bold'])
			# Iteration 18: autosave timer and the 'Saved' sign
			if not menu_open and not self.battle:
				self.autosave_time += dt
				if self.preferences['autosave'] and self.autosave_time >= self.preferences['autosave']:   # Iteration 25: Off/1/3/5 min
					self.autosave()
			if self.saved_flash > 0:
				self.saved_flash -= dt
				tag = hud_tag(self.display_surface, t('autosaved'), self.fonts['small'], 'save', alpha = int(255 * min(1, self.saved_flash / 0.4)), bottomright = (WINDOW_WIDTH - 16, WINDOW_HEIGHT - 50))
				wheel = spinner(self.saved_flash, 32)   # Iteration 32: the loading wheel spins next to it
				if wheel:
					wheel.set_alpha(int(255 * min(1, self.saved_flash / 0.4)))
					self.display_surface.blit(wheel, wheel.get_frect(midright = (tag.left - 8, tag.centery)))
			self.draw_toasts(dt)
			self.draw_achievements(dt)   # Iteration 25
			if self.preferences['speedrun_timer'] and not menu_open:
				hud_tag(self.display_surface, records.format_time(self.play_time), self.fonts['regular'], 'clock', topright = (WINDOW_WIDTH - 16, WINDOW_HEIGHT - 100))

			self.tint_screen(dt)

		# night mode tints the world, menus use their own night colours
		self.preferences.apply_night_mode(self.display_surface)
		if self.playing and not (self.battle or self.evolution or self.index_open):
			self.atmosphere.draw_lights(self.display_surface, self.all_sprites.offset)   # Iteration 20
		# Iteration 20: music is turned down while a jingle plays
		self.audio_manager.update(self.audio, self.music, 0 if self.preferences['muted'] else self.preferences['music_volume'] / 100)

		# a menu opened this frame must not receive the key that opened it
		self.ui.update(dt, events if menu_open else [])
		self.touch.draw(self.display_surface)
		self.preferences.apply_brightness(self.display_surface)
		pygame.display.update()
		controls.end_frame()

	# The game loop - runs frame() forever, working out dt from the clock each time.
	def run(self):
		while True:
			self.frame(min(self.clock.tick(FPS) / 1000, 0.1))   # Iteration 32: a slow frame never jumps the game forward more than 0.1 s

if __name__ == '__main__':
	game = Game()
	game.run()
