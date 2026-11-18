# battle.py
# Contains the Battle class, which controls a whole battle from start to finish: placing the
# monsters, the player's menus, the initiative turn order, damage, fainting, experience,
# catching and ending the battle. It is created by Game.end_dialog (trainer battle) or
# Game.monster_encounter (wild battle) and updated every frame from Game.run.

from settings import *
from sprites import MonsterSprite, MonsterNameSprite, MonsterLevelSprite, MonsterStatsSprite, MonsterOutlineSprite, AttackSprite, TimedSprite, DamageNumberSprite
from groups import BattleSprites
from game_data import ATTACK_DATA, CAPTURE_ORB_DATA, ITEM_DATA
from support import draw_bar
from timery import Timer
from localisation import t, attack_name
import controls
from random import choice, random
from math import sin, pi
import battle_rules as rules
import item_art
import options

# number of monsters each side can have on the field at once (positions top, center, bottom)
MAX_ACTIVE_MONSTERS = 3
# experience given per level of a defeated monster
XP_PER_DEFEATED_LEVEL = 100

# Iteration 14: returns the chance (0 to 1) of catching a monster with an orb.
# A monster on low health is easier to catch and better orbs multiply the chance.
def catch_chance(monster, orb):
	health_ratio = monster.health / monster.get_stat('max_health')
	return max(0, min(1, CAPTURE_ORB_DATA[orb]['rate'] * (1.1 - health_ratio) * options.state['catch']))   # Iteration 25: difficulty

# Iteration 14: returns how much faster every monster's turn bar should fill. If even the fastest
# monster on the field would wait longer than TURN_TIME seconds (e.g. low level monsters in the first
# battles), everything is sped up by the same amount, so the order of turns does not change.
def turn_speed_for(speeds):
	fastest = max(speeds, default = 0)
	if fastest <= 0:
		return 1
	return max(1, (100 / TURN_TIME) / fastest)

class Battle:
	# defaults so a half-built Battle (used by the tests) still works
	pending_catch = None
	versus = False         # Iteration 25: a local two-player battle
	crit_chance = 1 / 16   # Iteration 24 (the damage tests set it to 0 so their numbers are exact)
	vs_time = 0
	vs = None
	clouds = ()
	# Constructor.
	# Parameters: player_monsters / opponent_monsters (dict index -> Monster), monster_frames (dict of
	# images), bg_surf (background image for the biome), fonts (dict), end_battle (function in Game to
	# call when the battle is won), character (the trainer, or None for a wild battle), sounds (dict)
	# Iteration 14: inventory (dict, used for capture orbs) and tutorial (True in the player's first battle)
	# Iteration 18: use_item (function in Game that uses a potion/ether on a monster and returns a message)
	def __init__(self, player_monsters, opponent_monsters, monster_frames, bg_surf, fonts, end_battle, character, sounds, inventory = None, tutorial = False, use_item = None):
		# general
		self.display_surface = pygame.display.get_surface()   # the game window
		self.bg_surf = bg_surf                                # biome background
		self.monster_frames = monster_frames                  # monster, outline, icon, ui and attack images
		self.fonts = fonts
		self.monster_data = {'player': player_monsters, 'opponent': opponent_monsters}  # both teams
		self.battle_over = False      # stops end_battle being called more than once
		self.end_battle = end_battle  # callback into Game
		self.character = character    # trainer being fought, None if wild
		self.sounds = sounds
		self.inventory = inventory if inventory is not None else {}
		self.tutorial = tutorial
		self.selected_orb = None   # orb picked before choosing which monster to throw it at
		self.selected_item = None  # Iteration 18: potion/ether picked before choosing which monster gets it
		self.use_item = use_item
		self.shake_time = 0        # Iteration 18: seconds left of the screen shake after a super effective hit
		self.message = ''          # short text shown at the bottom, e.g. 'Caught!'
		self.log = []              # Iteration 21: every message this battle (the battle log)
		self.show_log = False      # Iteration 21: L opens and closes the log
		self.stuck_time = 0        # Iteration 16: seconds every monster has been paused with nobody's turn
		self.caught = []           # Iteration 16: monsters caught in this battle (offered a free nickname afterwards)

		# timers
		self.timers = {
			'opponent delay': Timer(600, func = self.opponent_attack),   # 'thinking time' before the opponent attacks
			'message': Timer(1800, func = self.clear_message),           # how long a battle message stays
			'catch': Timer(1500, func = self.finish_catch),             # Iteration 24: the orb wobbles before the result
		}
		self.level_ups = []          # Iteration 24: (name, new level) for the victory screen
		self.xp_gained = 0
		self.pending_catch = None
		self.vs_time = 0             # Iteration 24: seconds the VS intro is still showing (set by Game)
		self.vs = None
		self.clouds = [[random() * WINDOW_WIDTH, 30 + random() * 150, 60 + random() * 80, 10 + random() * 14] for _ in range(5)]

		# groups
		self.battle_sprites   = BattleSprites()            # everything drawn in the battle
		self.player_sprites   = pygame.sprite.Group()      # player's monsters on the field
		self.opponent_sprites = pygame.sprite.Group()      # opponent's monsters on the field

		# control
		self.current_monster = None     # MonsterSprite whose turn it is
		self.selection_mode  = None     # which menu is open: 'general', 'attacks', 'switch', 'target' or None
		self.selected_attack = None     # attack picked before choosing a target
		self.selection_side  = 'player' # which side the player is choosing a target on
		self.indexes = {                # highlighted option in each menu
			'general': 0,
			'monster': 0,
			'attacks': 0,
			'switch' : 0,
			'target' : 0,
			'orbs'   : 0,
			'items'  : 0,
		}

		self.starting = True   # Iteration 32: no cries while the teams first come out, just the battle-start jingle
		self.setup()
		self.starting = False
		if hasattr(self, 'sounds'):
			self.play_sound('battle_start')
		# Iteration 16: point out a shiny wild monster
		if any(monster.shiny for monster in opponent_monsters.values()) or any(sprite.monster.shiny for sprite in self.opponent_sprites):
			self.show_message(t('battle_shiny'))

	# Places the first three monsters of each team on the field.
	# Opponent monsters that are placed are removed from monster_data so that the
	# remaining ones can be sent out later as replacements. Called from: __init__
	def setup(self):
		# Iteration 36: the same number on each side - 1 v 1 against one monster, 2 v 2 against two and
		# 3 v 3 against three or more (the rest of the team waits and can be switched in)
		field = max(1, min(MAX_ACTIVE_MONSTERS, len(self.monster_data['opponent'])))
		for entity, monster in self.monster_data.items():
			for index, monster in {k:v for k,v in monster.items() if k < field}.items():
				self.create_monster(monster, index, index, entity)

			# remove opponent monster data
			for i in range(len(self.opponent_sprites)):
				del self.monster_data['opponent'][i]

	# Creates the sprite for one monster plus its outline, name, level and stats sprites.
	# Parameters: monster (Monster), index (key in its team dictionary), pos_index (0-2 field position),
	# entity ('player' or 'opponent'). Called from: setup, input (switch), MonsterSprite.destroy (replacement)
	def create_monster(self, monster, index, pos_index, entity):
		monster.paused = False
		frames = self.monster_frames['shiny' if monster.shiny else 'monsters'][monster.name]   # Iteration 16
		outline_frames = self.monster_frames['outlines'][monster.name]
		if getattr(monster, 'boss', False):   # Iteration 25: boss monsters are bigger
			frames = {state: [pygame.transform.scale_by(frame, 1.35) for frame in images] for state, images in frames.items()}
			outline_frames = {state: [pygame.transform.scale_by(frame, 1.35) for frame in images] for state, images in outline_frames.items()}
		if entity == 'player':
			pos = list(BATTLE_POSITIONS['left'].values())[pos_index]
			groups = (self.battle_sprites, self.player_sprites)
			# player monsters face right, so their frames are flipped horizontally
			frames = {state: [pygame.transform.flip(frame, True, False) for frame in frames] for state, frames in frames.items()}
			outline_frames = {state: [pygame.transform.flip(frame, True, False) for frame in frames] for state, frames in outline_frames.items()}
		else:
			pos = list(BATTLE_POSITIONS['right'].values())[pos_index]
			groups = (self.battle_sprites, self.opponent_sprites)

		monster_sprite = MonsterSprite(pos, frames, groups, monster, index, pos_index, entity, self.apply_attack, self.create_monster)
		MonsterOutlineSprite(monster_sprite, self.battle_sprites, outline_frames)

		# ui - Iteration 35: placed round the part of the picture the monster really fills, so the name tag
		# sits above it and the stats box below it (or beside it at the bottom of the screen) without
		# covering the monster
		body = self.visible_rect(monster_sprite)
		name_sprite = MonsterNameSprite((0, 0), monster_sprite, self.battle_sprites, self.fonts['regular'])
		level_sprite = MonsterLevelSprite(entity, (0, 0), monster_sprite, self.battle_sprites, self.fonts['small'])
		level_sprite.rect.height = name_sprite.rect.height
		level_sprite.image = pygame.Surface(level_sprite.rect.size)
		level_sprite.xp_rect = pygame.FRect(0, level_sprite.rect.height - 3, level_sprite.rect.width, 3)
		row_width = name_sprite.rect.width + 4 + level_sprite.rect.width
		name_sprite.rect.bottomleft = (body.centerx - row_width / 2, body.top - 6)
		level_sprite.rect.topleft = (name_sprite.rect.right + 4, name_sprite.rect.top)
		stats = MonsterStatsSprite((0, 0), monster_sprite, (150, 80), self.battle_sprites, self.fonts['small'])
		stats.rect.midtop = (body.centerx, body.bottom + 6)
		if stats.rect.bottom > WINDOW_HEIGHT - 72:   # the bottom row: slide sideways, clear of the key hints in the middle
			stats.rect.bottom = min(stats.rect.bottom, WINDOW_HEIGHT - 22)
			if entity == 'player':
				stats.rect.right = min(stats.rect.right, WINDOW_WIDTH / 2 - 250)
			else:
				stats.rect.left = max(stats.rect.left, WINDOW_WIDTH / 2 + 250)
		for sprite in (name_sprite, level_sprite, stats):
			sprite.rect.clamp_ip(pygame.FRect(6, 6, WINDOW_WIDTH - 12, WINDOW_HEIGHT - 12))
		# Iteration 24: opponents cry as they come out, and shiny monsters sparkle
		if entity == 'opponent' and hasattr(self, 'sounds') and not getattr(self, 'starting', False):
			self.play_sound(f'cry_{monster.name}')
		if monster.shiny:
			self.__dict__.setdefault('sparkles', []).append([monster_sprite, 1.6])

	# Handles the player's key presses while one of their monsters is taking a turn.
	# Up/down move through the current menu, space confirms and escape goes back.
	# Called every frame from update.
	def input(self):
		if controls.get_just_pressed()[pygame.K_l]:
			self.show_log = not self.show_log   # Iteration 21
		if self.selection_mode and self.current_monster:
			keys = controls.get_just_pressed()   # Iteration 16: also WASD and touch

			# limiter = number of options in the open menu, used for the range check below
			match self.selection_mode:
				case 'general': limiter = len(BATTLE_CHOICES['full'])
				case 'attacks': limiter = len(self.current_monster.monster.get_abilities(all = False))
				case 'switch': limiter = len(self.available_monsters)
				case 'orbs': limiter = len(self.owned_orbs())
				case 'items': limiter = len(self.owned_items())
				case 'target': limiter = len(self.opponent_sprites) if self.selection_side == 'opponent' else len(self.player_sprites)

			# range check: MOD keeps the index inside the list and wraps round at the ends
			if limiter > 0:
				if keys[pygame.K_DOWN]:
					self.indexes[self.selection_mode] = (self.indexes[self.selection_mode] + 1) % limiter
				if keys[pygame.K_UP]:
					self.indexes[self.selection_mode] = (self.indexes[self.selection_mode] - 1) % limiter
			if keys[pygame.K_SPACE] and limiter > 0:

				# switch the active monster for one from the party
				if self.selection_mode == 'switch':
					index, new_monster = list(self.available_monsters.items())[self.indexes['switch']]
					self.current_monster.kill()
					self.create_monster(new_monster, index, self.current_monster.pos_index, 'opponent' if getattr(self, 'swapped', False) else 'player')
					self.current_monster, self.selection_mode = None, None   # Iteration 16: forget the monster that left
					self.update_all_monsters('resume')

				# a target has been chosen - either for an attack or for catching
				if self.selection_mode == 'target':
					sprite_group = self.opponent_sprites if self.selection_side == 'opponent' else self.player_sprites
					sprites = {sprite.pos_index: sprite for sprite in sprite_group}
					monster_sprite = sprites[list(sprites.keys())[self.indexes['target']]]

					if self.selected_attack:
						self.use_move(self.current_monster, monster_sprite, self.selected_attack)
						self.selected_attack, self.current_monster, self.selection_mode = None, None, None
					elif self.selected_orb:
						self.throw_orb(monster_sprite)
					elif self.selected_item:
						self.give_item(monster_sprite)

				# an attack has been chosen - now the player picks a target
				if self.selection_mode == 'attacks':
					self.selection_mode = 'target'
					self.selected_attack = self.current_monster.monster.get_abilities(all = False)[self.indexes['attacks']]
					self.selection_side = ATTACK_DATA[self.selected_attack]['target']

				# Iteration 18: an item has been chosen - now the player picks which of their monsters gets it
				if self.selection_mode == 'items':
					self.selected_item = self.owned_items()[self.indexes['items']]
					self.selection_mode = 'target'
					self.selection_side = 'player'

				# an orb has been chosen - now the player picks which wild monster to throw it at
				if self.selection_mode == 'orbs':
					self.selected_orb = self.owned_orbs()[self.indexes['orbs']]
					self.selection_mode = 'target'
					self.selection_side = 'opponent'

				# main menu - Iteration 18: options are looked up by name, so adding 'items' did not
				# change the meaning of any of the other numbers
				if self.selection_mode == 'general':
					option = list(BATTLE_CHOICES['full'])[self.indexes['general']]
					if option == 'items':
						if self.owned_items() and self.use_item:
							self.selection_mode = 'items'
						else:
							self.show_message(t('battle_no_items'))

					if option == 'fight':
						# Iteration 15: an empty attack list used to leave the player stuck
						if self.current_monster.monster.get_abilities(all = False):
							self.selection_mode = 'attacks'
						else:
							self.show_message(t('battle_no_energy'))

					if option == 'defend':
						self.current_monster.monster.defend()
						self.update_all_monsters('resume')
						self.current_monster, self.selection_mode = None, None
						self.indexes['general'] = 0

					if option == 'switch':
						self.selection_mode = 'switch'

					# Iteration 14: catching needs an orb, a wild monster and space in the party
					if option == 'catch':
						if self.character is not None or self.versus:
							self.show_message(t('battle_catch_trainer'))
						elif len(self.monster_data['player']) >= MAX_PARTY_SIZE and getattr(self, 'storage', None) is None:
							self.show_message(t('battle_party_full', amount = MAX_PARTY_SIZE))
						elif not self.owned_orbs():
							self.show_message(t('battle_no_orbs'))
						else:
							self.selection_mode = 'orbs'

					# Iteration 16: run away from a wild battle (not allowed against a trainer)
					if option == 'run':
						if self.character is not None:
							self.show_message(t('battle_run_trainer'))
						else:
							self.run_away()
				self.indexes = {k: 0 for k in self.indexes}

			if keys[pygame.K_ESCAPE]:
				if self.selection_mode in ('attacks', 'switch', 'target', 'orbs', 'items'):
					self.selection_mode = 'general'
					self.selected_attack, self.selected_orb, self.selected_item = None, None, None

	# catching (Iteration 14)
	# Returns the names of the orbs the player has at least one of.
	def owned_orbs(self):
		return [orb for orb in CAPTURE_ORB_DATA if self.inventory.get(orb, 0) > 0]

	# Throws the selected orb at a wild monster. The orb is used up whether or not it works, and
	# throwing uses up the monster's turn. A random number decides if the catch works.
	def throw_orb(self, monster_sprite):
		orb, self.selected_orb = self.selected_orb, None
		self.inventory[orb] -= 1
		# Iteration 24: the orb wobbles three times first; finish_catch shows the result
		success = random() < catch_chance(monster_sprite.monster, orb)
		monster_sprite.hidden = True
		self.pending_catch = (monster_sprite, success, orb)
		self.timers['catch'].activate()
		self.current_monster, self.selection_mode = None, None

	def finish_catch(self):
		if not self.pending_catch:
			return
		monster_sprite, success, orb = self.pending_catch
		self.pending_catch = None
		if not success:
			monster_sprite.hidden = False
		if success:
			monster = monster_sprite.monster
			monster.initiative, monster.turn_speed = 0, 1
			if len(self.monster_data['player']) >= MAX_PARTY_SIZE and getattr(self, 'storage', None) is not None:
				self.storage.append(monster)   # Iteration 22: the party is full, so it goes to the PC box
				self.show_message(t('battle_caught_box', monster = monster.name))
			else:
				self.monster_data['player'][len(self.monster_data['player'])] = monster
				self.show_message(t('battle_caught', monster = monster.name))
			self.caught.append(monster)
			monster_sprite.delayed_kill(None)
			self.sounds['catch'].play() if 'catch' in self.sounds else None   # Iteration 18
		else:
			# show a red cross so the player knows the catch failed
			TimedSprite(monster_sprite.rect.center, self.monster_frames['ui']['cross'], self.battle_sprites, 1000)
			self.show_message(t('battle_catch_failed', monster = monster_sprite.monster.name))
			self.sounds['catch_fail'].play() if 'catch_fail' in self.sounds else None   # Iteration 18
		self.current_monster, self.selection_mode = None, None
		self.update_all_monsters('resume')

	# Iteration 16: leaves a wild battle. The player's monsters keep the experience they already earned.
	def run_away(self):
		self.battle_over = True
		self.current_monster, self.selection_mode = None, None
		for monster in self.monster_data['player'].values():
			monster.initiative, monster.paused = 0, False
		self.end_battle(None)

	# Iteration 18: items in battle
	# Returns the healing items (potion, ether) the player has at least one of.
	def owned_items(self):
		return [item for item in ITEM_DATA if self.inventory.get(item, 0) > 0]

	# Uses the selected item on one of the player's monsters. Uses up the monster's turn, like in other
	# monster games, unless the item had no effect (then the player can choose again).
	def give_item(self, monster_sprite):
		item, self.selected_item = self.selected_item, None
		before = self.inventory.get(item, 0)
		self.show_message(self.use_item(item, monster_sprite.monster))
		if self.inventory.get(item, 0) < before:
			self.sounds['heal'].play() if 'heal' in self.sounds else None
			self.current_monster, self.selection_mode = None, None
			self.update_all_monsters('resume')
		else:
			self.selection_mode = 'general'

	# Shows a message at the bottom of the battle for 1.8 seconds.
	def show_message(self, text):
		self.message = text
		self.__dict__.setdefault('log', [])
		# Iteration 21: every message also goes in the battle log (L shows the last 6)
		if text and (not self.log or self.log[-1] != text):
			self.log.append(text)
		if 'message' in getattr(self, 'timers', {}):
			self.timers['message'].activate()

	def clear_message(self):
		self.message = ''

	# Updates every timer owned by the battle. Called every frame from update.
	def update_timers(self):
		for timer in self.timers.values():
			timer.update()


	# battle system
	# Checks if any monster's initiative has reached 100. If so, pauses everyone, resets that
	# monster's initiative and gives it the turn (menu for the player, timer for the opponent).
	# Called every frame from update.
	# Iteration 16: a fainted monster that has not disappeared yet can no longer take a turn (its attack
	# never finished, so the battle froze), and only one monster can start a turn per frame.
	def check_active(self):
		# Iteration 36: while a turn is happening everyone is paused, and no other monster may start a turn.
		# (Two monsters with the same speed reach 100 on the same frame, and the second one used to take the
		# turn away a frame later - the menu stayed on screen but the keys did nothing.)
		if any(sprite.monster.paused for sprite in self.player_sprites.sprites() + self.opponent_sprites.sprites()):
			return
		for monster_sprite in self.player_sprites.sprites() + self.opponent_sprites.sprites():
			if monster_sprite.monster.health <= 0:
				continue
			if monster_sprite.monster.initiative >= 100:
				monster_sprite.monster.defending = False
				monster_sprite.monster.regain_energy()   # Iteration 15
				self.update_all_monsters('pause')
				monster_sprite.monster.initiative = 0
				monster_sprite.set_highlight(True)
				self.current_monster = monster_sprite
				# Iteration 21: burn and poison hurt, freeze and sleep can skip the turn
				monster = monster_sprite.monster
				can_act, message, damage = rules.start_of_turn(monster)
				if message:
					self.show_message(t(message, monster = monster.display_name))
					if damage:
						DamageNumberSprite(monster_sprite.rect.midtop, str(max(1, round(damage))), self.fonts['bold'], COLORS[{'burn': 'fire', 'poison': 'poison'}.get(monster.status, 'light')], self.battle_sprites)
					if monster.status == 'confused' and 'confused' in self.monster_frames['attacks']:
						AttackSprite(monster_sprite.rect.center, self.monster_frames['attacks']['confused'], self.battle_sprites)   # Iteration 32: stars spin round its head
				if monster.health <= 0:
					self.current_monster = None
					self.check_death()
					self.update_all_monsters('resume')
					return
				if not can_act:
					self.current_monster = None
					self.update_all_monsters('resume')
					return
				# Iteration 21: a charged move (or one waiting to strike last) is released now, with no menu
				if monster.charging:
					target, attack = monster.charging
					monster.charging = None
					side = self.opponent_sprites if self.player_sprites in monster_sprite.groups() else self.player_sprites
					if target is None or not target.groups() or target.monster.health <= 0:
						target = choice(side.sprites()) if side.sprites() else None
					if target is not None:
						monster_sprite.activate_attack(target, attack, pay = False)
						return
					self.update_all_monsters('resume')
					return
				if self.player_sprites in monster_sprite.groups():
					self.selection_mode = 'general'
				elif self.versus:
					self.swap_sides()   # Iteration 25: player 2 chooses
					self.selection_mode = 'general'
				else:
					self.timers['opponent delay'].activate()
				return

	# Iteration 16: safety checks so a battle can never freeze.
	# 1. If the monster whose turn it is has fainted or gone, its turn is cancelled.
	# 2. If every monster is paused but nobody is taking a turn for over 2 seconds, they are resumed.
	def check_stuck(self, dt):
		current = self.current_monster
		if current and (not current.groups() or current.monster.health <= 0) and current.state != 'attack':
			self.current_monster, self.selection_mode = None, None
			self.selected_attack, self.selected_orb = None, None
			self.timers['opponent delay'].deactivate()
			self.update_all_monsters('resume')
		sprites = self.player_sprites.sprites() + self.opponent_sprites.sprites()
		waiting = self.selection_mode or self.timers['opponent delay'].active or any(sprite.state == 'attack' for sprite in sprites) or self.pending_catch or self.vs_time > 0
		if sprites and not waiting and all(sprite.monster.paused for sprite in sprites):
			self.stuck_time += dt
			if self.stuck_time > 2:
				self.current_monster = None
				self.update_all_monsters('resume')
		else:
			self.stuck_time = 0

	# Pauses or resumes initiative for every monster on the field.
	# Parameter: option ('pause' or 'resume'). Called from: input, check_active, apply_attack
	def update_all_monsters(self, option):
		for monster_sprite in self.player_sprites.sprites() + self.opponent_sprites.sprites():
			monster_sprite.monster.paused = True if option == 'pause' else False

	# Applies an attack to a target once the attack animation has finished.
	# Parameters: target_sprite (MonsterSprite), attack (string key of ATTACK_DATA), amount (real, base damage)
	# Applies the element matchup, then the defence multiplier, then reduces the target's health.
	# Called from: MonsterSprite.animate
	# Iteration 18: attacker (the MonsterSprite attacking) is used to say "X used Y!".
	def apply_attack(self, target_sprite, attack, amount, attacker = None):
		# validation: the target must still exist and the attack must be a real attack
		if target_sprite is None or not target_sprite.groups() or attack not in ATTACK_DATA:
			self.update_all_monsters('resume')
			return

		data = ATTACK_DATA[attack]
		AttackSprite(target_sprite.rect.center, self.monster_frames['attacks'][data['animation']], self.battle_sprites, rules.animation_scale(attack))
		# Iteration 21: the original attacks keep their own sound, the new ones use their type's hit sound
		hit = f"hit_{data['element']}" if f"hit_{data['element']}" in self.sounds else 'hit_normal'
		sound = data.get('sound', data['animation'])   # Iteration 34: recoloured animations keep their old sound
		self.play_sound(sound if sound in self.sounds else hit)
		target = target_sprite.monster
		name = attacker.monster.display_name if attacker is not None else ''

		# Iteration 24: a critical hit (1 in 16) does 1.5 times the damage
		happy_attacker = attacker is not None and getattr(attacker, 'monster', None) is not None and attacker.monster.is_happy()
		critical = random() < self.crit_chance * (2 if happy_attacker else 1)   # Iteration 25: happy monsters crit twice as often
		if critical:
			amount *= 1.5

		# Iteration 21: accuracy - big moves can miss
		if not rules.hits(attack):
			self.show_message(t('battle_missed', monster = name, attack = attack_name(attack)))
			self.play_sound('miss')
			self.update_all_monsters('resume')
			return

		# Iteration 32: healing moves (Heal, Grassy Heal) heal one of your own monsters
		if data.get('kind') == 'heal':
			healed = min(target.get_stat('max_health') - target.health, target.get_stat('max_health') * data['heal'])
			target.health += healed
			fonts = getattr(self, 'fonts', None)
			if fonts:
				DamageNumberSprite(target_sprite.rect.midtop, f'+{max(0, round(healed))}', fonts['bold'], COLORS['plant'], self.battle_sprites)
			self.show_message(t('battle_healed', monster = target.display_name) if healed > 0 else t('battle_no_effect', monster = target.display_name))
			self.play_sound('heal') if 'heal' in self.sounds else None
			self.update_all_monsters('resume')
			return

		# Iteration 21: moves that do no damage change a stat or give a status instead
		if rules.is_status_move(attack):
			self.apply_side_effects(target_sprite, attack, name)
			self.update_all_monsters('resume')
			return

		# get correct attack damage amount (defense, type chart - Iteration 21)
		attack_element = data['element']
		multiplier, effect = rules.effectiveness(attack_element, *rules.types_of(target))
		amount *= multiplier

		# defence multiplier between 0 and 1 (lower means less damage gets through)
		target_defense = 1 - target_sprite.monster.get_stat('defense') / 2000
		if target_sprite.monster.defending:
			target_defense -= 0.2
		target_defense = max(0, min(1, target_defense))   # range check (clamp)

		# update the monster health (Iteration 32: scaled down so battles last a few turns)
		damage = amount * target_defense * rules.DAMAGE_SCALE
		target_sprite.monster.health -= damage
		# Iteration 25: a very happy monster of yours sometimes hangs on with 1 health (once per battle)
		if target.health <= 0 and self.player_sprites in target_sprite.groups() and target.is_happy() and not getattr(target, 'hung_on', False) and random() < 0.25:
			target.health, target.hung_on = 1, True
			self.show_message(t('battle_hung_on', monster = target.display_name))

		# Iteration 18: explain what happened - a floating damage number, a message and a shake
		self.announce_attack(attacker, attack, target_sprite, damage, effect)
		target_sprite.knock = 1.0   # Iteration 24: the target is knocked back a little
		if critical:
			self.crits = getattr(self, 'crits', 0) + 1   # Iteration 25: counted for the stats screen
			self.show_message(f"{getattr(self, 'message', '')} {t('battle_critical')}")
			self.play_sound('crit')
			self.shake_time = 0.35
		if target.health > 0:
			if target.status == 'freeze' and attack_element == 'fire':
				target.status = None   # Iteration 21: fire melts the ice
			self.apply_side_effects(target_sprite, attack, name, quiet = True)
		# Iteration 32: some moves can affect the attacker too (Headbutt can leave both monsters dizzy)
		self_status = data.get('self_status')
		if self_status and attacker is not None and getattr(attacker, 'monster', None) is not None and attacker.monster.health > 0 and not attacker.monster.status:
			if random() < self_status[1]:
				rules.give_status(attacker.monster, self_status[0])
				current = getattr(self, 'message', '')
				self.show_message(f"{current} {t(f'status_given_{self_status[0]}', monster = attacker.monster.display_name)}".strip())
		self.check_death()

		# resume
		self.update_all_monsters('resume')

	# Iteration 21: a move's extra effect - a status (burn, freeze, poison, sleep) or a stat change.
	# quiet = True when the attack's own message is already showing (the status is added to it).
	def apply_side_effects(self, target_sprite, attack, name, quiet = False):
		target, data = target_sprite.monster, ATTACK_DATA[attack]
		status = rules.try_status(target, attack)
		if status:
			text = t(f'status_given_{status}', monster = target.display_name)
			current = getattr(self, 'message', '')
			self.show_message(f'{current} {text}' if quiet and current else text)
			self.play_sound('status')
		elif 'stat' in data and (rules.is_status_move(attack) or random() < data.get('stat_chance', 1)):
			stat, change = data['stat']
			done = rules.change_stage(target, stat, change)
			key = 'stat_fell' if done < 0 else 'stat_rose' if done > 0 else 'stat_unchanged'
			self.show_message(t(key, monster = target.display_name, stat = t(f'stat_{stat}')))
			self.play_sound('stat_down' if done < 0 else 'stat_up')
		elif not quiet:
			self.show_message(t('battle_no_effect', monster = target.display_name))

	# Iteration 18: "Blaze used fire! It's super effective!", the damage floating up from the target
	# (orange if super effective, grey if not very effective) and a small screen shake on big hits.
	def announce_attack(self, attacker, attack, target_sprite, damage, effect):
		fonts = getattr(self, 'fonts', None)
		if fonts:
			color = {'super': COLORS['fire'], 'weak': COLORS['light']}.get(effect, COLORS['white'])
			DamageNumberSprite(target_sprite.rect.midtop, str(max(1, round(damage))), fonts['bold'], color, self.battle_sprites)
		if attacker is not None and hasattr(self, 'timers'):
			text = t('battle_used', monster = attacker.monster.display_name, attack = attack_name(attack))
			if effect:
				text = f"{text} {t(f'battle_effect_{effect}')}"
			self.show_message(text)
		if effect == 'super':
			self.shake_time = 0.25
			if 'super_hit' in self.sounds:
				self.sounds['super_hit'].play()

	# Checks every monster for 0 health. A fainted player monster is replaced by the next healthy
	# party member; a fainted opponent is replaced by the next one in its team and gives experience.
	# Called from: apply_attack
	def check_death(self):
		for monster_sprite in self.opponent_sprites.sprites() + self.player_sprites.sprites():
			if monster_sprite.monster.health <= 0:
				if self.player_sprites in monster_sprite.groups(): # player
					monster_sprite.monster.change_happiness(-3)   # Iteration 25
					active_monsters = [(monster_sprite.index, monster_sprite.monster) for monster_sprite in self.player_sprites.sprites()]
					available_monsters = [(index, monster) for index, monster in self.monster_data['player'].items() if monster.health > 0 and (index, monster) not in active_monsters]
					if available_monsters:
						new_monster_data = [(monster, index, monster_sprite.pos_index, 'player') for index, monster in available_monsters][0]
					else:
						new_monster_data = None
				else:
					new_monster_data = (list(self.monster_data['opponent'].values())[0], monster_sprite.index, monster_sprite.pos_index, 'opponent') if self.monster_data['opponent'] else None
					if self.monster_data['opponent']:
						del self.monster_data['opponent'][min(self.monster_data['opponent'])]
					self.award_xp(monster_sprite.monster)
					self.__dict__.setdefault('beaten', []).append(monster_sprite.monster.name)   # Iteration 25: for bounties

				monster_sprite.delayed_kill(new_monster_data)

	# Shares experience for a defeated opponent equally between the player's monsters on the field.
	# Parameter: defeated_monster (Monster). Iteration 6: moved out of check_death into its own
	# subroutine and given a check so it never divides by zero.
	def award_xp(self, defeated_monster):
		active_count = len(self.player_sprites)
		# validation: if no player monsters are on the field there is no one to give xp to
		if active_count == 0:
			return
		xp_amount = defeated_monster.level * XP_PER_DEFEATED_LEVEL / active_count * options.state['xp']   # Iteration 25: difficulty
		for player_sprite in self.player_sprites:
			level = player_sprite.monster.level
			player_sprite.monster.update_xp(xp_amount)
			self.xp_gained = getattr(self, 'xp_gained', 0) + xp_amount
			# Iteration 18: a sound and a message when a monster levels up
			if player_sprite.monster.level > level:
				player_sprite.glow_time = 1.5   # Iteration 24: glows gold
				player_sprite.monster.change_happiness(3)   # Iteration 25
				self.level_ups.append((player_sprite.monster.display_name, player_sprite.monster.level))
			if player_sprite.monster.level > level and hasattr(self, 'timers'):
				self.sounds['level_up'].play() if 'level_up' in self.sounds else None
				self.show_message(t('battle_level_up', monster = player_sprite.monster.display_name, level = player_sprite.monster.level))

	# Chooses and starts the opponent's attack after the 600 ms delay timer.
	# Iteration 5 change: only chooses from attacks the monster can afford (get_abilities(all = False)),
	# and defends instead if it cannot afford any. Called from: the 'opponent delay' timer
	def opponent_attack(self):
		if self.current_monster is None or not self.current_monster.groups() or self.current_monster.monster.health <= 0:
			self.update_all_monsters('resume')   # Iteration 16: the battle used to freeze here
			return
		abilities = self.current_monster.monster.get_abilities(all = False)
		if not abilities or not self.player_sprites:
			# not enough energy for any attack - defend this turn instead
			self.current_monster.monster.defend()
			self.update_all_monsters('resume')
			return
		ability = choice(abilities)
		# healing moves target the opponent's own side, damaging moves target the player's side
		random_target = choice(self.opponent_sprites.sprites()) if ATTACK_DATA[ability]['target'] == 'player' else choice(self.player_sprites.sprites())
		self.use_move(self.current_monster, random_target, ability)

	# Iteration 21: starts a move. A charge-up move (Solar Beam...) or a move that strikes last (Annihilate)
	# is paid for now and stored; it is released at the start of the monster's next turn (check_active).
	# A priority move acts now and leaves the monster with a head start towards its next turn.
	def use_move(self, sprite, target, attack):
		monster = sprite.monster
		if rules.is_charge(attack) or rules.priority(attack) < 0:
			monster.reduce_energy(attack)
			monster.charging = (target, attack)
			key = 'battle_charging' if rules.is_charge(attack) else 'battle_waiting'
			self.show_message(t(key, monster = monster.display_name, attack = attack_name(attack)))
			self.play_sound('status')
			monster.initiative = 0 if rules.is_charge(attack) else rules.LAST_WAIT
			self.update_all_monsters('resume')
			return
		sprite.activate_attack(target, attack)
		if rules.priority(attack) > 0:
			monster.initiative = rules.PRIORITY_HEAD_START

	def play_sound(self, name):
		if name in self.sounds:
			self.sounds[name].play()

	# Ends the battle when one side has no monsters left on the field. Called every frame from update.
	# Iteration 12 change: losing no longer closes the game - the Game is told the battle was lost instead.
	def check_end_battle(self):
		# opponents have been defeated
		if len(self.opponent_sprites) == 0 and not self.battle_over:
			self.battle_over = True
			self.end_battle(self.character)
			for monster in self. monster_data['player'].values():
				monster.initiative = 0

		# player has been defeated - battle_over stops this being called more than once
		if len(self.player_sprites) == 0 and not self.battle_over:
			self.battle_over = True
			for monster in self.monster_data['player'].values():
				monster.initiative = 0
			self.end_battle(self.character, lost = True)


	# ui
	# Draws whichever menu is currently open next to the active player monster. Called from update.
	def draw_ui(self):
		if self.current_monster:
			if self.selection_mode == 'general':
				self.draw_general()
			if self.selection_mode == 'attacks':
				self.draw_attacks()
			if self.selection_mode == 'switch':
				self.draw_switch()
			if self.selection_mode == 'orbs':
				self.draw_orbs()
			if self.selection_mode == 'items':
				self.draw_items()
		self.draw_catch()
		self.draw_sparkles()
		self.draw_help()
		if self.show_log:
			self.draw_log()

	# Iteration 25: menus open on the right of the monster whose turn it is, or on its left for a monster
	# on the right of the screen (player 2 in a local battle), so they never go off the screen.
	def on_right(self):
		return self.current_monster.rect.centerx > WINDOW_WIDTH / 2

	def menu_point(self, offset):
		offset = vector(offset)
		if self.on_right():
			return self.current_monster.rect.midleft + vector(-offset.x, offset.y)
		return self.current_monster.rect.midright + offset

	# Iteration 35: the part of a monster's picture it really fills (the frames have empty space round them)
	def visible_rect(self, monster_sprite):
		frames = monster_sprite.frames['idle']
		boxes = [frame.get_bounding_rect() for frame in frames]
		box = boxes[0].unionall(boxes[1:])
		return pygame.FRect(box).move(monster_sprite.rect.topleft)

	def place_menu(self, rect):
		if self.on_right():
			return rect.move_to(midright = self.current_monster.rect.midleft - vector(20, 0))
		return rect.move_to(midleft = self.current_monster.rect.midright + vector(20, 0))

	# ---------- Iteration 25: local two-player battles ----------
	# On player 2's turn the two sides are swapped, so all the menu code works for them unchanged.
	def swap_sides(self):
		self.player_sprites, self.opponent_sprites = self.opponent_sprites, self.player_sprites
		self.monster_data['player'], self.monster_data['opponent'] = self.monster_data['opponent'], self.monster_data['player']
		self.swapped = not getattr(self, 'swapped', False)

	def acting_side(self):
		if self.current_monster and self.selection_mode:
			return 'opponent' if getattr(self, 'swapped', False) else 'player'
		return None

	# Iteration 24: soft clouds drifting across the sky behind the monsters
	def draw_clouds(self, dt):
		layer = pygame.Surface((WINDOW_WIDTH, 260), pygame.SRCALPHA)
		for cloud in self.clouds:
			cloud[0] += cloud[3] * dt
			if cloud[0] > WINDOW_WIDTH + cloud[2]:
				cloud[0] = -cloud[2]
			x, y, w = cloud[0], cloud[1], cloud[2]
			for dx, dy, scale in ((0, 0, 1), (w * 0.35, -8, 0.7), (-w * 0.3, 4, 0.6)):
				pygame.draw.ellipse(layer, (255, 255, 255, 115), (x + dx - w * scale / 2, y + dy - 12 * scale, w * scale, 26 * scale))
		self.display_surface.blit(layer, (0, 0))

	# Iteration 24: four-pointed stars around a shiny monster for a moment after it appears
	def draw_sparkles(self):
		sparkles = self.__dict__.get('sparkles', [])
		for sparkle in sparkles[:]:
			sprite, left = sparkle
			sparkle[1] -= 1 / 60
			if left <= 0 or not sprite.groups():
				sparkles.remove(sparkle)
				continue
			for i in range(6):
				angle = i * pi / 3 + left * 2
				distance = 70 + 20 * sin(left * 6 + i)
				x, y = sprite.rect.centerx + distance * sin(angle), sprite.rect.centery + distance * sin(angle + pi / 2) * 0.7
				size = 4 + 8 * abs(sin(left * 5 + i))
				colour = (255, 240, 150)
				pygame.draw.polygon(self.display_surface, colour, [(x, y - size), (x + size / 4, y - size / 4), (x + size, y), (x + size / 4, y + size / 4), (x, y + size), (x - size / 4, y + size / 4), (x - size, y), (x - size / 4, y - size / 4)])

	# Iteration 24: the orb wobbling three times while a catch is decided
	def draw_catch(self):
		if not self.pending_catch:
			return
		sprite, success, orb = self.pending_catch
		elapsed = (pygame.time.get_ticks() - self.timers['catch'].start_time) / 1000
		angle = sin(elapsed * 3 * 2 * pi / 1.5) * 25 * max(0, 1 - elapsed / 1.6)
		picture = pygame.transform.rotate(item_art.item(orb, 56), angle)
		self.display_surface.blit(picture, picture.get_frect(center = sprite.rect.center + vector(0, 30)))

	# Iteration 24: split screen with both trainers and a big VS
	def draw_vs(self):
		left_frames, right_frames, name = self.vs
		progress = min(1, (2.2 - self.vs_time) / 0.35)
		shade = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
		pygame.draw.polygon(shade, (40, 60, 140, 235), [(0, 0), (WINDOW_WIDTH * 0.58 * progress, 0), (WINDOW_WIDTH * 0.42 * progress, WINDOW_HEIGHT), (0, WINDOW_HEIGHT)])
		pygame.draw.polygon(shade, (160, 40, 50, 235), [(WINDOW_WIDTH, 0), (WINDOW_WIDTH - WINDOW_WIDTH * 0.42 * progress, 0), (WINDOW_WIDTH - WINDOW_WIDTH * 0.58 * progress, WINDOW_HEIGHT), (WINDOW_WIDTH, WINDOW_HEIGHT)])
		self.display_surface.blit(shade, (0, 0))
		player = pygame.transform.scale_by(left_frames['right_idle'][0] if 'right_idle' in left_frames else left_frames['down_idle'][0], 2.4)
		leader = pygame.transform.scale_by(right_frames['left_idle'][0] if 'left_idle' in right_frames else right_frames['down_idle'][0], 2.4)
		self.display_surface.blit(player, player.get_frect(center = (WINDOW_WIDTH * 0.22 * progress + 40, WINDOW_HEIGHT / 2)))
		self.display_surface.blit(leader, leader.get_frect(center = (WINDOW_WIDTH - WINDOW_WIDTH * 0.22 * progress - 40, WINDOW_HEIGHT / 2)))
		vs = pygame.transform.scale_by(self.fonts['bold'].render('VS', False, COLORS['gold']), 3 + 0.3 * sin(self.vs_time * 12))
		self.display_surface.blit(vs, vs.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)))
		label = self.fonts['bold'].render(name, False, COLORS['white'])
		self.display_surface.blit(label, label.get_frect(center = (WINDOW_WIDTH * 0.78, WINDOW_HEIGHT * 0.82)))

	# Iteration 21: the last 6 things that happened, in a panel at the top right (L to open/close)
	def draw_log(self):
		lines = self.log[-6:]
		font = self.fonts['small']
		width = 420
		panel = pygame.FRect(WINDOW_WIDTH - width - 16, 16, width, 34 + 24 * max(1, len(lines)))
		layer = pygame.Surface(panel.size, pygame.SRCALPHA)
		pygame.draw.rect(layer, (30, 28, 36, 215), layer.get_frect(), 0, 8)
		layer.blit(font.render(t('battle_log'), False, COLORS['gold']), (12, 8))
		for row, line in enumerate(lines):
			text = font.render(line if font.size(line)[0] < width - 24 else line[:58] + '...', False, COLORS['white'])
			layer.blit(text, (12, 32 + row * 24))
		self.display_surface.blit(layer, panel)

	# Iteration 14: the list of orbs the player owns, with how many of each and the catch chance
	# for the weakest opponent so the player can decide which orb to use.
	def draw_orbs(self):
		orbs = self.owned_orbs()
		width, item_height = 260, 44
		bg_rect = self.place_menu(pygame.FRect((0,0), (width, item_height * len(orbs))))
		pygame.draw.rect(self.display_surface, COLORS['white'], bg_rect, 0, 5)
		weakest = min((sprite.monster for sprite in self.opponent_sprites), key = lambda monster: monster.health / monster.get_stat('max_health'), default = None)
		for index, orb in enumerate(orbs):
			selected = index == self.indexes['orbs']
			row = pygame.FRect(bg_rect.left, bg_rect.top + index * item_height, width, item_height)
			if selected:
				pygame.draw.rect(self.display_surface, COLORS['dark white'], row, 0, 5)
			chance = f'  {int(catch_chance(weakest, orb) * 100)}%' if weakest else ''
			text_surf = self.fonts['regular'].render(f"{t(f'item_{orb}')} x{self.inventory[orb]}{chance}", False, COLORS['red'] if selected else COLORS['black'])
			self.display_surface.blit(text_surf, text_surf.get_frect(midleft = row.midleft + vector(14, 0)))

	# Iteration 18: the list of healing items with how many the player has.
	def draw_items(self):
		items = self.owned_items()
		width, item_height = 240, 44
		bg_rect = self.place_menu(pygame.FRect((0,0), (width, item_height * len(items))))
		pygame.draw.rect(self.display_surface, COLORS['white'], bg_rect, 0, 5)
		for index, item in enumerate(items):
			selected = index == self.indexes['items']
			row = pygame.FRect(bg_rect.left, bg_rect.top + index * item_height, width, item_height)
			if selected:
				pygame.draw.rect(self.display_surface, COLORS['dark white'], row, 0, 5)
			# Iteration 19: each item shows its bottle (red potion / blue ether), highlighted when selected
			image = self.monster_frames['ui'].get(f"{item}_highlight" if selected else item)
			if image:
				self.display_surface.blit(image, image.get_frect(midleft = row.midleft + vector(8, 0)))
			text_surf = self.fonts['regular'].render(f"{t(f'item_{item}')} x{self.inventory[item]}", False, COLORS['red'] if selected else COLORS['black'])
			self.display_surface.blit(text_surf, text_surf.get_frect(midleft = row.midleft + vector(48, 0)))

	# Iteration 14: control hints at the bottom during the player's turn, battle messages, and the
	# tutorial box at the top during the player's first battle.
	def draw_help(self):
		def box(text, **anchor):
			text_surf = self.fonts['regular'].render(text, False, COLORS['black'])
			rect = text_surf.get_frect(**anchor).inflate(28, 18)
			pygame.draw.rect(self.display_surface, COLORS['white'], rect, 0, 8)
			self.display_surface.blit(text_surf, text_surf.get_frect(center = rect.center))
			return rect

		players_turn = self.current_monster and self.selection_mode and self.player_sprites.has(self.current_monster)
		bottom = WINDOW_HEIGHT - 24
		if players_turn:
			bottom = box(t('battle_hint'), midbottom = (WINDOW_WIDTH / 2, bottom)).top - 10
		if self.message:
			box(self.message, midbottom = (WINDOW_WIDTH / 2, bottom))
		if self.tutorial:
			step = self.selection_mode if players_turn else 'wait'
			lines = t(f'tutorial_{step}').split('|')
			for row, line in enumerate(lines):
				box(line, midtop = (WINDOW_WIDTH / 2, 16 + row * 40))

	# Draws the four action icons (fight, defend, switch, catch); the selected one is highlighted.
	def draw_general(self):
		for index, (option, data_dict) in enumerate(BATTLE_CHOICES['full'].items()):
			if index == self.indexes['general']:
				# the run icon (cross) has no separate highlight image, so the coloured one is used
				surf = self.monster_frames['ui'].get(f"{data_dict['icon']}_highlight", self.monster_frames['ui'][data_dict['icon']])
			else:
				surf = pygame.transform.grayscale(self.monster_frames['ui'][data_dict['icon']])
			rect = surf.get_frect(center = self.menu_point(data_dict['pos']))
			self.display_surface.blit(surf, rect)
			# Iteration 34: the selected option's name on a small tag beside its icon
			if index == self.indexes['general']:
				label = self.fonts['regular'].render(t(f'choice_{option}'), False, COLORS['white'])
				tag = label.get_frect().inflate(18, 8)
				if self.on_right():
					tag.midright = (rect.left - 8, rect.centery)
				else:
					tag.midleft = (rect.right + 8, rect.centery)
				pygame.draw.rect(self.display_surface, (34, 32, 40), tag, 0, 6)
				self.display_surface.blit(label, label.get_frect(center = tag.center))

	# Draws the scrolling list of attacks the active monster can afford, and a panel saying what the
	# selected move does. Iteration 34: dark text on white with the selected row filled in its type's
	# colour (the old pale grey and yellow text was hard to read), a type icon on every row and arrows
	# when the list scrolls.
	def draw_attacks(self):
		abilities = self.current_monster.monster.get_abilities(all = False)
		width, item_height, visible = 210, 42, 4
		height = item_height * visible
		first = max(0, self.indexes['attacks'] - visible + 1)
		bg_rect = self.place_menu(pygame.FRect((0, 0), (width, height)))
		bg_rect.clamp_ip(pygame.FRect(8, 8, WINDOW_WIDTH - 16, WINDOW_HEIGHT - 16))
		pygame.draw.rect(self.display_surface, COLORS['white'], bg_rect, 0, 6)
		pygame.draw.rect(self.display_surface, '#3a373b', bg_rect, 2, 6)

		targets = [rules.types_of(sprite.monster) for sprite in self.opponent_sprites]
		for row, ability in enumerate(abilities[first:first + visible]):
			index = first + row
			selected = index == self.indexes['attacks']
			data = ATTACK_DATA[ability]
			row_rect = pygame.FRect(bg_rect.left + 3, bg_rect.top + 3 + row * item_height, width - 6, item_height - 6 + (0 if row < visible - 1 else 0))
			if selected:
				colour = tuple(int(c * 0.78) for c in item_art.TYPE_COLOURS.get(data['element'], (150, 150, 150)))
				pygame.draw.rect(self.display_surface, colour, row_rect, 0, 5)
			icon = item_art.type_icon(data['element'], 20)
			self.display_surface.blit(icon, icon.get_frect(midleft = (row_rect.left + 6, row_rect.centery)))
			text_surf = self.fonts['regular'].render(attack_name(ability), False, COLORS['white'] if selected else '#2b2930')
			self.display_surface.blit(text_surf, text_surf.get_frect(midleft = (row_rect.left + 32, row_rect.centery)))
			# Iteration 24: how well the move works on the opponents (up arrow = super effective, down = weak)
			if targets and not rules.is_status_move(ability) and data['target'] == 'opponent':
				best = max(rules.effectiveness(data['element'], *kinds)[0] for kinds in targets)
				if best != 1:
					colour = (60, 170, 60) if best > 1 else (200, 70, 70)
					if selected:
						colour = (255, 255, 255)
					x, y = row_rect.right - 12, row_rect.centery
					points = [(x - 6, y + 3), (x, y - 5), (x + 6, y + 3)] if best > 1 else [(x - 6, y - 3), (x, y + 5), (x + 6, y - 3)]
					pygame.draw.polygon(self.display_surface, colour, points)
		# scroll arrows
		if first > 0:
			pygame.draw.polygon(self.display_surface, '#3a373b', [(bg_rect.centerx - 6, bg_rect.top - 4), (bg_rect.centerx + 6, bg_rect.top - 4), (bg_rect.centerx, bg_rect.top - 11)])
		if first + visible < len(abilities):
			pygame.draw.polygon(self.display_surface, '#3a373b', [(bg_rect.centerx - 6, bg_rect.bottom + 4), (bg_rect.centerx + 6, bg_rect.bottom + 4), (bg_rect.centerx, bg_rect.bottom + 11)])
		if abilities:
			self.draw_move_info(abilities[min(self.indexes['attacks'], len(abilities) - 1)], bg_rect)

	# Iteration 34: a panel under (or over) the move list saying what the selected move does.
	def draw_move_info(self, attack, menu_rect):
		from localisation import move_effects
		from ui_style import pixel_frame, UI
		data = ATTACK_DATA[attack]
		lines = move_effects(data)
		power = rules.move_power(attack)
		stats = '   '.join(part for part in (
			t('moves_power') + f' {power}' if power else None,
			t('moves_cost') + f" {data['cost']}",
			t('moves_accuracy') + f" {data.get('accuracy', 100)}%") if part)
		font, small = self.fonts['regular'], self.fonts['small']
		chip = item_art.type_chip(data['element'], small, t(f"element_{data['element']}"))
		widest = max([chip.get_width() + 12 + font.size(stats)[0]] + [font.size(line)[0] for line in lines] + [self.fonts['bold'].size(attack_name(attack))[0]])
		width = max(300, widest + 32)
		height = 92 + 28 * len(lines)
		rect = pygame.FRect(0, 0, width, height)
		rect.midbottom = (WINDOW_WIDTH / 2, WINDOW_HEIGHT - 72)   # the empty ground above the key hints
		rect.clamp_ip(pygame.FRect(8, 8, WINDOW_WIDTH - 16, WINDOW_HEIGHT - 16))
		pixel_frame(self.display_surface, rect, 4, fill = (34, 32, 40, 245))
		x, y = rect.left + 16, rect.top + 12
		name = self.fonts['bold'].render(attack_name(attack), False, COLORS['white'])
		self.display_surface.blit(name, (x, y))
		y += name.get_height() + 8
		self.display_surface.blit(chip, (x, y))
		stats_surf = font.render(stats, False, (200, 198, 210))
		self.display_surface.blit(stats_surf, stats_surf.get_frect(midleft = (x + chip.get_width() + 12, y + chip.get_height() / 2)))
		y += chip.get_height() + 10
		for line in lines:
			self.display_surface.blit(font.render(line, False, (150, 225, 140)), (x, y))
			y += 28

	# Draws the list of party monsters that can be switched in (not on the field and not fainted),
	# with their icon, level, health bar and energy bar.
	def draw_switch(self):
		# data
		width, height = 300, 320
		visible_monsters = 4
		item_height = height / visible_monsters
		v_offset = 0 if self.indexes['switch'] < visible_monsters else -(self.indexes['switch'] - visible_monsters + 1) * item_height
		bg_rect = self.place_menu(pygame.FRect((0,0), (width, height)))
		pygame.draw.rect(self.display_surface, COLORS['white'], bg_rect, 0, 5)

		# monsters
		active_monsters = [(monster_sprite.index, monster_sprite.monster) for monster_sprite in self.player_sprites]
		self.available_monsters = {index: monster for index, monster in self.monster_data['player'].items() if (index, monster) not in active_monsters and monster.health > 0}

		for index, monster in enumerate(self.available_monsters.values()):
			selected = index == self.indexes['switch']
			item_bg_rect = pygame.FRect((0,0), (width, item_height)).move_to(midleft = (bg_rect.left, bg_rect.top + item_height / 2 + index * item_height + v_offset))

			icon_surf = self.monster_frames['shiny_icons' if monster.shiny else 'icons'][monster.name]
			icon_rect = icon_surf.get_frect(midleft = bg_rect.topleft + vector(10,item_height / 2 + index * item_height + v_offset))
			text_surf = self.fonts['regular'].render(f'{monster.display_name} ({monster.level})', False, COLORS['red'] if selected else COLORS['black'])
			text_rect = text_surf.get_frect(topleft = (bg_rect.left + 90, icon_rect.top))

			# selection bg
			if selected:
				if item_bg_rect.collidepoint(bg_rect.topleft):
					pygame.draw.rect(self.display_surface, COLORS['dark white'], item_bg_rect, 0, 0, 5, 5)
				elif item_bg_rect.collidepoint(bg_rect.midbottom + vector(0,-1)):
					pygame.draw.rect(self.display_surface, COLORS['dark white'], item_bg_rect, 0, 0, 0, 0, 5, 5)
				else:
					pygame.draw.rect(self.display_surface, COLORS['dark white'], item_bg_rect)

			if bg_rect.collidepoint(item_bg_rect.center):
				for surf, rect in ((icon_surf, icon_rect), (text_surf, text_rect)):
					self.display_surface.blit(surf, rect)
				health_rect = pygame.FRect((text_rect.bottomleft + vector(0,4)), (100,4))
				energy_rect = pygame.FRect((health_rect.bottomleft + vector(0,2)), (80,4))
				draw_bar(self.display_surface, health_rect, monster.health, monster.get_stat('max_health'), COLORS['red'], COLORS['black'])
				draw_bar(self.display_surface, energy_rect, monster.energy, monster.get_stat('max_energy'), COLORS['blue'], COLORS['black'])

	# Iteration 14: speeds up slow battles - see turn_speed_for at the top of this file.
	def set_turn_speed(self):
		sprites = self.player_sprites.sprites() + self.opponent_sprites.sprites()
		speed = turn_speed_for([sprite.monster.get_stat('speed') for sprite in sprites])
		for sprite in sprites:
			sprite.monster.turn_speed = speed

	# Runs one frame of the battle: end check, input, timers, sprites, turn check, then drawing.
	# Parameter: dt (real, seconds since last frame). Called from Game.run while a battle is open.
	def update(self, dt):
		# Iteration 24: the VS intro for gym leaders and the rival plays before the battle starts
		if self.vs_time > 0:
			self.vs_time -= dt
			self.display_surface.blit(self.bg_surf, (0, 0))
			self.draw_vs()
			return
		# Iteration 25: player 2's turn has ended, so the sides go back to normal
		if getattr(self, 'swapped', False) and not (self.current_monster and self.selection_mode):
			self.swap_sides()
		self.check_end_battle()

		# updates
		self.input()
		self.update_timers()
		self.set_turn_speed()
		self.battle_sprites.update(dt)
		self.check_stuck(dt)
		self.check_active()

		# drawing
		self.display_surface.blit(self.bg_surf, (0,0))
		self.draw_clouds(dt)   # Iteration 24
		for sprite in self.player_sprites.sprites() + self.opponent_sprites.sprites():
			sprite.knock = max(0, getattr(sprite, 'knock', 0) - dt * 6)
		self.battle_sprites.draw(self.current_monster, self.selection_side, self.selection_mode, self.indexes['target'], self.player_sprites, self.opponent_sprites)
		self.draw_ui()

		# Iteration 18: screen shake after a super effective hit
		if self.shake_time > 0:
			self.shake_time -= dt
			self.display_surface.scroll(choice((-6, 6)), choice((-4, 4)))
