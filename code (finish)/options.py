# options.py
# Iteration 24/25: the extra settings and what they change in the game.
#   colour_blind   - type colours from a palette that people with red-green colour blindness can tell apart
#   large_text     - every font about 20% bigger
#   difficulty     - easy / normal / hard: trainer levels, XP and catch rate
#   autosave       - how often the game saves itself (off, 1, 3 or 5 minutes)
#   encounter_rate - how quickly wild monsters appear in long grass
#   keys           - the second key for each direction and for sprinting (WASD + Shift by default)

from settings import *
import item_art

DIFFICULTIES = ('easy', 'normal', 'hard')
# level change for trainers' monsters, XP multiplier and catch-chance multiplier
DIFFICULTY_EFFECTS = {'easy': (-2, 1.25, 1.25), 'normal': (0, 1.0, 1.0), 'hard': (2, 0.85, 0.85)}
AUTOSAVE_CHOICES = (0, 60, 180, 300)          # seconds, 0 = off
ENCOUNTER_RATES = ('low', 'normal', 'high')
ENCOUNTER_DELAY = {'low': (1600, 4000), 'normal': (800, 2500), 'high': (300, 1100)}   # ms before a battle starts
FONT_SIZES = {'dialog': 30, 'regular': 18, 'small': 14, 'bold': 20, 'pixel': 12}
FONT_FILES = {'dialog': 'PixeloidSans.ttf', 'regular': 'PixeloidSans.ttf', 'small': 'PixeloidSans.ttf', 'bold': 'dogicapixelbold.otf', 'pixel': 'dogicapixel.otf'}
LARGE_TEXT = 1.2

# the second key for each action, changed on the Controls screen
REBINDABLE = ('up', 'down', 'left', 'right', 'sprint')
DEFAULT_KEYS = {'up': pygame.K_w, 'down': pygame.K_s, 'left': pygame.K_a, 'right': pygame.K_d, 'sprint': pygame.K_RSHIFT}
MAIN_KEY = {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT, 'right': pygame.K_RIGHT, 'sprint': pygame.K_LSHIFT}
RESERVED = {pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_LSHIFT}

# Okabe-Ito based colours: easy to tell apart with any common type of colour blindness
COLOUR_BLIND_TYPES = {
	'normal': (200, 200, 200), 'fire': (230, 159, 0), 'water': (0, 114, 178), 'plant': (0, 158, 115),
	'ice': (86, 180, 233), 'poison': (204, 121, 167), 'bug': (240, 228, 66), 'flying': (150, 150, 255), 'psychic': (213, 94, 0), 'rock': (160, 130, 90),
	'dark': (60, 60, 60), 'ghost': (120, 100, 200), 'fairy': (255, 170, 220),
}
_original_colours = dict(COLORS)
_original_types = dict(item_art.TYPE_COLOURS)

def hex_colour(rgb):
	return '#%02x%02x%02x' % rgb

# Changes the shared colour dictionaries in place, so every screen picks up the new colours.
def apply_colour_blind(on):
	COLORS.update(_original_colours)
	item_art.TYPE_COLOURS.update(_original_types)
	if on:
		for element, rgb in COLOUR_BLIND_TYPES.items():
			COLORS[element] = hex_colour(rgb)
			item_art.TYPE_COLOURS[element] = rgb
		COLORS['red'] = '#d55e00'    # health bars: orange instead of red
		COLORS['blue'] = '#56b4e9'

# Fills the fonts dictionary in place (screens keep a reference to the same dictionary).
def build_fonts(fonts, large = False):
	scale = LARGE_TEXT if large else 1
	for name, size in FONT_SIZES.items():
		fonts[name] = pygame.font.Font(asset('graphics', 'fonts', FONT_FILES[name]), round(size * scale))
	return fonts

# the effects of the current difficulty, read by entities.py (trainer levels) and battle.py (XP, catching)
state = {'level': 0, 'xp': 1.0, 'catch': 1.0}

def apply_difficulty(name):
	state['level'], state['xp'], state['catch'] = DIFFICULTY_EFFECTS.get(name, DIFFICULTY_EFFECTS['normal'])

def difficulty(preferences):
	return DIFFICULTY_EFFECTS.get(preferences['difficulty'], DIFFICULTY_EFFECTS['normal'])

def encounter_delay(preferences):
	return ENCOUNTER_DELAY.get(preferences['encounter_rate'], ENCOUNTER_DELAY['normal'])

# Puts the chosen keys into controls.ALIASES (the arrow keys always work as well).
def apply_keys(keys):
	import controls
	for action in REBINDABLE:
		key = keys.get(action, DEFAULT_KEYS[action])
		controls.ALIASES[MAIN_KEY[action]] = (MAIN_KEY[action], key) + ((pygame.K_RSHIFT,) if action == 'sprint' and key != pygame.K_RSHIFT else ())

# Checks a key binding from the preferences file. Returns the cleaned dictionary.
def valid_keys(keys):
	clean = dict(DEFAULT_KEYS)
	if isinstance(keys, dict):
		used = set()
		for action in REBINDABLE:
			key = keys.get(action)
			if isinstance(key, int) and key not in RESERVED and key not in used:
				clean[action] = key
			used.add(clean[action])
	return clean

# Changes one binding. Returns an error key, or None if it worked. Two actions cannot share a key.
def rebind(keys, action, key):
	if key in RESERVED:
		return 'keys_reserved'
	for other, bound in keys.items():
		if other != action and bound == key:
			return 'keys_taken'
	keys[action] = key
	return None
