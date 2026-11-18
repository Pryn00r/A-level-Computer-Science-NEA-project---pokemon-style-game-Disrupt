# ending.py
# Iteration 18: what happens after the player beats all three gym leaders.
# The story: the player was playing a monster game, got stuck inside it, and can only leave by
# beating the three gym leaders. The screen fades to black, the player walks around in the dark
# talking to himself, a light appears, he "wakes up", and the credits roll.
# (A proper animated video can replace the middle part later - see play_video_if_present in main.py.)

from math import sin

from settings import *
from localisation import t
from menus import Screen, draw_text
from ui_style import pixel_button, pixel_frame
import controls

# (seconds the line starts, text key) - what the player thinks while walking around in the dark
THOUGHTS = [
	(1.5, 'ending_line_1'), (5.0, 'ending_line_2'), (8.5, 'ending_line_3'),
	(12.0, 'ending_line_4'), (15.5, 'ending_line_5'), (19.0, 'ending_line_6'),
]
LIGHT_TIME = 22.5        # the light appears
WAKE_TIME = 25.5         # white flash - he wakes up
CREDITS_TIME = 28.0      # the credits start
CREDITS_LENGTH = 24.0    # how long the credits take to scroll


class EndingScreen(Screen):
	use_backdrop = False

	def __init__(self, ui):
		super().__init__(ui)
		self.time = 0
		self.frames = self.game.overworld_frames['characters']['player']
		self.x = WINDOW_WIDTH / 2
		self.direction = 1
		self.frame_index = 0
		self.game.set_music('ending')

		self.choosing = False   # Iteration 19: True once the credits end - Continue or Main Menu
		self.choice = 0

	def handle_key(self, event):
		key = controls.menu_key(event.key)
		if self.choosing:
			if key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
				self.choice = 1 - self.choice
			elif key in (pygame.K_RETURN, pygame.K_SPACE):
				self.choose(self.choice)
			return
		# Esc skips to the credits, and skips the credits at the end
		if event.key == pygame.K_ESCAPE:
			if self.time < CREDITS_TIME:
				self.time = CREDITS_TIME
			else:
				self.finish()

	def handle_click(self, pos):
		if self.choosing:
			for index, rect in enumerate(self.button_rects()):
				if rect.collidepoint(pos):
					self.choose(index)

	# Iteration 19: after the credits the player chooses to keep playing or go back to the main menu
	def finish(self):
		self.choosing = True

	def button_rects(self):
		return [pygame.FRect(0, 0, 420, 62).move_to(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 30 + index * 80)) for index in range(2)]

	def choose(self, index):
		self.game.set_music(None)
		self.ui.pop()
		if index == 0:
			self.game.continue_after_ending()
		else:
			self.game.back_to_hub()

	def update(self, dt):
		if self.choosing:
			return
		self.time += dt
		self.frame_index += ANIMATION_SPEED * dt
		# he paces left and right, turning round at the edges of the light
		if self.time < LIGHT_TIME:
			self.x += self.direction * 90 * dt
			if abs(self.x - WINDOW_WIDTH / 2) > 220:
				self.direction *= -1
		elif self.time < WAKE_TIME:
			self.x += (WINDOW_WIDTH / 2 - self.x) * min(1, 2 * dt)   # stops in the middle and looks up
		if self.time > CREDITS_TIME + CREDITS_LENGTH + 2:
			self.finish()

	def draw(self, surface):
		surface.fill('black')
		if self.choosing:
			pixel_frame(surface, pygame.FRect(0, 0, 560, 320).move_to(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)), 6)
			draw_text(surface, self.fonts['bold'], t('ending_question'), COLORS['gold'], center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 70))
			for index, (rect, key) in enumerate(zip(self.button_rects(), ('ending_continue', 'ending_main_menu'))):
				pixel_button(surface, rect, t(key), self.fonts['bold'], index == self.choice)
			return
		if self.time < WAKE_TIME:
			self.draw_dream(surface)
		elif self.time < CREDITS_TIME:
			# white flash fading into the credits
			surface.fill('white')
			surface.fill([int(255 * max(0, 1 - (self.time - WAKE_TIME) / 2.5))] * 3)
			draw_text(surface, self.fonts['dialog'], t('ending_woke'), COLORS['gold'], center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
		else:
			self.draw_credits(surface)

	def draw_dream(self, surface):
		fade = min(1, self.time / 1.5)
		# a soft spotlight that follows him
		light = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
		for radius, alpha in ((260, 18), (190, 26), (130, 34)):
			pygame.draw.circle(light, (255, 255, 230, int(alpha * fade)), (self.x, WINDOW_HEIGHT / 2 + 40), radius)
		surface.blit(light, (0, 0))

		# the light appearing at the top of the screen near the end
		if self.time > LIGHT_TIME:
			glow = min(1, (self.time - LIGHT_TIME) / 2)
			pygame.draw.circle(surface, (255, 255, 200), (WINDOW_WIDTH / 2, 120), int(10 + 40 * glow + sin(self.time * 6) * 3))

		# the player walking (or standing still looking up once the light appears)
		walking = self.time < LIGHT_TIME
		state = ('right' if self.direction > 0 else 'left') if walking else 'up_idle'
		frames = self.frames[state]
		frame = frames[int(self.frame_index) % len(frames)]
		frame = frame.copy()
		frame.set_alpha(int(255 * fade))
		rect = frame.get_frect(center = (self.x, WINDOW_HEIGHT / 2 + 20))
		surface.blit(frame, rect)

		# his thoughts, one at a time, in a bubble above him
		current = [key for start, key in THOUGHTS if start <= self.time < start + 3.3]
		if current and self.time < LIGHT_TIME:
			text = self.fonts['regular'].render(t(current[-1]), False, COLORS['black'])
			bubble = text.get_frect(midbottom = (rect.centerx, rect.top - 6)).inflate(24, 16)
			bubble.clamp_ip(surface.get_frect().inflate(-20, -20))
			pygame.draw.rect(surface, COLORS['white'], bubble, 0, 8)
			surface.blit(text, text.get_frect(center = bubble.center))
		draw_text(surface, self.fonts['pixel'], t('ending_skip'), '#5a5762', bottomright = (WINDOW_WIDTH - 20, WINDOW_HEIGHT - 14))

	def draw_credits(self, surface):
		progress = (self.time - CREDITS_TIME) / CREDITS_LENGTH
		lines = [
			('title', GAME_TITLE.upper()), ('gap', ''),
			('heading', t('credits_made_by')), ('name', 'Prabnoor'), ('gap', ''),
			('heading', t('credits_project')), ('name', t('credits_nea')), ('gap', ''),
			('heading', t('credits_built_with')), ('name', 'Python, pygame-ce, pytmx, Tiled'), ('gap', ''),
			('heading', t('credits_testers')), ('name', t('credits_testers_names')), ('gap', ''),
			# Iteration 26: the free art packs (their licences ask for credit)
			('heading', t('credits_art')), ('name', "Icons: Shikashi's Fantasy Icons Pack"),
			('name', 'Effects: Super Pixel Effects Gigapack - Will Tice / unTied Games'), ('name', 'Effects: FREE 20+ VFX Pack - ThePixelGame'),
			('name', 'Effects: Acid, Dark and Wood VFX, Fire Effect 2 (itch.io)'), ('gap', ''),
			('heading', t('credits_thanks')), ('name', t('credits_you')), ('gap', ''), ('gap', ''),
			('title', t('credits_the_end')),
		]
		y = WINDOW_HEIGHT + 40 - progress * (len(lines) * 46 + WINDOW_HEIGHT * 0.6)
		for kind, text in lines:
			font, color = {'title': ('dialog', COLORS['gold']), 'heading': ('pixel', COLORS['light']), 'name': ('regular', COLORS['white']), 'gap': ('small', COLORS['white'])}[kind]
			if text:
				draw_text(surface, self.fonts[font], text, color, center = (WINDOW_WIDTH / 2, y))
			y += 46
		draw_text(surface, self.fonts['pixel'], t('ending_skip'), '#5a5762', bottomright = (WINDOW_WIDTH - 20, WINDOW_HEIGHT - 14))
