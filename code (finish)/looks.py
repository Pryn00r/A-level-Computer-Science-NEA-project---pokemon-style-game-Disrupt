# looks.py
# Iteration 22, simplified in Iteration 27: the player is always the game's original trainer. The only
# change allowed is the colour of the clothes, chosen at the dresser in the bedroom.
# A look is a dictionary {'hue': degrees, 'gold': True/False}:
#   hue  - turns the colours of the clothes round the colour wheel (0 = the original colours)
#   gold - turns the clothes gold instead
# Skin, eyes and outlines are never changed. Recoloured frames are made once and remembered.

from settings import *

# the colours on offer: name -> look
COLOURS = {
	'original': {'hue': 0, 'gold': False},
	'sunset':   {'hue': 30, 'gold': False},
	'lime':     {'hue': 80, 'gold': False},
	'forest':   {'hue': 130, 'gold': False},
	'ocean':    {'hue': 180, 'gold': False},
	'sky':      {'hue': 220, 'gold': False},
	'violet':   {'hue': 270, 'gold': False},
	'rose':     {'hue': 320, 'gold': False},
	'golden':   {'hue': 0, 'gold': True},
}
DEFAULT_LOOK = COLOURS['original']

_cache = {}

def _is_skin(colour):
	r, g, b = colour[:3]
	h, s, v, _ = pygame.Color(r, g, b).hsva
	return 8 <= h <= 40 and 18 <= s <= 62 and v >= 55

def _is_outline(colour):
	return sum(colour[:3]) < 150

# Recolours one frame of the original trainer. The see-through colour, skin and outline are kept.
def _recolour(frame, look):
	out = frame.copy()
	hue, gold = look['hue'], look['gold']
	key = frame.get_colorkey()
	key = tuple(key[:3]) if key else None
	pixels = pygame.PixelArray(out)
	done = {}
	for x in range(out.get_width()):
		for y in range(out.get_height()):
			mapped = pixels[x, y]
			if mapped not in done:
				colour = out.unmap_rgb(mapped)
				new = colour
				if colour.a and tuple(colour[:3]) != key and not _is_outline(colour) and not _is_skin(colour):
					h, s, v, a = colour.hsva
					new = pygame.Color(0, 0, 0)
					new.hsva = (45, min(100, s * 0.6 + 40), min(100, v * 0.9 + 10), a) if gold else ((h + hue) % 360, s, v, a)
				done[mapped] = out.map_rgb(new)
			pixels[x, y] = done[mapped]
	del pixels
	return out

# Returns the walking frames ({'down': [...], 'left_idle': [...], ...}) for a look.
def frames_for(game, look):
	look = validate(look)
	original = game.overworld_frames['characters']['player']
	if not look['hue'] and not look['gold']:
		return original
	key = (look['hue'], look['gold'])
	if key not in _cache:
		_cache[key] = {state: [_recolour(frame, look) for frame in frames] for state, frames in original.items()}
	return _cache[key]

# The player is a boy.
def is_female(look):
	return False

# Checks a look read from a save file. Returns a safe look; anything else (including the character
# designs from Iterations 22-26) becomes the original colours.
def validate(look):
	if not isinstance(look, dict):
		return dict(DEFAULT_LOOK)
	hue = look.get('hue', 0)
	if look.get('base', 'player') != 'player' or 'sheet' in look or 'parts' in look:
		return dict(DEFAULT_LOOK)
	if not isinstance(hue, int) or isinstance(hue, bool) or not 0 <= hue < 360:
		return dict(DEFAULT_LOOK)
	return {'hue': hue, 'gold': look.get('gold') is True}

def colour_name(look):
	look = validate(look)
	return next((name for name, value in COLOURS.items() if value == look), 'original')
