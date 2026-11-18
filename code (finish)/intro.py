# intro.py
# Iteration 17: the intro shown when the game starts.
# 1. A "studio" card: an NEA project, made by Prabnoor.
# 2. The game's name with the three starters.
# 3. A deliberately silly fake loading screen - it races to 35%, slows down, gets stuck at 75%,
#    stalls again and again, then suddenly finishes, while listing made-up files being "installed".
# Space or Enter skips to the next part, Esc skips the whole intro.

from random import choice, uniform
from math import sin

from settings import *
from localisation import t
from menus import Screen, draw_text
from ui_style import spinner

# (seconds into the loading screen, percent shown) - the bar moves in straight lines between these
LOADING_CURVE = [
	(0.0, 0), (0.9, 35), (1.5, 52), (2.3, 63), (3.0, 75),    # fast at first
	(4.4, 75), (4.6, 76), (5.9, 76), (6.1, 77), (7.3, 77),   # stuck at 75... and stuck again
	(7.5, 99), (8.4, 99), (8.5, 100),                         # suddenly almost done, one last stall
]
LOADING_TIME = LOADING_CURVE[-1][0] + 0.6
STUDIO_TIME, LOGO_TIME = 3.0, 2.2

# made-up files for the loading list (the joke is how pointless they are)
FAKE_FILES = [
	'grass_that_rustles_slightly.png', 'sparchu_attitude.dll', 'unnecessary_shaders.pak', 'more_grass.png',
	'monster_feelings.json', 'nurse_smile_v7_final_FINAL.png', 'reticulating_splines.exe', 'ocean_wetness.cfg',
	'beach_sand_coarse_and_rough.dat', 'trainer_excuses.txt', 'gym_floor_shine.mat', 'invisible_walls.col',
	'background_music_but_louder.ogg', 'plumette_leaf_physics.bin', 'finsta_splash_damage.bin', 'cloud_shapes.zip',
	'fake_progress_bar.py', 'homework_folder_do_not_open.zip', 'snowflakes_each_unique.png', 'larvea_wiggle.anim',
	'boss_battle_tension.mp3', 'coin_jingle_extra_shiny.wav', 'tree_collision_v2.col', 'jacana_speed_lines.png',
	'definitely_not_a_virus.exe', 'wifi_password.txt', 'loading_screen_jokes.txt', 'shiny_sparkle_dust.png',
]
# messages shown under the bar while it is stuck
STALL_MESSAGES = [
	'Almost there...', 'Seriously, almost there.', 'Asking Sparchu nicely to cooperate...', 'Still loading. Probably.',
	'Have you tried turning it off and on again?', 'Counting every blade of grass...', 'The hamster powering this needs a break.',
]


# Draws the three intro parts in order. It sits on top of the title screen and closes itself at the end.
class IntroScreen(Screen):
	use_backdrop = False

	# Iteration 18: short = True skips the studio card and the loading screen (Settings > Intro)
	def __init__(self, ui, short = False):
		super().__init__(ui)
		self.short = short
		self.phase = 'logo' if short else 'studio'     # 'studio' -> 'logo' -> 'loading'
		self.time = 0             # seconds spent in the current part
		self.files = []           # (file name, size in MB) lines shown in the loading list
		self.file_timer = 0
		self.monster = choice(list(self.game.monster_frames['monsters']))
		self.monster_timer = 0
		self.stall_message = choice(STALL_MESSAGES)
		self.frame_index = 0
		self.last_percent = 0

	def handle_key(self, event):
		if event.key == pygame.K_ESCAPE:
			self.finish()
		elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
			self.next_phase()

	def handle_click(self, pos):
		self.next_phase()

	def next_phase(self):
		self.time = 0
		if self.phase == 'studio':
			self.phase = 'logo'
		elif self.phase == 'logo' and not self.short:
			self.phase = 'loading'
		else:
			self.finish()

	# Closes the intro, showing the title screen underneath.
	def finish(self):
		if self in self.ui.screens:
			self.ui.screens.remove(self)

	# Returns the percentage for the current time by following LOADING_CURVE (linear interpolation).
	@staticmethod
	def percent_at(time):
		for (start, low), (end, high) in zip(LOADING_CURVE, LOADING_CURVE[1:]):
			if start <= time <= end:
				return low + (high - low) * (time - start) / (end - start)
		return 100

	def update(self, dt):
		self.time += dt
		self.frame_index += ANIMATION_SPEED * dt
		limit = {'studio': STUDIO_TIME, 'logo': LOGO_TIME, 'loading': LOADING_TIME}[self.phase]
		if self.time >= limit:
			self.next_phase()
			return
		if self.phase == 'loading':
			percent = self.percent_at(self.time)
			moving = percent > self.last_percent + 0.01
			self.last_percent = percent
			# new file lines appear quickly while the bar moves, and almost never while it is stuck
			self.file_timer -= dt
			if self.file_timer <= 0:
				self.files.append((choice(FAKE_FILES), uniform(0.1, 480)))
				self.files = self.files[-9:]
				self.file_timer = uniform(0.04, 0.12) if moving else uniform(0.8, 1.6)
			if not moving and uniform(0, 1) < dt * 0.6:
				self.stall_message = choice(STALL_MESSAGES)
			self.monster_timer += dt
			if self.monster_timer > 1.6:
				self.monster_timer = 0
				self.monster = choice(list(self.game.monster_frames['monsters']))

	# Returns 0-255: fades in at the start of a part and out at the end.
	def fade(self, length):
		return int(255 * max(0, min(1, self.time / 0.6, (length - self.time) / 0.6)))

	def draw(self, surface):
		surface.fill('#0d0c10')
		match self.phase:
			case 'studio': self.draw_studio(surface)
			case 'logo': self.draw_logo(surface)
			case 'loading': self.draw_loading(surface)
		draw_text(surface, self.fonts['pixel'], t('intro_skip'), '#5a5762', bottomright = (WINDOW_WIDTH - 20, WINDOW_HEIGHT - 14))

	def draw_studio(self, surface):
		layer = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
		draw_text(layer, self.fonts['regular'], t('intro_presents'), COLORS['light'], center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 50))
		draw_text(layer, self.fonts['dialog'], 'PRABNOOR', COLORS['gold'], center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
		draw_text(layer, self.fonts['small'], t('intro_made_by'), COLORS['light'], center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 44))
		layer.set_alpha(self.fade(STUDIO_TIME))
		surface.blit(layer, (0, 0))

	def draw_logo(self, surface):
		layer = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
		# the title bounces in with a shadow
		scale = min(1, self.time / 0.4)
		title = self.fonts['dialog'].render(GAME_TITLE.upper(), False, COLORS['gold'])
		title = pygame.transform.scale_by(title, 2.4 * max(0.2, scale))
		shadow = self.fonts['dialog'].render(GAME_TITLE.upper(), False, '#7a5c00')
		shadow = pygame.transform.scale_by(shadow, 2.4 * max(0.2, scale))
		centre = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 90)
		layer.blit(shadow, shadow.get_frect(center = (centre[0] + 6, centre[1] + 6)))
		layer.blit(title, title.get_frect(center = centre))
		# the three starters underneath
		for number, name in enumerate(('Plumette', 'Sparchu', 'Finsta')):
			frames = self.game.monster_frames['monsters'][name]['idle']
			frame = frames[int(self.frame_index + number) % len(frames)]
			x = WINDOW_WIDTH / 2 + (number - 1) * 220
			y = WINDOW_HEIGHT / 2 + 110 + sin(self.time * 4 + number) * 8
			layer.blit(frame, frame.get_frect(center = (x, y)))
		layer.set_alpha(self.fade(LOGO_TIME))
		surface.blit(layer, (0, 0))

	def draw_loading(self, surface):
		percent = self.percent_at(self.time)
		title = draw_text(surface, self.fonts['bold'], t('intro_loading'), COLORS['white'], topleft = (80, 70))
		wheel = spinner(self.time, 40) if percent < 100 else None   # Iteration 32: the loading wheel
		if wheel and title:
			surface.blit(wheel, wheel.get_frect(midleft = (title.right + 16, title.centery)))

		# progress bar
		bar = pygame.FRect(80, 130, WINDOW_WIDTH - 160, 30)
		pygame.draw.rect(surface, '#24222b', bar, 0, 6)
		filled = bar.copy()
		filled.width = bar.width * percent / 100
		pygame.draw.rect(surface, COLORS['gold'], filled, 0, 6)
		pygame.draw.rect(surface, COLORS['light'], bar, 2, 6)
		draw_text(surface, self.fonts['bold'], f'{int(percent)}%', COLORS['white'], bottomright = bar.topright + vector(0, -10))

		stuck = 0 < self.time and self.percent_at(self.time) == self.percent_at(self.time - 0.15) and percent < 100
		message = self.stall_message if stuck else t('intro_loading_files')
		draw_text(surface, self.fonts['regular'], message, COLORS['light'], topleft = bar.bottomleft + vector(0, 14))

		# the list of made-up files, newest at the bottom
		for row, (name, size) in enumerate(self.files):
			y = 230 + row * 30
			color = COLORS['white'] if row == len(self.files) - 1 else '#7d7a86'
			draw_text(surface, self.fonts['pixel'], f'> {name}', color, topleft = (80, y))
			draw_text(surface, self.fonts['pixel'], f'{size:6.1f} MB', color, topright = (620, y))

		# a random monster bouncing on the right, with a random tip
		frames = self.game.monster_frames['monsters'][self.monster]['idle']
		frame = frames[int(self.frame_index) % len(frames)]
		surface.blit(frame, frame.get_frect(center = (930, 360 + sin(self.time * 5) * 10)))
		draw_text(surface, self.fonts['regular'], self.monster, COLORS['gold'], midtop = (930, 470))
		tip = t(f'intro_tip_{int(self.time / 2.2) % 5}')
		draw_text(surface, self.fonts['small'], tip, COLORS['light'], midbottom = (WINDOW_WIDTH / 2, WINDOW_HEIGHT - 50))
