# item_art.py
# Iteration 20: pictures for things that used to be words only - items, types, language flags,
# key caps, medals and status effects. Each one is drawn once in code on a tiny canvas (pixel art),
# given a dark outline like the battle icons, scaled up and remembered (cached).

from math import sin, cos

from os.path import exists

from settings import *

OUTLINE = (34, 32, 52)
_cache = {}

def _outlined(canvas, outline = OUTLINE):
	# adds a 1 pixel outline around everything drawn on the canvas
	w, h = canvas.get_size()
	out = canvas.copy()
	for y in range(h):
		for x in range(w):
			if canvas.get_at((x, y)).a == 0:
				for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
					nx, ny = x + dx, y + dy
					if 0 <= nx < w and 0 <= ny < h and canvas.get_at((nx, ny)).a > 0:
						out.set_at((x, y), outline)
						break
	return out

def _canvas(size = 16):
	return pygame.Surface((size, size), pygame.SRCALPHA)

def _orb(top, bottom, band, button):
	c = _canvas()
	pygame.draw.circle(c, bottom, (8, 8), 6)
	pygame.draw.rect(c, (0, 0, 0, 0), (0, 0, 16, 8))
	top_half = _canvas()
	pygame.draw.circle(top_half, top, (8, 8), 6)
	c.blit(top_half.subsurface((0, 0, 16, 8)), (0, 0))
	pygame.draw.line(c, band, (2, 8), (13, 8))
	pygame.draw.circle(c, button, (8, 8), 2)
	c.set_at((5, 4), (255, 255, 255))
	return c

# ---------- items ----------
def _draw_item(name):
	c = _canvas()
	if name == 'capture_orb':
		return _orb((222, 64, 64), (240, 240, 240), OUTLINE, (250, 250, 250))
	if name == 'great_orb':
		c = _orb((64, 110, 220), (240, 240, 240), OUTLINE, (250, 250, 250))
		c.set_at((4, 5), (230, 60, 60)); c.set_at((11, 5), (230, 60, 60))
		return c
	if name == 'prime_orb':
		return _orb((40, 38, 46), (250, 210, 60), (250, 210, 60), (255, 240, 170))
	if name == 'debug_orb':
		c = _orb((60, 220, 120), (30, 30, 36), (60, 220, 120), (200, 255, 220))
		for x in (4, 7, 10):
			c.set_at((x, 11), (60, 220, 120))
		return c
	if name == 'power_band':
		pygame.draw.rect(c, (210, 55, 55), (2, 6, 12, 4))
		pygame.draw.polygon(c, (210, 55, 55), [(12, 8), (15, 12), (13, 13), (11, 9)])
		pygame.draw.line(c, (255, 140, 140), (3, 7), (12, 7))
	elif name == 'vital_charm':
		pygame.draw.circle(c, (240, 90, 140), (6, 7), 3)
		pygame.draw.circle(c, (240, 90, 140), (10, 7), 3)
		pygame.draw.polygon(c, (240, 90, 140), [(3, 8), (13, 8), (8, 13)])
		pygame.draw.line(c, (200, 200, 210), (8, 1), (8, 4))
		c.set_at((5, 6), (255, 210, 225))
	elif name == 'focus_ring':
		pygame.draw.circle(c, (240, 200, 70), (8, 10), 5, 2)
		pygame.draw.polygon(c, (90, 170, 250), [(8, 1), (11, 4), (8, 7), (5, 4)])
		c.set_at((7, 3), (220, 240, 255))
	elif name == 'wise_feather':
		pygame.draw.polygon(c, (180, 140, 240), [(13, 1), (15, 3), (5, 13), (3, 13), (3, 11)])
		pygame.draw.line(c, (240, 230, 255), (13, 2), (3, 13))
		pygame.draw.line(c, (120, 90, 190), (2, 14), (4, 12))
	elif name == 'illuminator':
		pygame.draw.rect(c, (120, 110, 130), (5, 1, 6, 2))
		pygame.draw.rect(c, (255, 236, 140), (4, 3, 8, 9))
		for i, colour in enumerate(((255, 120, 120), (255, 200, 90), (130, 230, 130), (120, 170, 255))):
			c.set_at((5 + i * 2, 6), colour); c.set_at((5 + i * 2, 8), colour)
		pygame.draw.rect(c, (120, 110, 130), (5, 12, 6, 2))
	elif name in ('burn_heal', 'thaw_spray', 'antidote', 'wake_bell', 'full_cure', 'party_heal', 'max_ether'):
		liquid = {'burn_heal': (250, 140, 60), 'thaw_spray': (150, 220, 250), 'antidote': (170, 90, 220), 'wake_bell': (250, 220, 90),
		          'full_cure': (250, 250, 250), 'party_heal': (250, 110, 170), 'max_ether': (80, 120, 240)}[name]
		if name == 'wake_bell':
			pygame.draw.polygon(c, liquid, [(8, 2), (12, 6), (13, 12), (3, 12), (4, 6)])
			pygame.draw.circle(c, (200, 160, 60), (8, 13), 2)
			c.set_at((6, 5), (255, 255, 220))
		else:
			pygame.draw.rect(c, (180, 180, 190), (6, 1, 4, 3))
			pygame.draw.rect(c, liquid, (4, 4, 8, 10))
			pygame.draw.rect(c, (255, 255, 255), (5, 5, 1, 5))
			if name == 'full_cure':
				pygame.draw.line(c, (230, 60, 60), (8, 6), (8, 11)); pygame.draw.line(c, (230, 60, 60), (6, 8), (10, 8))
	elif name == 'repel':
		pygame.draw.rect(c, (120, 200, 120), (4, 3, 8, 11))
		pygame.draw.rect(c, (60, 60, 70), (6, 1, 4, 2))
		pygame.draw.line(c, (255, 255, 255), (6, 7), (10, 11)); pygame.draw.line(c, (255, 255, 255), (10, 7), (6, 11))
	elif name == 'escape_rope':
		for i in range(10):
			a = i * 0.9
			c.set_at((int(8 + cos(a) * (2 + i * 0.5)), int(8 + sin(a) * (2 + i * 0.5))), (200, 160, 100))
		pygame.draw.circle(c, (200, 160, 100), (8, 8), 6, 1)
	elif name == 'swift_cap':
		pygame.draw.ellipse(c, (60, 140, 230), (3, 4, 10, 8))
		pygame.draw.rect(c, (60, 140, 230), (8, 9, 7, 2))
		pygame.draw.line(c, (255, 230, 80), (5, 6), (9, 6))
	# Iteration 25: tools, new held items and things found by digging and fishing
	elif name == 'fishing_rod':
		pygame.draw.line(c, (150, 100, 60), (2, 14), (13, 2), 2)
		pygame.draw.line(c, (230, 230, 240), (13, 2), (14, 10))
		pygame.draw.circle(c, (230, 60, 60), (14, 11), 1)
		pygame.draw.circle(c, (90, 90, 100), (5, 11), 2)
	elif name == 'shovel':
		pygame.draw.line(c, (150, 100, 60), (3, 3), (10, 10), 2)
		pygame.draw.rect(c, (150, 100, 60), (1, 1, 4, 2))
		pygame.draw.polygon(c, (180, 185, 200), [(9, 8), (14, 9), (15, 14), (10, 15), (8, 11)])
		c.set_at((11, 10), (240, 240, 250))
	elif name == 'snow_boots':
		for x in (2, 9):
			pygame.draw.rect(c, (140, 90, 60), (x, 3, 5, 9))
			pygame.draw.rect(c, (140, 90, 60), (x, 10, 7 if x == 2 else 6, 4))
			pygame.draw.rect(c, (245, 245, 250), (x, 3, 5, 2))
	elif name == 'swift_scarf':
		pygame.draw.rect(c, (250, 200, 60), (2, 4, 12, 4))
		pygame.draw.polygon(c, (250, 200, 60), [(10, 7), (13, 7), (14, 14), (11, 13)])
		for x in (3, 6, 9):
			c.set_at((x, 5), (230, 120, 40))
	elif name == 'guard_shell':
		pygame.draw.ellipse(c, (110, 160, 90), (2, 3, 12, 11))
		pygame.draw.line(c, (70, 110, 60), (8, 3), (8, 13)); pygame.draw.line(c, (70, 110, 60), (2, 8), (14, 8))
		c.set_at((5, 5), (200, 240, 180))
	elif name in ('lucky_coin', 'shiny_charm'):
		colour = (250, 210, 60) if name == 'lucky_coin' else (120, 220, 250)
		pygame.draw.circle(c, colour, (8, 8), 6)
		pygame.draw.circle(c, (255, 255, 255), (8, 8), 6, 1)
		if name == 'lucky_coin':
			pygame.draw.line(c, (200, 150, 30), (8, 4), (8, 12))
		else:
			pygame.draw.polygon(c, (255, 255, 255), [(8, 3), (9, 7), (13, 8), (9, 9), (8, 13), (7, 9), (3, 8), (7, 7)])
	elif name == 'pearl':
		pygame.draw.circle(c, (240, 235, 245), (8, 9), 4)
		c.set_at((7, 7), (255, 255, 255)); pygame.draw.arc(c, (200, 180, 220), (3, 4, 10, 10), 3.6, 5.8)
	elif name == 'fossil':
		pygame.draw.ellipse(c, (190, 170, 140), (2, 3, 12, 11))
		for i in range(4):
			pygame.draw.arc(c, (120, 100, 80), (4 + i, 5 + i, 8 - i * 2, 8 - i * 2), 0, 4.5)
	elif name == 'crystal':
		pygame.draw.polygon(c, (150, 220, 250), [(8, 1), (12, 6), (10, 14), (6, 14), (4, 6)])
		pygame.draw.line(c, (230, 250, 255), (8, 2), (7, 12))
	elif name == 'scrap':
		pygame.draw.polygon(c, (150, 150, 160), [(2, 9), (7, 3), (14, 6), (12, 13), (4, 13)])
		pygame.draw.circle(c, (100, 100, 110), (9, 8), 2)
	elif name == 'herb':
		pygame.draw.line(c, (70, 140, 60), (8, 14), (8, 5))
		for side in (-1, 1):
			pygame.draw.ellipse(c, (100, 190, 80), (8 + (side - 1) * 3, 5, 6, 4))
		pygame.draw.ellipse(c, (100, 190, 80), (6, 1, 4, 6))
	elif name == 'egg':
		pygame.draw.ellipse(c, (245, 240, 225), (3, 1, 10, 14))
		for x, y in ((6, 5), (10, 8), (6, 11)):
			pygame.draw.circle(c, (120, 200, 140), (x, y), 1)
	else:
		pygame.draw.circle(c, (200, 200, 210), (8, 8), 5)
	return c

# Iteration 26: items use the pictures from Shikashi's Fantasy Icons Pack (graphics/item_icons) when there is
# one; the pictures drawn in code are only used if the file is missing.
def pack_picture(name):
	path = asset('graphics', 'item_icons', f'{name}.png')
	return pygame.image.load(path).convert_alpha() if exists(path) else None

def item(name, size = 32):
	key = ('item', name, size)
	if key not in _cache:
		picture = pack_picture(name)
		_cache[key] = pygame.transform.scale(picture if picture else _outlined(_draw_item(name)), (size, size))
	return _cache[key]

# ---------- types ----------
TYPE_COLOURS = {
	'normal': (168, 160, 140), 'fire': (240, 120, 50), 'water': (70, 140, 230), 'plant': (90, 190, 80),
	'ice': (120, 210, 230), 'poison': (170, 80, 200), 'bug': (160, 190, 40), 'flying': (150, 160, 240), 'psychic': (240, 90, 150), 'rock': (176, 150, 110),
	'dark': (70, 62, 80), 'ghost': (110, 96, 180), 'fairy': (236, 130, 190),   # Iteration 35
}

def type_emblem(element, colour = (255, 255, 255)):
	c = _canvas(10)
	x, y = 5, 5
	if element == 'fire':
		pygame.draw.polygon(c, colour, [(5, 0), (8, 4), (8, 7), (5, 9), (2, 7), (2, 4)])
	elif element == 'water':
		pygame.draw.polygon(c, colour, [(5, 0), (8, 5), (5, 9), (2, 5)]); pygame.draw.circle(c, colour, (5, 6), 3)
	elif element == 'plant':
		pygame.draw.ellipse(c, colour, (2, 0, 6, 9)); pygame.draw.line(c, (0, 0, 0, 0), (5, 1), (5, 8))
	elif element == 'ice':
		for a in (0, 60, 120):
			v = vector(0, 4).rotate(a)
			pygame.draw.line(c, colour, (x - v.x, y - v.y), (x + v.x, y + v.y))
	elif element == 'poison':
		pygame.draw.circle(c, colour, (5, 4), 3); pygame.draw.rect(c, colour, (3, 6, 5, 2))
		c.set_at((4, 4), (0, 0, 0, 0)); c.set_at((6, 4), (0, 0, 0, 0))
	elif element == 'bug':
		pygame.draw.ellipse(c, colour, (2, 2, 6, 7)); pygame.draw.line(c, colour, (3, 0), (4, 2)); pygame.draw.line(c, colour, (7, 0), (6, 2))
	elif element == 'flying':
		pygame.draw.polygon(c, colour, [(0, 3), (5, 5), (10, 3), (7, 8), (3, 8)])
	elif element == 'rock':   # Iteration 27: a lumpy stone
		pygame.draw.polygon(c, colour, [(2, 8), (3, 3), (6, 1), (9, 3), (9, 8)])
		c.set_at((4, 4), (0, 0, 0, 0)); c.set_at((7, 6), (0, 0, 0, 0))
	elif element == 'psychic':
		pygame.draw.ellipse(c, colour, (0, 2, 10, 6)); pygame.draw.circle(c, (0, 0, 0, 0), (5, 5), 2); pygame.draw.circle(c, colour, (5, 5), 1)
	else:
		pygame.draw.circle(c, colour, (5, 5), 4, 2)
	return c

# A small coloured tag with the type's emblem and name, e.g. [flame FIRE]. Parameters: element, font, label.
# Iteration 32: the round type icons from the Openmon icon pack (falls back to the drawn emblem)
def type_icon(element, size = 16):
	key = ('type_icon', element, size)
	if key not in _cache:
		path = asset('graphics', 'type_icons', f'{element}.png')
		if exists(path):
			_cache[key] = pygame.transform.scale(pygame.image.load(path).convert_alpha(), (size, size))
		else:
			_cache[key] = pygame.transform.scale(type_emblem(element), (size, size))
	return _cache[key]

def type_chip(element, font, label):
	key = ('chip', element, label, id(font))
	if key not in _cache:
		text = font.render(label.upper(), False, (255, 255, 255))
		emblem = type_icon(element, 16)
		w, h = text.get_width() + 30, max(20, text.get_height() + 6)
		chip = pygame.Surface((w, h), pygame.SRCALPHA)
		colour = TYPE_COLOURS.get(element, (150, 150, 150))
		pygame.draw.rect(chip, colour, (0, 0, w, h), 0, 5)
		pygame.draw.rect(chip, tuple(int(c * 0.6) for c in colour), (0, 0, w, h), 2, 5)
		chip.blit(emblem, emblem.get_rect(midleft = (4, h / 2)))
		chip.blit(text, text.get_rect(midleft = (23, h / 2 + 1)))
		_cache[key] = chip
	return _cache[key]

# ---------- language flags ----------
def flag(language, size = (30, 20)):
	key = ('flag', language, size)
	if key not in _cache:
		w, h = 15, 10
		c = pygame.Surface((w, h))
		if language == 'it':
			for i, colour in enumerate(((0, 146, 70), (255, 255, 255), (206, 43, 55))):
				c.fill(colour, (i * 5, 0, 5, h))
		elif language == 'es':
			c.fill((198, 11, 30)); c.fill((255, 196, 0), (0, 3, w, 4))
		else:
			c.fill((1, 33, 105))
			pygame.draw.line(c, (255, 255, 255), (0, 0), (w, h), 3); pygame.draw.line(c, (255, 255, 255), (0, h), (w, 0), 3)
			pygame.draw.line(c, (200, 16, 46), (0, 0), (w, h), 1); pygame.draw.line(c, (200, 16, 46), (0, h), (w, 0), 1)
			c.fill((255, 255, 255), (6, 0, 3, h)); c.fill((255, 255, 255), (0, 3, w, 4))
			c.fill((200, 16, 46), (7, 0, 1, h)); c.fill((200, 16, 46), (0, 4, w, 2))
		surf = pygame.transform.scale(c, size)
		pygame.draw.rect(surf, OUTLINE, surf.get_rect(), 1)
		_cache[key] = surf
	return _cache[key]

# ---------- key caps for the control hints ----------
def key_cap(label, font):
	key = ('cap', label, id(font))
	if key not in _cache:
		text = font.render(label, False, (40, 38, 46))
		w, h = max(22, text.get_width() + 12), 22
		cap = pygame.Surface((w, h + 3), pygame.SRCALPHA)
		pygame.draw.rect(cap, (120, 116, 130), (0, 3, w, h), 0, 4)
		pygame.draw.rect(cap, (236, 236, 236), (0, 0, w, h), 0, 4)
		pygame.draw.rect(cap, (120, 116, 130), (0, 0, w, h), 1, 4)
		cap.blit(text, text.get_rect(center = (w / 2, h / 2 + 1)))
		_cache[key] = cap
	return _cache[key]

# ---------- medals for the top 3 on the Players screen ----------
def medal(place, size = 28):
	key = ('medal', place, size)
	if key not in _cache:
		colour = {1: (250, 210, 60), 2: (200, 205, 215), 3: (205, 130, 70)}[place]
		c = _canvas()
		pygame.draw.polygon(c, (60, 110, 220), [(4, 0), (7, 0), (8, 6), (5, 6)])
		pygame.draw.polygon(c, (220, 70, 70), [(9, 0), (12, 0), (11, 6), (8, 6)])
		pygame.draw.circle(c, colour, (8, 10), 5)
		pygame.draw.circle(c, tuple(int(v * 0.75) for v in colour), (8, 10), 3, 1)
		c.set_at((6, 8), (255, 255, 255))
		_cache[key] = pygame.transform.scale(_outlined(c), (size, size))
	return _cache[key]

# ---------- status effect icons (Iteration 21 uses these above the health bar) ----------
STATUS_COLOURS = {'burn': (240, 110, 40), 'freeze': (120, 210, 240), 'poison': (170, 80, 200), 'sleep': (150, 150, 200)}
def status_icon(status, size = 18):
	key = ('status', status, size)
	picture = pack_picture(f'status_{status}') if key not in _cache else None
	if picture:
		_cache[key] = pygame.transform.scale(picture, (size, size))
	if key not in _cache:
		c = _canvas(10)
		colour = STATUS_COLOURS.get(status, (200, 200, 200))
		pygame.draw.rect(c, colour, (0, 0, 10, 10), 0, 3)
		mark = {'burn': 'fire', 'freeze': 'ice', 'poison': 'poison'}.get(status)
		if mark:
			c.blit(pygame.transform.scale(type_emblem(mark), (8, 8)), (1, 1))
		else:
			for i, (x, y) in enumerate(((2, 6), (5, 3), (7, 1))):
				pygame.draw.line(c, (255, 255, 255), (x, y), (x + 2, y)); pygame.draw.line(c, (255, 255, 255), (x + 2, y), (x, y + 2)); pygame.draw.line(c, (255, 255, 255), (x, y + 2), (x + 2, y + 2))
		_cache[key] = pygame.transform.scale(c, (size, size))
	return _cache[key]

# ---------- trainer heads for the map (cut from their walking sprite) ----------
def trainer_head(frames, size = 22):
	key = ('head', id(frames), size)
	if key not in _cache:
		frame = frames['down'][0]
		bounds = frame.get_bounding_rect()
		head = frame.subsurface(pygame.Rect(bounds.left, bounds.top, bounds.width, min(bounds.height, int(bounds.width * 0.9)))).copy()
		_cache[key] = pygame.transform.smoothscale(head, (size, size))
	return _cache[key]
