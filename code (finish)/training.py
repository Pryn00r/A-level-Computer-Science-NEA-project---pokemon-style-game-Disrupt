# training.py
# Iteration 33: training mode. Pick any of the 16 monsters (level 50, knowing every move its species can
# learn) and try its moves on a training Pouch. The Pouch never attacks back, gets straight back up when it
# is knocked out, and your monster never runs out of energy or faints. Nothing here is saved: the monsters
# are new copies made just for training, so your own party, items and experience do not change.
# Iteration 34: Esc leaves at any time, R resets both monsters, the banner is easier to read and the
# setup screen shows the monster's type, stats and moves.

from settings import *
from game_data import MONSTER_DATA, ATTACK_DATA
from localisation import t, attack_name, stat_name
from monster import Monster
from ui_base import Screen, ListScreen, draw_text, draw_key_hints
from ui_style import UI, hud_tag
from timery import Timer
import item_art

TRAINING_LEVEL = 50
DUMMY = 'Pouch'

# A monster for training: level 50, full health and energy, and every move it can learn usable in battle.
def training_monster(name):
	monster = Monster(name, TRAINING_LEVEL)
	monster.all_moves = True   # Monster.equipped_moves gives every known move instead of only 4
	monster.health, monster.energy = monster.get_stat('max_health'), monster.get_stat('max_energy')
	return monster


# Step 1: choose which monster to train with.
class TrainingSetupScreen(ListScreen):
	hint = 'hint_list'

	def get_items(self):
		return [(name, lambda name = name: self.pick(name)) for name in MONSTER_DATA]

	def pick(self, name):
		self.ui.push(TrainingScreen(self.ui, name))

	# a small type icon in front of every monster's name
	def row_picture(self, index, selected):
		name = list(MONSTER_DATA)[index]
		return item_art.type_icon(MONSTER_DATA[name]['stats']['element'], 22)

	def draw(self, surface):
		area = self.draw_panel(surface, t('training_title'))
		split = area.width * 0.4
		self.draw_list(surface, pygame.FRect(area.left, area.top, split, area.height - 36))
		left, width = area.left + split + 32, area.width - split - 32
		y = self.draw_paragraph(surface, t('training_info'), (left, area.top), width, self.theme['muted'])

		# the selected monster: picture, types, stats and how many moves it has
		name = list(MONSTER_DATA)[min(self.index, len(MONSTER_DATA) - 1)]
		monster = training_monster(name)
		frames = self.game.monster_frames['monsters'][name]['idle']
		frame = pygame.transform.scale_by(frames[int(pygame.time.get_ticks() / 150) % len(frames)], 0.8)
		picture = frame.get_frect(topleft = (left, y + 6))
		surface.blit(frame, picture)
		x = picture.right + 16
		draw_text(surface, self.fonts['bold'], name, UI['gold'], topleft = (x, y + 14))
		chip_x = x
		for element in (monster.element, getattr(monster, 'element2', None)):
			if element:
				chip = item_art.type_chip(element, self.fonts['small'], t(f'element_{element}'))
				surface.blit(chip, (chip_x, y + 48))
				chip_x += chip.get_width() + 6
		row_y = y + 82
		for stat in ('max_health', 'attack', 'defense', 'speed'):
			label = stat_name(stat.replace('max_', ''))
			draw_text(surface, self.fonts['small'], f'{label.capitalize()}: {int(monster.get_stat(stat))}', self.theme['text'], topleft = (x, row_y))
			row_y += 22
		draw_text(surface, self.fonts['regular'], t('training_moves', count = len(monster.known_moves())), UI['gold'], topleft = (left, max(picture.bottom, row_y) + 12))


# Step 2: the training battle against the Pouch.
class TrainingScreen(Screen):
	use_backdrop = False

	def __init__(self, ui, name):
		super().__init__(ui)
		from battle import Battle
		game = self.game
		self.previous_music = getattr(game, 'music', None)
		self.trainee = training_monster(name)
		self.battle = Battle({0: self.trainee}, {0: self.new_dummy()}, game.monster_frames, game.bg_frames['forest'], game.fonts,
		                     self.finished, None, game.audio, {}, False, None)
		battle = self.battle
		battle.training = True
		battle.award_xp = lambda defeated: None          # no experience in training
		battle.opponent_attack = self.dummy_turn         # the Pouch never attacks back
		battle.timers['opponent delay'] = Timer(600, func = self.dummy_turn)   # (the timer kept the old one)
		original_check_death = battle.check_death
		def check_death():
			self.keep_going()
			original_check_death()
		battle.check_death = check_death
		self.knockouts = 0
		self.done = False
		self.dt = 1 / 60
		game.set_music('battle_wild')

	def new_dummy(self):
		dummy = Monster(DUMMY, TRAINING_LEVEL)
		dummy.health, dummy.energy = dummy.get_stat('max_health'), dummy.get_stat('max_energy')
		return dummy

	# Called just before the battle checks for knocked-out monsters.
	def keep_going(self):
		battle = self.battle
		# your monster cannot faint in training
		for sprite in battle.player_sprites:
			if sprite.monster.health <= 0:
				sprite.monster.health = sprite.monster.get_stat('max_health')
		# a knocked-out Pouch is replaced by a fresh one (the battle sends out the next monster on the list)
		for sprite in battle.opponent_sprites:
			if sprite.monster.health <= 0 and not sprite.timers['kill'].active:
				self.knockouts += 1
				battle.monster_data['opponent'] = {self.knockouts: self.new_dummy()}
				battle.show_message(t('training_respawn', monster = DUMMY))

	def dummy_turn(self):
		battle = self.battle
		battle.show_message(t('training_dummy_waits', monster = DUMMY))
		battle.current_monster = None
		battle.update_all_monsters('resume')

	# The battle calls this when it ends - in training that only happens when you choose Run.
	def finished(self, character, lost = False):
		self.done = True

	# Iteration 34: Esc leaves training at any time (unless it is closing a battle menu), R resets both monsters
	def handle_key(self, event):
		battle = self.battle
		if event.key == pygame.K_ESCAPE and battle.selection_mode not in ('attacks', 'switch', 'target', 'orbs', 'items'):
			self.done = True
		elif event.key == pygame.K_r:
			self.reset()

	# Puts both monsters back to normal: full health, no status and no raised or lowered stats.
	def reset(self):
		for sprite in list(self.battle.player_sprites) + list(self.battle.opponent_sprites):
			monster = sprite.monster
			if monster.health <= 0:
				continue
			monster.health = monster.get_stat('max_health')
			monster.status, monster.status_turns, monster.stages, monster.charging = None, 0, {}, None
		self.battle.show_message(t('training_reset'))

	def update(self, dt):
		self.dt = min(0.05, dt)
		# your monster never runs out of energy
		self.trainee.energy = self.trainee.get_stat('max_energy')
		if self.done:
			if self.previous_music:
				self.game.set_music(self.previous_music)
			self.ui.pop()

	def draw(self, surface):
		self.battle.update(self.dt)
		# Iteration 34: the banner is on a dark tag so it can be read over the sky
		tag = hud_tag(surface, t('training_banner', count = self.knockouts), self.fonts['bold'], 'sword', color = UI['gold'], midtop = (WINDOW_WIDTH / 2, 10))
		layer = pygame.Surface((WINDOW_WIDTH, 40), pygame.SRCALPHA)
		hints = draw_key_hints(layer, self.fonts['small'], t('training_keys'), COLORS['white'], midtop = (WINDOW_WIDTH / 2, 7))
		backing = hints.inflate(24, 12).move(0, tag.bottom + 1)
		pygame.draw.rect(surface, (34, 32, 40), backing, 0, 8)
		surface.blit(layer, (0, tag.bottom + 1))
