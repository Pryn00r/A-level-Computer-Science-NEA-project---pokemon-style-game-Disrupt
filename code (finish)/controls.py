# controls.py
# Iteration 16: one place that reads the controls, so every part of the game supports the same keys.
# - WASD works the same as the arrow keys.
# - On a touch screen, on-screen buttons (a D-pad plus A, B, Party and Map) appear after the first touch.
# The rest of the game calls get_pressed() / get_just_pressed() from here instead of from pygame.

from settings import *

# each game key and the keys that also count as it
ALIASES = {
	pygame.K_UP: (pygame.K_UP, pygame.K_w),
	pygame.K_DOWN: (pygame.K_DOWN, pygame.K_s),
	pygame.K_LEFT: (pygame.K_LEFT, pygame.K_a),
	pygame.K_RIGHT: (pygame.K_RIGHT, pygame.K_d),
	pygame.K_LSHIFT: (pygame.K_LSHIFT, pygame.K_RSHIFT),   # Iteration 18: either Shift key sprints
}

virtual_held = set()      # keys held down by an on-screen touch button
virtual_pressed = set()   # keys tapped on an on-screen touch button this frame


# Behaves like the list pygame returns from get_pressed: keys[pygame.K_UP] etc.,
# but also counts the WASD aliases and touch buttons.
class KeyState:
	def __init__(self, real, virtual):
		self.real = real
		self.virtual = virtual

	def __getitem__(self, key):
		if key in self.virtual:
			return True
		return any(self.real[alias] for alias in ALIASES.get(key, (key,)))


# Keys held down right now (used for walking).
def get_pressed():
	return KeyState(pygame.key.get_pressed(), virtual_held)

# Keys pressed this frame (used for menus in battles, dialogue and the monster index).
def get_just_pressed():
	return KeyState(pygame.key.get_just_pressed(), virtual_pressed | virtual_just_held())

# A touch on a direction counts as a single press when it starts.
_held_last_frame = set()
def virtual_just_held():
	return virtual_held - _held_last_frame

# Called once at the end of every frame.
def end_frame():
	global _held_last_frame
	_held_last_frame = set(virtual_held)
	virtual_pressed.clear()

# Turns a menu key event's key into the arrow key it stands for (W -> Up etc.), so the
# list menus also work with WASD. Text boxes do not use this, so W can still be typed.
def menu_key(key):
	for arrow, aliases in ALIASES.items():
		if key in aliases:
			return arrow
	return key


# Iteration 25: game controllers (Xbox / PlayStation / Switch style). The left stick or D-pad walks,
# A = Space (talk, confirm), B = Escape (back), X = Map, Y or Start = the menu (Enter), and the
# right bumper or trigger sprints. Buttons are turned into key presses, so every screen works with them.
PAD_BUTTONS = {0: pygame.K_SPACE, 1: pygame.K_ESCAPE, 2: pygame.K_m, 3: pygame.K_RETURN, 7: pygame.K_RETURN, 6: pygame.K_ESCAPE}
PAD_SPRINT = (5, 10)        # right bumper (different numbers on different controllers)
DEAD_ZONE = 0.45
using_pad = False   # Iteration 32: True while a controller is being used, so key hints show the A/B/X/Y buttons

class Gamepad:
	def __init__(self):
		self.pads = {}
		self.held = set()       # directions held on the stick or D-pad
		self.sprint = False
		for index in range(pygame.joystick.get_count()):
			self.add(index)

	def add(self, index):
		try:
			pad = pygame.joystick.Joystick(index)
			self.pads[pad.get_instance_id()] = pad
		except pygame.error:
			pass

	def press(self, key):
		virtual_pressed.add(key)
		pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key = key, unicode = '', mod = 0, scancode = 0, pad = True))

	def handle(self, events):
		global using_pad
		for event in events:
			if event.type == pygame.KEYDOWN and not getattr(event, 'pad', False):
				using_pad = False   # the keyboard is being used again
			elif event.type in (pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION):
				using_pad = True
			if event.type == pygame.JOYDEVICEADDED:
				self.add(event.device_index)
			elif event.type == pygame.JOYDEVICEREMOVED:
				self.pads.pop(event.instance_id, None)
			elif event.type == pygame.JOYBUTTONDOWN:
				if event.button in PAD_SPRINT:
					self.sprint = True
				elif event.button in PAD_BUTTONS:
					self.press(PAD_BUTTONS[event.button])
			elif event.type == pygame.JOYBUTTONUP and event.button in PAD_SPRINT:
				self.sprint = False
		# directions: the D-pad (hat) or the left stick, read every frame
		held = set()
		for pad in list(self.pads.values()):
			try:
				x, y = pad.get_hat(0) if pad.get_numhats() else (0, 0)
				y = -y   # the hat's up is +1, the screen's up is -1
				if pad.get_numaxes() >= 2:
					x = x or (1 if pad.get_axis(0) > DEAD_ZONE else -1 if pad.get_axis(0) < -DEAD_ZONE else 0)
					y = y or (1 if pad.get_axis(1) > DEAD_ZONE else -1 if pad.get_axis(1) < -DEAD_ZONE else 0)
				if pad.get_numaxes() >= 6 and pad.get_axis(5) > 0.5:
					held.add(pygame.K_LSHIFT)
			except pygame.error:
				continue
			if x or y: using_pad = True
			if x: held.add(pygame.K_RIGHT if x > 0 else pygame.K_LEFT)
			if y: held.add(pygame.K_DOWN if y > 0 else pygame.K_UP)
		# a new direction also counts as one key press, so menus move one row at a time
		for key in held - self.held:
			if key != pygame.K_LSHIFT:
				pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key = key, unicode = '', mod = 0, scancode = 0, pad = True))
		self.held = held
		virtual_held.update(held)
		if self.sprint:
			virtual_held.add(pygame.K_LSHIFT)


# The on-screen buttons for touch screens.
class TouchControls:
	def __init__(self, fonts):
		self.fonts = fonts
		self.enabled = False   # becomes True the first time the screen is touched
		size = 64
		pad = vector(110, WINDOW_HEIGHT - 120)
		self.directions = {
			pygame.K_UP: pygame.FRect(0, 0, size, size).move_to(center = pad + vector(0, -size)),
			pygame.K_DOWN: pygame.FRect(0, 0, size, size).move_to(center = pad + vector(0, size)),
			pygame.K_LEFT: pygame.FRect(0, 0, size, size).move_to(center = pad + vector(-size, 0)),
			pygame.K_RIGHT: pygame.FRect(0, 0, size, size).move_to(center = pad + vector(size, 0)),
		}
		right = WINDOW_WIDTH - 110
		self.buttons = {   # key -> (rectangle, label)
			pygame.K_SPACE: (pygame.FRect(0, 0, 84, 84).move_to(center = (right, WINDOW_HEIGHT - 150)), 'A'),
			pygame.K_ESCAPE: (pygame.FRect(0, 0, 70, 70).move_to(center = (right - 100, WINDOW_HEIGHT - 80)), 'B'),
			pygame.K_RETURN: (pygame.FRect(0, 0, 70, 46).move_to(center = (right - 120, WINDOW_HEIGHT - 190)), 'Party'),
			pygame.K_m: (pygame.FRect(0, 0, 70, 46).move_to(center = (right + 10, WINDOW_HEIGHT - 60)), 'Map'),
		}
		# Iteration 18: held down to sprint, like the direction buttons
		self.run_button = pygame.FRect(0, 0, 70, 46).move_to(center = (110, WINDOW_HEIGHT - 250))
		self.fingers = {}   # finger id -> direction key it is holding

	# Returns True if a position is on one of the on-screen buttons (so menus ignore that tap).
	def covers(self, pos):
		if not self.enabled:
			return False
		return any(rect.collidepoint(pos) for rect in self.directions.values()) or any(rect.collidepoint(pos) for rect, _ in self.buttons.values()) or self.run_button.collidepoint(pos)

	# Reads touch events. A direction is held while a finger stays on it; a button is a single tap
	# (it is also posted as a key event so menu screens receive it).
	def handle(self, events):
		for event in events:
			# Iteration 18: the on-screen buttons hide again as soon as the real keyboard or mouse is used
			# (before this they stayed on screen for the rest of the game)
			real_key = event.type == pygame.KEYDOWN and not getattr(event, 'touch', False) and not getattr(event, 'pad', False)
			real_mouse = event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN) and not getattr(event, 'touch', False)
			if (real_key or real_mouse) and self.enabled:
				self.enabled = False
				self.fingers.clear()
			if event.type not in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
				continue
			self.enabled = True
			pos = (event.x * WINDOW_WIDTH, event.y * WINDOW_HEIGHT)
			if event.type == pygame.FINGERUP:
				self.fingers.pop(event.finger_id, None)
			else:
				direction = next((key for key, rect in self.directions.items() if rect.collidepoint(pos)), None)
				if direction is None and self.run_button.collidepoint(pos):
					direction = pygame.K_LSHIFT
				if direction:
					if self.fingers.get(event.finger_id) != direction and direction != pygame.K_LSHIFT:
						pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key = direction, unicode = '', mod = 0, scancode = 0, touch = True))
					self.fingers[event.finger_id] = direction
				else:
					self.fingers.pop(event.finger_id, None)
				if event.type == pygame.FINGERDOWN:
					for key, (rect, _) in self.buttons.items():
						if rect.collidepoint(pos):
							virtual_pressed.add(key)
							pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key = key, unicode = '', mod = 0, scancode = 0, touch = True))
		virtual_held.clear()
		virtual_held.update(self.fingers.values())

	def draw(self, surface):
		if not self.enabled:
			return
		overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
		for key, rect in self.directions.items():
			pygame.draw.rect(overlay, (255, 255, 255, 150 if key in virtual_held else 80), rect, 0, 10)
			arrow = {pygame.K_UP: '^', pygame.K_DOWN: 'v', pygame.K_LEFT: '<', pygame.K_RIGHT: '>'}[key]
			text = self.fonts['bold'].render(arrow, False, COLORS['black'])
			overlay.blit(text, text.get_frect(center = rect.center))
		pygame.draw.rect(overlay, (255, 255, 255, 150 if pygame.K_LSHIFT in virtual_held else 80), self.run_button, 0, 10)
		run_text = self.fonts['regular'].render('Run', False, COLORS['black'])
		overlay.blit(run_text, run_text.get_frect(center = self.run_button.center))
		# Iteration 20: Party and Map show icons in the same pixel style as the menus
		from ui_style import icon
		pictures = {'Party': 'person', 'Map': 'map'}
		for key, (rect, label) in self.buttons.items():
			pygame.draw.ellipse(overlay, (255, 255, 255, 110), rect)
			if label in pictures:
				picture = icon(pictures[label], 3, (40, 38, 46), (255, 215, 0))
				overlay.blit(picture, picture.get_frect(center = rect.center))
			else:
				text = self.fonts['regular'].render(label, False, COLORS['black'])
				overlay.blit(text, text.get_frect(center = rect.center))
		surface.blit(overlay, (0, 0))
