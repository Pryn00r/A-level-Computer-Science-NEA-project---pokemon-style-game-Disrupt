# ui_style.py
# Iteration 18: the pixel-art look shared by every menu - chunky frames with stepped corners,
# bracket-shaped buttons and small icons drawn from text patterns (so no extra image files are needed).

from math import sin

from os.path import exists

from settings import *

# menu colours
UI = {
	'frame_light': (220, 220, 220),
	'frame_dark': (52, 50, 56),
	'fill': (40, 38, 46, 228),
	'row': (62, 59, 70),
	'row_edge': (88, 84, 98),
	'selected': (236, 236, 236),
	'selected_text': (30, 28, 34),
	'text': (240, 240, 240),
	'muted': (160, 156, 170),
	'gold': (255, 215, 0),
}

# Icons as 12 x 12 patterns: '#' = dark outline, 'o' = light fill, anything else = see-through.
ICONS = {
	'person': [
		'....####....', '...#oooo#...', '..#oo##oo#..', '..#o#oo#o#..', '..#oooooo#..', '...#o##o#...',
		'....####....', '..##oooo##..', '.#oooooooo#.', '#oooo##oooo#', '#oooooooooo#', '############'],
	'sun': [
		'.....##.....', '..#..##..#..', '...#....#...', '....####....', '...#oooo#...', '##.#oooo#.##',
		'##.#oooo#.##', '...#oooo#...', '....####....', '...#....#...', '..#..##..#..', '.....##.....'],
	'moon': [
		'....####....', '..##oo##....', '.#ooo#......', '.#oo#.......', '#ooo#.......', '#ooo#.......',
		'#ooo#.......', '#oooo#......', '.#ooo##...#.', '.#oooo####..', '..##oooo##..', '....####....'],
	'sound': [
		'.....#......', '....##..#...', '...#o#...#..', '####o#.#..#.', '#ooooo#.#.#.', '#ooooo#.#.#.',
		'#ooooo#.#.#.', '#ooooo#.#.#.', '####o#.#..#.', '...#o#...#..', '....##..#...', '.....#......'],
	'mute': [
		'.....#......', '....##......', '...#o#......', '####o#.#...#', '#ooooo#.#.#.', '#ooooo#..#..',
		'#ooooo#..#..', '#ooooo#.#.#.', '####o#.#...#', '...#o#......', '....##......', '.....#......'],
	'settings': [
		'............', '############', '#oooooooooo#', '############', '............', '############',
		'#oooooooooo#', '############', '............', '############', '#oooooooooo#', '############'],
	'search': [
		'....#####...', '...#ooooo#..', '..#oo###oo#.', '..#o#...#o#.', '..#o#...#o#.', '..#oo###oo#.',
		'...#ooooo#..', '...######...', '..##o#......', '.##o#.......', '##o#........', '###.........'],
	'trophy': [
		'############', '#o########o#', '#o#oooooo#o#', '.##oooooo##.', '..#oooooo#..', '...#oooo#...',
		'....#oo#....', '.....##.....', '.....##.....', '...######...', '..#oooooo#..', '..########..'],
	'help': [
		'...######...', '..#oooooo#..', '.#oo####oo#.', '.#o#....#o#.', '.###...#oo#.', '......#oo#..',
		'.....#oo#...', '.....#o#....', '.....###....', '............', '.....###....', '.....###....'],
	'policy': [
		'.#########..', '.#ooooooo##.', '.#o#####o#o#', '.#ooooooo###', '.#o######oo#', '.#ooooooooo#',
		'.#o#######o#', '.#ooooooooo#', '.#o######oo#', '.#ooooooooo#', '.#ooooooooo#', '.###########'],
	'door': [
		'..########..', '..#oooooo#..', '..#oooooo#..', '..#oooooo#..', '..#oooooo#..', '..#oooo#o#..',
		'..#oooooo#..', '..#oooooo#..', '..#oooooo#..', '..#oooooo#..', '..#oooooo#..', '############'],
	'power': [
		'.....##.....', '..#..##..#..', '.#o#.##.#o#.', '#o#..##..#o#', '#o#..##..#o#', '#o#......#o#',
		'#o#......#o#', '#o#......#o#', '.#o#....#o#.', '..#oo##oo#..', '...######...', '............'],
	# Iteration 20: icons for the menu rows
	'bag': [
		'....####....', '...#....#...', '..#......#..', '############', '#oooooooooo#', '#oo######oo#',
		'#oo#oooo#oo#', '#oo######oo#', '#oooooooooo#', '#oooooooooo#', '#oooooooooo#', '############'],
	'map': [
		'####........', '#oo####.....', '#oooo#o####.', '#o#oo#oooo#.', '#oo#o#o#oo##', '#oooo#oo#oo#',
		'#o#oo#ooooo#', '#oo#o#o##oo#', '#oooo#oooo##', '#####o#oo#..', '.....####...', '............'],
	'badge': [
		'....####....', '..##oooo##..', '.#oooooooo#.', '.#oo#oo#oo#.', '#oooo##oooo#', '#oo######oo#',
		'#oooo##oooo#', '.#oo#oo#oo#.', '.#oooooooo#.', '..##oooo##..', '..#.####.#..', '.##......##.'],
	'book': [
		'.##########.', '#oooo##oooo#', '#o##o##o##o#', '#oooo##oooo#', '#o##o##o##o#', '#oooo##oooo#',
		'#o##o##o##o#', '#oooo##oooo#', '#oooo##oooo#', '############', '............', '............'],
	'scroll': [
		'.##########.', '#oooooooooo#', '.#o######o#.', '.#oooooooo#.', '.#o#####oo#.', '.#oooooooo#.',
		'.#o######o#.', '.#oooooooo#.', '.#o####ooo#.', '#oooooooooo#', '.##########.', '............'],
	'note': [
		'.....######.', '.....#oooo#.', '.....######.', '.....#....#.', '.....#....#.', '.....#....#.',
		'.....#....#.', '..####..####', '.#oooo##ooo#', '.#oooo##ooo#', '..####..###.', '............'],
	'keyboard': [
		'............', '############', '#o#o#o#o#o##', '############', '#oo#o#o#o#o#', '############',
		'#o#oooooo#o#', '############', '............', '............', '............', '............'],
	'film': [
		'############', '#o#oooooo#o#', '############', '#o#oooooo#o#', '#o#oooooo#o#', '#o#oooooo#o#',
		'#o#oooooo#o#', '############', '#o#oooooo#o#', '############', '............', '............'],
	'heal': [
		'....####....', '....#oo#....', '....#oo#....', '#####oo#####', '#oooooooooo#', '#oooooooooo#',
		'#####oo#####', '....#oo#....', '....#oo#....', '....####....', '............', '............'],
	# Iteration 19: icons for the world HUD (coins, quest reward waiting, game saved)
	'coin': [
		'....####....', '..##oooo##..', '.#oooooooo#.', '.#ooo##ooo#.', '#oooo##oooo#', '#oooo##oooo#',
		'#oooo##oooo#', '#oooo##oooo#', '.#ooo##ooo#.', '.#oooooooo#.', '..##oooo##..', '....####....'],
	'quest': [
		'....####....', '....#oo#....', '....#oo#....', '....#oo#....', '....#oo#....', '....#oo#....',
		'....#oo#....', '....####....', '............', '....####....', '....#oo#....', '....####....'],
	'save': [
		'##########..', '#oo#oooo#o#.', '#oo#oooo#oo#', '#oo######oo#', '#oooooooooo#', '#o########o#',
		'#o#oooooo#o#', '#o#oooooo#o#', '#o#oooooo#o#', '#o#oooooo#o#', '#o#oooooo#o#', '############'],	# Iteration 24/25: icons for the new settings
	'eye': [
		'............', '............', '...######...', '.##oooooo##.', '#ooo####ooo#', '#oo#o##o#oo#',
		'#oo#o##o#oo#', '#ooo####ooo#', '.##oooooo##.', '...######...', '............', '............'],
	'text': [
		'############', '#oooooooooo#', '#oo######oo#', '####o##o####', '...#o##o#...', '...#o##o#...',
		'...#o##o#...', '...#o##o#...', '...#o##o#...', '..##o##o##..', '..#oooooo#..', '..########..'],
	'sword': [
		'..........##', '.........#o#', '........#o#.', '.......#o#..', '......#o#...', '.....#o#....',
		'.##.#o#.....', '.#o#o#......', '..#o#.......', '.#o#o#......', '#o#.##......', '##..........'],
	'clock': [
		'...######...', '..#oooooo#..', '.#ooo##ooo#.', '#oooo##oooo#', '#oooo##oooo#', '#oooo####oo#',
		'#oooooooooo#', '#oooooooooo#', '.#oooooooo#.', '..#oooooo#..', '...######...', '............'],
	'grass': [
		'............', '.#....#...#.', '#o#..#o#.#o#', '#o#..#o#.#o#', '#o#.#oo#.#o#', '#oo##o#.#oo#',
		'.#o#oo##oo#.', '.#oo#o#oo#..', '..#oooooo#..', '.##########.', '############', '............'],
	'house': [   # Iteration 29: the Town menu option
		'.....##.....', '....#oo#....', '...#oooo#...', '..#oooooo#..', '.#oooooooo#.', '############',
		'.#oooooooo#.', '.#oo##oooo#.', '.#oo##o##o#.', '.#oo##o##o#.', '.#oo##oooo#.', '.##########.'],
	'pad': [
		'............', '............', '.##########.', '#oo#oooo#oo#', '#o###oo##oo#', '##ooo#oooo##',
		'#o###oo##oo#', '#oo#oooo#oo#', '#oooo##oooo#', '#ooo#..#ooo#', '.###....###.', '............'],
}

_icon_cache = {}

# Returns an icon as a Surface, made from its pattern and scaled up so each pattern cell is `scale` pixels.
def icon(name, scale = 3, dark = UI['frame_dark'], light = UI['frame_light']):
	key = (name, scale, dark, light)
	if key not in _icon_cache:
		# Iteration 26: some icons come from Shikashi's Fantasy Icons Pack instead of the 12 x 12 patterns
		path = asset('graphics', 'item_icons', f'ui_{name}.png')
		if exists(path):
			_icon_cache[key] = pygame.transform.scale(pygame.image.load(path).convert_alpha(), (12 * scale, 12 * scale))
			return _icon_cache[key]
		pattern = ICONS.get(name, ICONS['star'] if 'star' in ICONS else next(iter(ICONS.values())))
		surf = pygame.Surface((len(pattern[0]), len(pattern)), pygame.SRCALPHA)
		for y, row in enumerate(pattern):
			for x, cell in enumerate(row):
				if cell == '#':
					surf.set_at((x, y), dark)
				elif cell == 'o':
					surf.set_at((x, y), light)
		_icon_cache[key] = pygame.transform.scale_by(surf, scale)
	return _icon_cache[key]

# Draws a pixel-art frame: a light outer border with stepped (notched) corners, a dark inner
# border and a see-through dark fill. Parameters: surface, rect, step (size of a corner step in px).
def pixel_frame(surface, rect, step = 6, fill = UI['fill'], light = UI['frame_light'], dark = UI['frame_dark']):
	rect = pygame.Rect(rect)
	body = pygame.Surface(rect.size, pygame.SRCALPHA)
	inner = pygame.Rect(0, 0, rect.width, rect.height)
	# fill, cut back at the corners so they look stepped
	pygame.draw.rect(body, fill, inner.inflate(-step * 2, 0))
	pygame.draw.rect(body, fill, inner.inflate(0, -step * 2))
	pygame.draw.rect(body, fill, inner.inflate(-step, -step))
	# light border: straight edges plus two steps at each corner
	w, h = rect.size
	edges = [
		(step * 2, 0, w - step * 4, step), (step * 2, h - step, w - step * 4, step),
		(0, step * 2, step, h - step * 4), (w - step, step * 2, step, h - step * 4),
		(step, step, step, step), (w - step * 2, step, step, step),
		(step, h - step * 2, step, step), (w - step * 2, h - step * 2, step, step)]
	for edge in edges:
		pygame.draw.rect(body, light, edge)
	# thin dark line just inside the light border
	pygame.draw.rect(body, dark, inner.inflate(-step * 3, -step * 3), max(2, step // 3), step)
	surface.blit(body, rect.topleft)

# Draws a bracket-style button (like "< text >"). Selected buttons are light with dark text and a
# small arrow that bobs left and right. Returns the button's rectangle.
def pixel_button(surface, rect, text, font, selected = False, enabled = True):
	rect = pygame.FRect(rect)
	step = 4
	fill = UI['selected'] if selected else UI['row']
	pygame.draw.rect(surface, fill, rect.inflate(-step * 2, 0))
	pygame.draw.rect(surface, fill, rect.inflate(0, -step * 2))
	edge = UI['frame_light'] if not selected else UI['frame_dark']
	pygame.draw.line(surface, UI['row_edge'] if not selected else (255, 255, 255), rect.topleft + vector(step, 0), rect.topright + vector(-step - 1, 0), 2)
	pygame.draw.line(surface, (20, 20, 24), rect.bottomleft + vector(step, -1), rect.bottomright + vector(-step - 1, -1), 2)
	# brackets at each end
	for side in (-1, 1):
		x = rect.left + 6 if side < 0 else rect.right - 8
		pygame.draw.rect(surface, edge, (x, rect.top + 8, 3, rect.height - 16))
		pygame.draw.rect(surface, edge, (x + (3 if side < 0 else -3), rect.top + 8, 3, 3))
		pygame.draw.rect(surface, edge, (x + (3 if side < 0 else -3), rect.bottom - 11, 3, 3))
	color = UI['selected_text'] if selected else (UI['text'] if enabled else UI['muted'])
	text_surf = font.render(text, False, color)
	surface.blit(text_surf, text_surf.get_frect(center = rect.center))
	if selected:
		bob = (pygame.time.get_ticks() // 180) % 2 * 3
		points = [(rect.left + 18 + bob, rect.centery - 6), (rect.left + 26 + bob, rect.centery), (rect.left + 18 + bob, rect.centery + 6)]
		pygame.draw.polygon(surface, UI['selected_text'], points)
	return rect

# Draws a square icon button (a small pixel frame with an icon in it). Returns its rectangle.
def icon_button(surface, center, name, selected = False, size = 56, active = True):
	rect = pygame.FRect(0, 0, size, size).move_to(center = center)
	fill = (236, 236, 236, 240) if selected else (40, 38, 46, 220)
	pixel_frame(surface, rect, 4, fill = fill)
	image = icon(name, 3, UI['frame_dark'] if selected else UI['frame_light'], UI['gold'] if active else UI['muted'])
	surface.blit(image, image.get_frect(center = rect.center))
	return rect

# Iteration 19: a small pixel-framed label for the world HUD (coins, quest reminder, 'Saved', messages),
# so these match the menu buttons instead of being plain coloured boxes. An optional icon sits on
# the left. Position it with one anchor, e.g. topleft = (20, 20). Returns its rectangle.
def hud_tag(surface, text, font, icon_name = None, color = UI['text'], alpha = 255, border = UI['frame_light'], **anchor):
	text_surf = font.render(text, False, color)
	width = text_surf.get_width() + 32 + (32 if icon_name else 0)
	height = max(44, text_surf.get_height() + 22)
	rect = pygame.FRect(0, 0, width, height)
	setattr(rect, *next(iter(anchor.items())))
	layer = pygame.Surface(rect.size, pygame.SRCALPHA)
	pixel_frame(layer, layer.get_frect(), 4, fill = (40, 38, 46, 235), light = border)
	x = 16
	if icon_name:
		image = icon(icon_name, 2, UI['frame_dark'], UI['gold'])
		layer.blit(image, image.get_frect(midleft = (x, height / 2)))
		x += 32
	layer.blit(text_surf, text_surf.get_frect(midleft = (x, height / 2)))
	layer.set_alpha(alpha)
	surface.blit(layer, rect)
	return rect

# The game's name in a capsule-shaped pixel frame with a drop shadow (used on the title and menu).
def draw_logo(surface, font, center, scale = 2.2):
	text = pygame.transform.scale_by(font.render(GAME_TITLE.upper(), False, UI['frame_light']), scale)
	shadow = pygame.transform.scale_by(font.render(GAME_TITLE.upper(), False, (20, 20, 24)), scale)
	frame = text.get_frect(center = center).inflate(90, 50)
	pixel_frame(surface, frame, 8, fill = (40, 38, 46, 200))
	surface.blit(shadow, shadow.get_frect(center = (center[0] + 5, center[1] + 5)))
	surface.blit(text, text.get_frect(center = center))
	return frame


# ---------- Iteration 19: badges ----------
# Each badge is drawn on a tiny 32 x 40 canvas and scaled up 3 times, so it looks like pixel art.
# Ordinary badges are round medals; gym leader badges are bigger-looking hexagons. Both hang from
# two ribbon tails in the badge's colour. Earned badges are coloured with a gold rim and a shine
# that sweeps across; badges not earned yet are a dark shape with a '?'.
BADGE_STYLE = {   # badge name -> (main colour, emblem)
	'Rookie': ((222, 84, 84), 'star'),     'Shell': ((240, 150, 175), 'shell'),  'Sunny': ((250, 196, 60), 'sun'),
	'Meadow': ((130, 205, 95), 'flower'),  'Grove': ((70, 150, 85), 'tree'),     'Leaf': ((80, 190, 95), 'leaf'),
	'Frost': ((150, 205, 240), 'flake'),   'Flame': ((240, 120, 45), 'flame'),   'Glacier': ((95, 190, 220), 'crystal'),
	'Tide': ((65, 115, 225), 'wave'),
}
_badge_cache = {}

def _shade(color, amount):
	return tuple(max(0, min(255, int(c * amount))) for c in color)

def _emblem(canvas, emblem, colour, c = (16, 16)):
	x, y = c
	if emblem == 'star':
		points = [vector(0, -8).rotate(i * 36) * (1 if i % 2 == 0 else 0.45) + c for i in range(10)]
		pygame.draw.polygon(canvas, colour, points)
	elif emblem == 'shell':
		pygame.draw.circle(canvas, colour, (x, y + 3), 7, draw_top_left = True, draw_top_right = True)
		pygame.draw.rect(canvas, colour, (x - 3, y + 3, 7, 4))
		for dx in (-4, 0, 4):
			pygame.draw.line(canvas, _shade(colour, 0.7), (x, y + 6), (x + dx, y - 3))
	elif emblem == 'sun':
		pygame.draw.circle(canvas, colour, c, 4)
		for i in range(8):
			end = vector(0, -8).rotate(i * 45) + c
			pygame.draw.line(canvas, colour, vector(0, -6).rotate(i * 45) + c, end)
	elif emblem == 'flower':
		for i in range(5):
			pygame.draw.circle(canvas, colour, vector(0, -4).rotate(i * 72) + c, 3)
		pygame.draw.circle(canvas, (250, 210, 80), c, 2)
	elif emblem == 'tree':
		pygame.draw.polygon(canvas, colour, [(x, y - 8), (x - 7, y + 3), (x + 7, y + 3)])
		pygame.draw.rect(canvas, _shade(colour, 0.6), (x - 1, y + 3, 3, 5))
	elif emblem == 'leaf':
		pygame.draw.ellipse(canvas, colour, (x - 4, y - 8, 9, 16))
		pygame.draw.line(canvas, _shade(colour, 0.6), (x, y - 6), (x, y + 8))
		for dy in (-3, 1):
			pygame.draw.line(canvas, _shade(colour, 0.6), (x, y + dy + 2), (x - 3, y + dy))
			pygame.draw.line(canvas, _shade(colour, 0.6), (x, y + dy + 2), (x + 3, y + dy))
	elif emblem == 'flake':
		for angle in (0, 60, 120):
			a, b = vector(0, -8).rotate(angle) + c, vector(0, 8).rotate(angle) + c
			pygame.draw.line(canvas, colour, a, b)
			for end in (a, b):
				pygame.draw.circle(canvas, colour, end, 1)
	elif emblem == 'flame':
		pygame.draw.polygon(canvas, colour, [(x, y - 9), (x + 3, y - 3), (x + 6, y - 1), (x + 5, y + 5), (x, y + 8), (x - 5, y + 5), (x - 6, y - 1), (x - 3, y + 1)])
		pygame.draw.polygon(canvas, (255, 230, 120), [(x, y - 1), (x + 3, y + 4), (x, y + 7), (x - 3, y + 4)])
	elif emblem == 'crystal':
		pygame.draw.polygon(canvas, colour, [(x, y - 9), (x + 6, y - 2), (x, y + 9), (x - 6, y - 2)])
		pygame.draw.line(canvas, _shade(colour, 0.7), (x - 6, y - 2), (x + 6, y - 2))
		pygame.draw.line(canvas, _shade(colour, 0.7), (x, y - 9), (x, y + 9))
	elif emblem == 'wave':
		for row in (-3, 3):
			points = [(x - 8 + i, y + row + round(2 * sin(i * 0.8))) for i in range(17)]
			pygame.draw.lines(canvas, colour, False, points, 2)

# Returns the badge picture (96 x 120). Parameters: name (e.g. 'Leaf'), earned (bool), gym (bool).
GYM_GEMS = {'Leaf': 'green', 'Flame': 'red', 'Tide': 'blue'}   # Iteration 32: the three gym badges are the coloured gems

# Iteration 35: the whole badge from the badge art - wings (gym badges only), the outline frame and the gem.
# Gym badges keep the art's own red, green and blue; the others are the grey parts tinted with their colour;
# badges not won yet are a dark shape. Returns None if the pictures are missing.
def _badge_part(part, colour):
	path = asset('graphics', 'badges', f'{part}_{colour}.png')
	return pygame.image.load(path).convert_alpha() if exists(path) else None

def _gem(name, earned, gym = False):
	colour = GYM_GEMS.get(name, 'grey')
	gem, frame, wing = _badge_part('gem', colour), _badge_part('frame', colour), _badge_part('wing', colour) if gym else None
	if gem is None or frame is None:
		return None
	width = max(frame.get_width(), wing.get_width() if wing else 0)
	canvas = pygame.Surface((width, frame.get_height() + 6), pygame.SRCALPHA)
	centre = (width / 2, frame.get_height() / 2)
	if wing:
		canvas.blit(wing, wing.get_frect(center = (centre[0], centre[1] + 7)))
	canvas.blit(frame, frame.get_frect(center = centre))
	canvas.blit(gem, gem.get_frect(center = (centre[0], centre[1] + 1)))
	if not earned:   # a dark shape you have not won yet
		canvas.fill((70, 66, 80, 255), special_flags = pygame.BLEND_RGBA_MULT)
	elif colour == 'grey':   # the other badges are the grey parts tinted with their own colour
		tint = tuple(min(255, int(c * 1.25)) for c in BADGE_STYLE.get(name, ((200, 200, 200), ''))[0]) + (255,)
		canvas.fill(tint, special_flags = pygame.BLEND_RGBA_MULT)
	return pygame.transform.scale(canvas, (canvas.get_width() * 2, canvas.get_height() * 2))

def badge_image(name, earned, gym):
	key = (name, earned, gym)
	if key not in _badge_cache:
		colour, emblem = BADGE_STYLE.get(name, ((200, 200, 200), 'star'))
		canvas = pygame.Surface((32, 40), pygame.SRCALPHA)
		if earned:
			main, dark, rim, ink = colour, _shade(colour, 0.6), UI['gold'], (255, 255, 255)
		else:
			main, dark, rim, ink = (62, 59, 70), (40, 38, 46), (88, 84, 98), (120, 116, 130)
		# ribbon tails
		pygame.draw.polygon(canvas, dark, [(9, 22), (14, 22), (13, 39), (10, 36), (7, 39)])
		pygame.draw.polygon(canvas, dark, [(18, 22), (23, 22), (25, 39), (22, 36), (19, 39)])
		badge = _gem(name, earned, gym)
		if badge:
			image = pygame.Surface((max(96, badge.get_width()), 120), pygame.SRCALPHA)
			image.blit(badge, badge.get_frect(center = (image.get_width() / 2, 52)))
			_badge_cache[key] = image
			return image
		# the medal: hexagon for gym leaders, circle for everyone else
		if gym:
			outer = [vector(0, -15).rotate(i * 60) + (16, 16) for i in range(6)]
			inner = [vector(0, -12).rotate(i * 60) + (16, 16) for i in range(6)]
			pygame.draw.polygon(canvas, rim, outer)
			pygame.draw.polygon(canvas, main, inner)
			pygame.draw.polygon(canvas, dark, inner, 1)
		else:
			pygame.draw.circle(canvas, rim, (16, 16), 14)
			pygame.draw.circle(canvas, main, (16, 16), 12)
			pygame.draw.circle(canvas, dark, (16, 16), 12, 1)
		if earned:
			_emblem(canvas, emblem, ink)
			canvas.set_at((10, 8), (255, 255, 255))   # a little highlight
			canvas.set_at((9, 9), (255, 255, 255))
		else:
			mark = pygame.font.Font(None, 20).render('?', False, ink)
			canvas.blit(mark, mark.get_frect(center = (16, 17)))
		_badge_cache[key] = pygame.transform.scale(canvas, (96, 120))
	return _badge_cache[key]

# Draws a badge centred at a point. Earned badges get a shine sweeping across every few seconds.
def draw_badge(surface, center, name, earned, gym, time = 0.0):
	image = badge_image(name, earned, gym)
	rect = image.get_frect(center = center)
	surface.blit(image, rect)
	if earned:
		sweep = (time * 60) % 260 - 60   # the shine's x position on the badge, with a pause between sweeps
		if 0 <= sweep <= 96:
			shine = pygame.Surface(image.get_size(), pygame.SRCALPHA)
			pygame.draw.polygon(shine, (255, 255, 255, 110), [(sweep, 0), (sweep + 14, 0), (sweep - 16, 66), (sweep - 30, 66)])
			mask = pygame.mask.from_surface(image).to_surface(setcolor = (255, 255, 255, 255), unsetcolor = (0, 0, 0, 0))
			shine.blit(mask, (0, 0), special_flags = pygame.BLEND_RGBA_MULT)   # keep the shine inside the badge shape
			surface.blit(shine, rect)
	return rect

# Iteration 32: the spinning loading icon (5 frames from the New folder art). Returns None if the files are missing.
_spinner = []
def spinner(time, size = 32):
	if not _spinner:
		for n in range(5):
			path = asset('graphics', 'ui_pack', f'spinner_{n}.png')
			if not exists(path):
				return None
			_spinner.append(pygame.image.load(path).convert_alpha())
	frame = _spinner[int(time * 10) % len(_spinner)]
	return pygame.transform.scale(frame, (size, size))
