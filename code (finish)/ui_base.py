# ui_base.py
# Iteration 18 (split from menus.py): the building blocks every menu uses - text helpers, the
# colour themes, the screen stack and the base Screen / ListScreen / ChoiceScreen / PixelMenuScreen classes.

import unicodedata
from math import sin

from settings import *
from game_data import HELD_ITEM_DATA
from localisation import t
from ui_style import UI, pixel_frame, pixel_button, icon_button, draw_logo
import controls
import item_art


THEMES = {
	'day':   {'panel': COLORS['dark'], 'row': COLORS['gray'], 'text': COLORS['white'], 'muted': COLORS['light'],
	          'selected': COLORS['light'], 'selected_text': COLORS['black'], 'accent': COLORS['gold']},
	'night': {'panel': '#121116', 'row': '#1e1c24', 'text': COLORS['light'], 'muted': '#8d8a96',
	          'selected': '#4b484d', 'selected_text': COLORS['white'], 'accent': COLORS['fire']},
}


# text helpers
# Returns the text unchanged if the font can draw every character, otherwise removes accents (é -> e).
def fit_to_font(font, text):
	# pixel fonts often lack accents, so é becomes e rather than an empty box
	if all(metric is not None for metric in font.metrics(text)):
		return text
	return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

# Draws text anchored at a position (e.g. topleft = ...) and returns its rectangle.
def draw_text(surface, font, text, color, **anchor):
	text_surf = font.render(fit_to_font(font, str(text)), False, color)
	text_rect = text_surf.get_frect(**anchor)
	surface.blit(text_surf, text_rect)
	return text_rect

# Splits a paragraph into lines that fit within width pixels. Returns a list of lines.
def wrap_text(font, text, width):
	lines, current = [], ''
	for word in text.split():
		candidate = f'{current} {word}'.strip()
		if font.size(fit_to_font(font, candidate))[0] <= width:
			current = candidate
		else:
			lines.append(current)
			current = word
	return lines + [current] if current else lines

# Iteration 18: the picture behind menus when no game is being played - the forest battle background,
# darkened more towards the bottom so the menu on top is easy to read.
_backdrop = {}
def draw_backdrop(surface, game):
	if 'image' not in _backdrop:
		if not hasattr(game, 'bg_frames'):     # (e.g. in the tests, where no images are loaded)
			surface.fill(COLORS['dark'])
			return
		image = game.bg_frames['forest'].copy()
		shade = pygame.Surface(image.get_size(), pygame.SRCALPHA)
		for y in range(0, image.get_height(), 4):
			pygame.draw.rect(shade, (10, 8, 20, int(40 + 120 * y / image.get_height())), (0, y, image.get_width(), 4))
		image.blit(shade, (0, 0))
		_backdrop['image'] = image
	surface.blit(_backdrop['image'], (0, 0))

# Iteration 24: the title and account screens come alive - monsters walk along the bottom and
# leaves drift down. Uses the clock, so it needs no update calls.
PARADE = ('Sparchu', 'Finsta', 'Plumette', 'Cleaf', 'Jacana', 'Draem', 'Pouch', 'Friolera', 'Atrox', 'Larvea', 'Ivieron', 'Gulfin')
def animated_backdrop(surface, game):
	draw_backdrop(surface, game)
	frames = getattr(game, 'monster_frames', None)
	if not frames:
		return
	now = pygame.time.get_ticks() / 1000
	# leaves
	for i in range(14):
		x = (i * 97 + now * (20 + i % 4 * 8)) % (WINDOW_WIDTH + 40) - 20
		y = (i * 53 + now * (30 + i % 3 * 10)) % (WINDOW_HEIGHT + 40) - 20
		wobble = sin(now * 2 + i) * 8
		colour = ((140, 190, 90), (200, 160, 70), (110, 160, 80))[i % 3]
		pygame.draw.ellipse(surface, colour, (x + wobble, y, 9, 5))
	# the parade: each monster walks from left to right, one after another, then they loop
	spacing, speed = 190, 70
	loop = (len(PARADE) * spacing + WINDOW_WIDTH)
	for i, name in enumerate(PARADE):
		monster = frames['monsters'].get(name)
		if not monster:
			continue
		x = (now * speed - i * spacing) % loop - 100
		if x > WINDOW_WIDTH + 100:
			continue
		idle = monster['idle']
		frame = pygame.transform.flip(idle[int(now * 6 + i) % len(idle)], True, False)
		frame = pygame.transform.scale_by(frame, 0.55)
		hop = abs(sin(now * 5 + i)) * 6
		shadow = pygame.Surface((70, 14), pygame.SRCALPHA)
		pygame.draw.ellipse(shadow, (0, 0, 0, 70), shadow.get_rect())
		surface.blit(shadow, shadow.get_frect(center = (x, WINDOW_HEIGHT - 52)))
		surface.blit(frame, frame.get_frect(midbottom = (x, WINDOW_HEIGHT - 50 - hop)))

# Iteration 13: held items use 'held_' text keys and normal items use 'item_' keys.
def item_name(name):
	return t(f'held_{name}') if name in HELD_ITEM_DATA else t(f'item_{name}')

def item_description(name):
	return t(f'held_{name}_desc') if name in HELD_ITEM_DATA else t(f'item_{name}_desc')

# Iteration 19: the picture for an item (potion = red bottle, ether = blue bottle, Illuminator = the
# star sparkle), or None if it has no picture. Parameters: game (for the loaded images), item name.
ITEM_ICONS = {'potion': 'potion', 'ether': 'ether', 'illuminator': 'star'}
def item_icon(game, name):
	# Iteration 20: pictures drawn in code (item_art.py); Iteration 26: from the icon pack
	if name in ITEM_PICTURES:
		return item_art.item(name)
	return None
ITEM_PICTURES = ('potion', 'ether', 'capture_orb', 'great_orb', 'prime_orb', 'power_band', 'vital_charm', 'focus_ring', 'wise_feather', 'illuminator',
	'burn_heal', 'thaw_spray', 'antidote', 'wake_bell', 'full_cure', 'party_heal', 'max_ether', 'repel', 'escape_rope', 'swift_cap',
	'fishing_rod', 'shovel', 'snow_boots', 'swift_scarf', 'guard_shell', 'lucky_coin', 'shiny_charm', 'pearl', 'fossil', 'crystal', 'scrap', 'herb', 'egg')   # Iteration 25


# Iteration 20: control hints drawn as key caps - "Space: Talk    Esc: Back" becomes [Space] Talk  [Esc] Back.
# Works for every language because the hint texts all use "keys: action" separated by wide gaps.
# Iteration 32: with a controller, the keys in the hints are shown as the controller's buttons
PAD_HINTS = {'space': 'a', 'spazio': 'a', 'espacio': 'a', 'esc': 'b', 'm': 'x', 'enter': 'y', 'invio': 'y', 'intro': 'y'}
_pad_pictures = {}
def hint_cap(key, font):
	import controls
	button = PAD_HINTS.get(key.lower()) if controls.using_pad else None
	if button:
		if button not in _pad_pictures:
			from os.path import exists
			path = asset('graphics', 'ui_pack', f'pad_{button}.png')
			_pad_pictures[button] = pygame.transform.scale(pygame.image.load(path).convert_alpha(), (26, 26)) if exists(path) else None
		if _pad_pictures[button]:
			return _pad_pictures[button]
	return item_art.key_cap(key, font)

def draw_key_hints(surface, font, text, color, **anchor):
	import re
	parts = []
	for segment in [s.strip() for s in re.split(r'\s{2,}', text) if s.strip()]:
		if ': ' in segment:
			keys, label = segment.split(': ', 1)
			parts.append(([hint_cap(key.strip(), font) for key in keys.split('/')], font.render(label, False, color)))
		else:
			parts.append(([], font.render(segment, False, color)))
	width = sum(sum(cap.get_width() + 3 for cap in caps) + label.get_width() + 22 for caps, label in parts) - 22
	strip = pygame.Surface((max(1, width), 26), pygame.SRCALPHA)
	x = 0
	for caps, label in parts:
		for cap in caps:
			strip.blit(cap, (x, 0))
			x += cap.get_width() + 3
		strip.blit(label, (x + 3, 13 - label.get_height() / 2))
		x += label.get_width() + 22
	rect = strip.get_frect(**anchor)
	surface.blit(strip, rect)
	return rect

# Iteration 20: a menu icon (from ui_style patterns) coloured for a selected or normal row.
def row_icon(name, selected):
	from ui_style import icon
	return icon(name, 2, UI['selected_text'] if selected else (20, 18, 24), UI['gold'])

def small_item_icon(game, name, size = 24):
	picture = item_icon(game, name)
	return pygame.transform.scale(picture, (size, size)) if picture else None


# screen management
# Holds the open menu screens as a stack (list). Only the top screen receives key presses.
class ScreenStack:
	def __init__(self, game):
		self.game = game
		self.screens = []
		self.backdrop = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
		self.backdrop.set_alpha(200)

	# True if any menu is open (the game world is paused while this is True).
	@property
	def active(self):
		return bool(self.screens)

	# Iteration 18: a small blip for moving, confirming and going back in menus.
	def click_sound(self, event):
		play = getattr(self.game, 'play', lambda name: None)
		key = controls.menu_key(event.key)
		if key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
			play('menu_move')
		elif key in (pygame.K_RETURN, pygame.K_SPACE):
			play('menu_select')
		elif key == pygame.K_ESCAPE:
			play('menu_back')

	# Opens a screen on top of the current one. A new screen does not get typed text until the next
	# frame, so the key that opened it (e.g. R for rename) is not also typed into it.
	def push(self, screen):
		screen.accept_text = False
		self.screens.append(screen)

	# Closes the top screen. If none are left, tells the Game the menu has closed.
	def pop(self):
		self.screens.pop()
		if self.screens:
			self.screens[-1].on_resume()
		else:
			self.game.menu_closed()

	# Swaps the top screen for another (e.g. username screen -> slot screen).
	def replace(self, screen):
		screen.accept_text = False
		self.screens[-1] = screen

	# Closes every screen.
	def clear(self):
		self.screens.clear()

	# Sends key presses to the top screen, then draws it (and the screens under it if it is an overlay).
	def update(self, dt, events):
		for event in events:
			if event.type == pygame.KEYDOWN and self.screens:
				self.click_sound(event)
				self.screens[-1].handle_key(event)
			# Iteration 15: typed characters come from TEXTINPUT events. Reading event.unicode from
			# KEYDOWN could miss characters when typing quickly, so a password could be saved or
			# checked with a letter missing.
			elif event.type == pygame.TEXTINPUT and self.screens and self.screens[-1].accept_text:
				self.screens[-1].handle_text(event.text)
			# Iteration 16: mouse clicks and taps on a touch screen (not on the on-screen buttons)
			elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.screens and not self.game.touch.covers(event.pos):
				self.screens[-1].handle_click(event.pos)
		if not self.screens:
			return
		self.screens[-1].accept_text = True

		self.screens[-1].update(dt)
		if not self.screens:
			return   # Iteration 18: the screen closed itself during update (e.g. the end of the credits)

		# an overlay is drawn on top of the screens that opened it
		first_visible = len(self.screens) - 1
		while first_visible > 0 and self.screens[first_visible].overlay:
			first_visible -= 1

		surface = self.game.display_surface
		if self.screens[first_visible].use_backdrop:
			surface.blit(self.backdrop, (0, 0))
		for screen in self.screens[first_visible:]:
			screen.draw(surface)


# Base class for every menu screen. Child classes override handle_key, update and draw.
class Screen:
	overlay = False
	use_backdrop = True
	hint = 'hint_list'

	def __init__(self, ui):
		self.ui = ui
		self.game = ui.game
		self.fonts = ui.game.fonts

	# Returns the night or day colours depending on the night mode setting.
	@property
	def theme(self):
		return THEMES['night' if self.game.preferences['night_mode'] else 'day']

	def handle_key(self, event):
		pass

	# Called with typed text (one or more characters). Only screens with text boxes use it.
	def handle_text(self, text):
		pass

	# Called when the screen is clicked or tapped. Parameter: pos (x, y).
	def handle_click(self, pos):
		pass

	accept_text = True

	def on_resume(self):
		pass

	def update(self, dt):
		pass

	def draw(self, surface):
		pass

	def back(self):
		self.ui.pop()

	# Draws the shared panel with a title and the control hint. Returns the area for the screen's content.
	# Iteration 18: drawn as a pixel-art frame (ui_style.py) instead of a plain grey rounded box.
	def draw_panel(self, surface, title):
		# returns the area that the screen can draw its content in
		panel = pygame.FRect(0, 0, WINDOW_WIDTH * 0.8, WINDOW_HEIGHT * 0.86).move_to(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
		pixel_frame(surface, panel, 6)
		title_rect = draw_text(surface, self.fonts['bold'], title, self.theme['accent'], topleft = panel.topleft + vector(36, 30))
		line_y = title_rect.bottom + 16
		for x in range(int(panel.left + 36), int(panel.right - 36), 12):   # dotted pixel line under the title
			pygame.draw.rect(surface, UI['row_edge'], (x, line_y, 6, 3))
		draw_key_hints(surface, self.fonts['small'], t(self.hint), self.theme['muted'], midbottom = panel.midbottom + vector(0, -12))
		return pygame.FRect(panel.left + 32, line_y + 20, panel.width - 64, panel.bottom - line_y - 72)

	# Draws one list row, highlighted if selected.
	# Iteration 18: rows have a light top edge and dark bottom edge (a pixel bevel), and the selected
	# row is light with a small arrow that bobs.
	def draw_row(self, surface, rect, text, selected, picture = None):
		color = UI['selected'] if selected else UI['row']
		text_color = UI['selected_text'] if selected else UI['text']
		pygame.draw.rect(surface, color, rect.inflate(-6, 0))
		pygame.draw.rect(surface, color, rect.inflate(0, -6))
		pygame.draw.line(surface, (255, 255, 255) if selected else UI['row_edge'], rect.topleft + vector(3, 0), rect.topright + vector(-4, 0), 2)
		pygame.draw.line(surface, (24, 22, 28), rect.bottomleft + vector(3, -1), rect.bottomright + vector(-4, -1), 2)
		offset = 16
		if selected:
			offset = 36
			bob = (pygame.time.get_ticks() // 180) % 2 * 3
			pygame.draw.polygon(surface, UI['selected_text'], [(rect.left + 12 + bob, rect.centery - 6), (rect.left + 20 + bob, rect.centery), (rect.left + 12 + bob, rect.centery + 6)])
		if picture:   # Iteration 20: a small icon before the words
			surface.blit(picture, picture.get_frect(midleft = rect.midleft + vector(offset, 0)))
			offset += picture.get_width() + 10
		draw_text(surface, self.fonts['regular'], text, text_color, midleft = rect.midleft + vector(offset, 0))

	# Draws wrapped text and returns the y position below it.
	def draw_paragraph(self, surface, text, pos, width, color, font = 'regular'):
		y = pos[1]
		for line in wrap_text(self.fonts[font], text, width):
			y = draw_text(surface, self.fonts[font], line, color, topleft = (pos[0], y)).bottom + 4
		return y


# A screen with a scrolling list of (label, function) items. Up/Down move, Enter runs the function.
class ListScreen(Screen):
	row_height = 44
	row_gap = 8

	def __init__(self, ui):
		super().__init__(ui)
		self.index = 0
		self.scroll = 0
		self.message = ''

	# returns a list of (label, function) pairs - overridden by each list screen
	def get_items(self):
		# returns a list of (label, function) pairs
		return []

	def handle_key(self, event):
		items = self.get_items()
		key = controls.menu_key(event.key)   # W/S work like Up/Down
		if event.key == pygame.K_ESCAPE:
			self.back()
		elif not items:
			return
		elif key == pygame.K_UP:
			self.index = (self.index - 1) % len(items)
			self.message = ''
		elif key == pygame.K_DOWN:
			self.index = (self.index + 1) % len(items)
			self.message = ''
		elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
			items[self.index][1]()

	# Iteration 16: tapping or clicking a row selects it and opens it.
	def handle_click(self, pos):
		items = self.get_items()
		for rect, index in getattr(self, 'row_rects', []):
			if rect.collidepoint(pos) and index < len(items):
				self.index = index
				items[index][1]()
				return

	# Draws only the rows that fit in the area, scrolling so the selected row is always visible.
	# Iteration 20: the icon shown on a row (None = no icon). Screens with icons override this.
	def row_picture(self, index, selected):
		return None

	def draw_list(self, surface, area):
		items = self.get_items()
		self.index = min(self.index, max(0, len(items) - 1))
		step = self.row_height + self.row_gap
		visible = max(1, int((area.height + self.row_gap) // step))

		if self.index < self.scroll:
			self.scroll = self.index
		elif self.index >= self.scroll + visible:
			self.scroll = self.index - visible + 1

		self.row_rects = []   # kept so a click/tap can be matched to a row
		for row, (label, _) in enumerate(items[self.scroll:self.scroll + visible]):
			rect = pygame.FRect(area.left, area.top + row * step, area.width, self.row_height)
			self.draw_row(surface, rect, label, row + self.scroll == self.index, self.row_picture(row + self.scroll, row + self.scroll == self.index))
			self.row_rects.append((rect, row + self.scroll))


# A small pop-up with a question and choices, e.g. "Delete slot 1? No / Yes".
class ChoiceScreen(ListScreen):
	overlay = True

	def __init__(self, ui, title, choices):
		super().__init__(ui)
		self.title = title
		self.choices = choices

	def get_items(self):
		return self.choices

	def draw(self, surface):
		lines = wrap_text(self.fonts['regular'], self.title, 520)
		rows = min(len(self.choices), 7)
		height = 72 + len(lines) * 28 + rows * (self.row_height + self.row_gap)
		rect = pygame.FRect(0, 0, 600, height).move_to(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
		pygame.draw.rect(surface, self.theme['panel'], rect, 0, 12)
		pygame.draw.rect(surface, self.theme['accent'], rect, 2, 12)

		for index, line in enumerate(lines):
			draw_text(surface, self.fonts['regular'], line, self.theme['text'], topleft = rect.topleft + vector(40, 24 + index * 28))

		top = rect.top + 44 + len(lines) * 28
		self.draw_list(surface, pygame.FRect(rect.left + 40, top, rect.width - 80, rect.bottom - top - 12))


# start up screens (Iteration 14: accounts with passwords replace the old username-only list)

# Iteration 18: base class for the big picture menus (title screen and the menu after signing in).
# Each screen lists widgets: dicts with a 'rect', an 'action' and how to draw it ('button', 'icon' or
# 'side'). Arrow keys / WASD move through them in order, Enter or a tap/click uses one.
class PixelMenuScreen(Screen):
	use_backdrop = False

	def __init__(self, ui):
		super().__init__(ui)
		self.focus = 0
		self.message = ''

	def widgets(self):
		return []

	def handle_key(self, event):
		widgets = self.widgets()
		key = controls.menu_key(event.key)
		if event.key == pygame.K_ESCAPE:
			self.back()
		elif key in (pygame.K_DOWN, pygame.K_RIGHT, pygame.K_TAB):
			self.focus = (self.focus + 1) % len(widgets)
		elif key in (pygame.K_UP, pygame.K_LEFT):
			self.focus = (self.focus - 1) % len(widgets)
		elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
			widgets[self.focus]['action']()

	def handle_click(self, pos):
		for index, widget in enumerate(self.widgets()):
			if widget['rect'].collidepoint(pos):
				self.focus = index
				widget['action']()
				return

	# the three quick buttons in the top right: brightness, night mode and sound
	def quick_widgets(self):
		preferences = self.game.preferences
		def brightness():
			# cycles 100% -> 120% -> 80% -> 100%
			values = (100, 120, 80)
			current = preferences['brightness']
			preferences.set('brightness', values[(values.index(current) + 1) % 3] if current in values else 100)
		def night():
			preferences.toggle('night_mode')
		def sound():
			preferences.toggle('muted')
			preferences.apply_audio(self.game.audio)
		return [
			{'kind': 'icon', 'icon': 'sun', 'rect': pygame.FRect(0, 0, 60, 60).move_to(center = (1010, 58)), 'action': brightness, 'active': preferences['brightness'] != 100, 'tip': t('quick_brightness', value = preferences['brightness'])},
			{'kind': 'icon', 'icon': 'moon', 'rect': pygame.FRect(0, 0, 60, 60).move_to(center = (1084, 58)), 'action': night, 'active': preferences['night_mode'], 'tip': t('setting_night_mode')},
			{'kind': 'icon', 'icon': 'mute' if preferences['muted'] else 'sound', 'rect': pygame.FRect(0, 0, 60, 60).move_to(center = (1158, 58)), 'action': sound, 'active': not preferences['muted'], 'tip': t('quick_sound')},
			{'kind': 'icon', 'icon': 'power', 'rect': pygame.FRect(0, 0, 60, 60).move_to(center = (1232, 58)), 'action': self.game.quit_game, 'active': True, 'tip': t('quit_game')}]

	def draw_widgets(self, surface):
		for index, widget in enumerate(self.widgets()):
			selected = index == self.focus
			rect = widget['rect']
			if widget['kind'] == 'button':
				pixel_button(surface, rect, widget['label'], self.fonts['bold'], selected, widget.get('enabled', True))
			elif widget['kind'] == 'icon':
				icon_button(surface, rect.center, widget['icon'], selected, rect.width, widget.get('active', True))
				if selected and widget.get('tip'):
					draw_text(surface, self.fonts['small'], widget['tip'], UI['text'], midtop = rect.midbottom + vector(0, 8))
			elif widget['kind'] == 'side':
				# icon with its label to one side (right column and bottom left)
				box = pygame.FRect(0, 0, rect.height, rect.height).move_to(**{('midright' if widget['side'] == 'right' else 'midleft'): (rect.right if widget['side'] == 'right' else rect.left, rect.centery)})
				icon_button(surface, box.center, widget['icon'], selected, box.width)
				anchor = {'midright': box.midleft + vector(-12, 0)} if widget['side'] == 'right' else {'midleft': box.midright + vector(12, 0)}
				label = self.fonts['bold'].render(widget['label'], False, UI['gold'] if selected else UI['text'])
				shadow = self.fonts['bold'].render(widget['label'], False, (20, 20, 24))
				label_rect = label.get_frect(**anchor)
				surface.blit(shadow, label_rect.move(2, 2))
				surface.blit(label, label_rect)

	def draw(self, surface):
		animated_backdrop(surface, self.game)   # Iteration 24
		draw_logo(surface, self.fonts['bold'], (WINDOW_WIDTH / 2, 120 + sin(pygame.time.get_ticks() / 600) * 4))
		self.draw_extra(surface)
		self.draw_widgets(surface)
		if self.message:
			draw_text(surface, self.fonts['regular'], self.message, UI['gold'], center = (WINDOW_WIDTH / 2, 588))
		draw_key_hints(surface, self.fonts['small'], t('hint_pixel_menu'), UI['muted'], midbottom = (WINDOW_WIDTH / 2, WINDOW_HEIGHT - 10))

	def draw_extra(self, surface):
		pass

