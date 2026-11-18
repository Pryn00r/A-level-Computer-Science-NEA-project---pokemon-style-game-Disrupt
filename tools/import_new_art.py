# import_new_art.py
# Iteration 32: copies the new art into the game's graphics folder.
#   From "New folder":
#     03.png  - the spinning loading icon (middle row, 5 frames)          -> graphics/ui_pack/spinner_N.png
#     01.png  - the badge gems (red, green, blue and grey)               -> graphics/badges/gem_COLOUR.png
#     05.png  - the segmented bar (bottom row) for the battle turn bar   -> graphics/ui_pack/turnbar_full/empty.png
#     OpenmonItemIcons.png - item icons and the round type icons         -> graphics/item_icons/, graphics/type_icons/
#     32x32/  - menu icons and the controller buttons (A, B, X, Y)       -> graphics/item_icons/ui_NAME.png, graphics/ui_pack/pad_N.png
#     32x32 Unit Auras..., 32x48 Pillars..., 48x48 Area Blasts...       -> new attack animations
#   From the packs folder: the Super Pixel Effects Gigapack, Acid VFX, Dark VFX, Fire Effect 2 and Plants packs
#   for more attack animations (graphics/attacks/NAME.png - one row of 192 x 192 frames, like the others).
# Run with:  python tools/import_new_art.py "<New folder>" "<folder with the unzipped packs>"

import os
import re
import sys
from PIL import Image

NEW = sys.argv[1] if len(sys.argv) > 1 else 'New folder'
PACKS = sys.argv[2] if len(sys.argv) > 2 else 'packs'
GAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
GFX = os.path.join(GAME, 'graphics')
FRAME = 192

def out(*parts):
	path = os.path.join(GFX, *parts)
	os.makedirs(os.path.dirname(path), exist_ok = True)
	return path

def open_rgba(*parts):
	return Image.open(os.path.join(*parts)).convert('RGBA')

def trimmed(image):
	box = image.getbbox()
	return image.crop(box) if box else image

# ---------- interface pictures ----------
def import_ui():
	sheet = open_rgba(NEW, '03.png')
	for n in range(5):
		sheet.crop((n * 48, 48, n * 48 + 48, 96)).save(out('ui_pack', f'spinner_{n}.png'))
	gems = open_rgba(NEW, '01.png')
	for colour, x in (('red', 85), ('green', 133), ('blue', 181), ('grey', 229)):
		gems.crop((x, 55, x + 38, 89)).save(out('badges', f'gem_{colour}.png'))
	# Iteration 35: every part of the badge art - the wings and the outline frame as well as the gem
	for colour, y in (('grey', 0), ('blue', 33), ('green', 65), ('red', 97)):
		trimmed(gems.crop((0, y, 80, y + 30))).save(out('badges', f'wing_{colour}.png'))
	for colour, x in (('red', 80), ('green', 128), ('blue', 176), ('grey', 224)):
		trimmed(gems.crop((x, 0, x + 48, 50))).save(out('badges', f'frame_{colour}.png'))
	bar = open_rgba(NEW, '05.png')
	bar.crop((0, 20, 47, 28)).save(out('ui_pack', 'turnbar_full.png'))
	bar.crop((240, 20, 287, 28)).save(out('ui_pack', 'turnbar_empty.png'))
	for button in 'abxy':
		open_rgba(NEW, '32x32', f'button_xbox_{button}.png').save(out('ui_pack', f'pad_{button}.png'))
	print('interface pictures done')

# menu icon name (ui_style.icon) -> file in the 32x32 icon pack
MENU_ICONS = {'person': 'party', 'map': 'map', 'badge': 'star', 'book': 'book', 'scroll': 'script', 'trophy': 'shield',
              'save': 'disk_save', 'bag': 'inventory', 'settings': 'settings_gear', 'door': 'exit', 'chest': 'chest', 'clothes': 'character',
              'monsters': 'enemy', 'box': 'package', 'hourglass': 'hourglass'}   # Iteration 33: no repeated icons in the menu
def import_menu_icons():
	for name, source in MENU_ICONS.items():
		open_rgba(NEW, '32x32', f'{source}.png').save(out('item_icons', f'ui_{name}.png'))
	print('menu icons:', len(MENU_ICONS))

# ---------- Openmon item and type icons (32 x 32 cells; the type icons are 16 x 16 along the bottom) ----------
ITEMS = {'potion': (7, 7), 'ether': (6, 7), 'max_ether': (6, 2), 'party_heal': (9, 2), 'full_cure': (8, 2),
         'burn_heal': (3, 2), 'thaw_spray': (2, 2), 'antidote': (1, 2), 'wake_bell': (2, 5),
         'power_band': (0, 5), 'vital_charm': (8, 1), 'focus_ring': (5, 6), 'wise_feather': (1, 3),
         'swift_scarf': (6, 6), 'guard_shell': (6, 5), 'illuminator': (7, 6), 'shiny_charm': (8, 6)}
TYPES = {'normal': 0, 'fire': 1, 'water': 2, 'plant': 3, 'bug': 4, 'poison': 5, 'rock': 7, 'psychic': 9, 'flying': 14, 'ice': 17,
         'ghost': 8, 'dark': 10, 'fairy': 13}   # Iteration 35
def import_icons():
	sheet = open_rgba(NEW, 'OpenmonItemIcons.png')
	for name, (column, row) in ITEMS.items():
		sheet.crop((column * 32, row * 32, column * 32 + 32, row * 32 + 32)).save(out('item_icons', f'{name}.png'))
	for name, column in TYPES.items():
		sheet.crop((column * 16, 256, column * 16 + 16, 272)).save(out('type_icons', f'{name}.png'))
	confused = open_rgba(NEW, '32x32 Unit Auras, Casts & Status', 'Confused', '32x32 Side Scroller TD Unit Auras, Casts & Status-Confused_Effect.png')
	trimmed(confused.crop((64, 0, 96, 32))).save(out('item_icons', 'status_confused.png'))
	print('item icons:', len(ITEMS), 'type icons:', len(TYPES))

# ---------- attack animations ----------
def strip(path, width, height = None, y = 0, count = None):
	sheet = Image.open(path).convert('RGBA')
	height = height or sheet.height
	frames = [sheet.crop((x, y, x + width, y + height)) for x in range(0, sheet.width - width + 1, width)]
	return frames[:count] if count else frames

def giga(group, effect, colour, size = 'large'):
	root = os.path.join(PACKS, 'Super Pixel Effects Gigapack (Free Version) v3.2.0', 'Super Pixel Effects Gigapack (Free Version)', 'spritesheet')
	folder = os.path.join(root, group, effect, f'{effect}_{size}_{colour}')
	if not os.path.isdir(folder):   # pick whichever colour the free version has
		options = sorted(name for name in os.listdir(os.path.join(root, group, effect)) if f'_{size}_' in name)
		folder = os.path.join(root, group, effect, options[0])
	sheet = Image.open(os.path.join(folder, 'spritesheet.png')).convert('RGBA')
	frames = []
	for line in open(os.path.join(folder, 'spritesheet.txt')):
		x, y, w, h = [int(n) for n in re.findall(r'\d+', line.split('=')[1])]
		frames.append(sheet.crop((x, y, x + w, y + h)))
	return frames

def tint(frames, colour):
	out_frames = []
	for frame in frames:
		r, g, b, a = frame.split()
		grey = Image.merge('RGB', (r, g, b)).convert('L')
		coloured = Image.merge('RGB', [grey.point(lambda v, c = c: int(v * c / 255)) for c in colour])
		out_frames.append(Image.merge('RGBA', (*coloured.split(), a)))
	return out_frames

def save_attack(name, frames, most = 12, fill = 0.9):
	if len(frames) > most:
		frames = [frames[round(i * (len(frames) - 1) / (most - 1))] for i in range(most)]
	frames = [f for f in frames if f.getbbox()] or frames
	# cut away the empty space shared by every frame, so small effects are not drawn tiny
	boxes = [f.getbbox() for f in frames]
	union = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
	frames = [f.crop(union) for f in frames]
	sheet = Image.new('RGBA', (FRAME * len(frames), FRAME), (0, 0, 0, 0))
	biggest = max(max(f.width, f.height) for f in frames)
	scale = FRAME * fill / biggest
	for i, frame in enumerate(frames):
		big = frame.resize((max(1, int(frame.width * scale)), max(1, int(frame.height * scale))), Image.NEAREST)
		sheet.alpha_composite(big, (i * FRAME + (FRAME - big.width) // 2, (FRAME - big.height) // 2))
	sheet.save(out('attacks', f'{name}.png'))

def plant_row(y0, y1, count, width = 96):
	sheet = open_rgba(PACKS, 'Plants', 'PlantAlternate.png')
	return [sheet.crop((n * width, y0, n * width + width, y1)) for n in range(count)]

def grass_growth():
	sheet = open_rgba(PACKS, 'Plants', 'PlantAlternate.png')
	return [sheet.crop((x, 0, x + 32, 32)) for x in range(576, 768, 32)]

def vertical(path, height):
	sheet = Image.open(path).convert('RGBA')
	return [sheet.crop((0, y, sheet.width, y + height)) for y in range(0, sheet.height - height + 1, height)]

def new_folder(*parts):
	return os.path.join(NEW, *parts)

ATTACKS = {
	# from the new folder
	'heal_aura':     lambda: strip(new_folder('32x32 Unit Auras, Casts & Status', 'Heal', '32x32 Side Scroller TD Unit Auras, Casts & Status-Heal_Effect.png'), 32),
	'confused':      lambda: strip(new_folder('32x32 Unit Auras, Casts & Status', 'Confused', '32x32 Side Scroller TD Unit Auras, Casts & Status-Confused_Effect.png'), 32),
	'fire_pillar':   lambda: strip(new_folder('32x48 Pillars & Skyfalls', '32x48 Side Scroller TD Pillars & Skyfalls-Fire_Column_Effect.png'), 32),
	'thunder':       lambda: strip(new_folder('32x48 Pillars & Skyfalls', '32x48 Side Scroller TD Pillars & Skyfalls-Blue_Lightning_Effect.png'), 32),
	'acid_pool':     lambda: strip(new_folder('48x48 Area Blasts & Ground Fields', 'Acid Pool', '48x48 Side Scroller TD Area Blasts & Ground Fields-Acid_Pool_Effect.png'), 48),
	'acid_spray':    lambda: vertical(os.path.join(PACKS, 'Acid VFX 01 - 02', 'Acid VFX 01 - 02', 'Acid VFX 2', 'Acid VFX 02Repeatable.png'), 32)
	                         + vertical(os.path.join(PACKS, 'Acid VFX 01 - 02', 'Acid VFX 01 - 02', 'Acid VFX 2', 'Acid VFX 02Ending.png'), 32),
	'inferno':       lambda: strip(os.path.join(PACKS, 'Fire Effect 2', 'Fire Effect 2', 'Explosion 2 SpriteSheet.png'), 48),
	# from the Gigapack
	'static':        lambda: giga('Lightning', 'lightning_burst_001', 'yellow'),
	'storm':         lambda: giga('Lightning', 'lightning_strike_001', 'blue'),
	'nightmare':     lambda: giga('Smoke Bursts', 'stylized_skull_smoke_burst_001', 'violet'),
	'dark_pulse':    lambda: giga('Fantasy Spells', 'spell_death_001', 'violet'),
	'confuse_ray':   lambda: giga('Sci-fi', 'scifi_warp_001', 'violet'),
	'power_up':      lambda: giga('Fantasy Spells', 'spell_attack_up_001', 'red'),
	'guard_up':      lambda: giga('Fantasy Spells', 'spell_defense_up_001', 'blue'),
	'glare':         lambda: giga('Symbols', 'symbol_alert_001', 'red'),
	# from the Plants pack
	'vine':          lambda: plant_row(130, 232, 11),
	'petal':         lambda: plant_row(225, 300, 14),
	'grass_grow':    lambda: grass_growth(),
}

# ---------- Iteration 33: every animation left in the packs gets a move ----------
def grid(path, size):
	sheet = Image.open(path).convert('RGBA')
	return [sheet.crop((x, y, x + size, y + size)) for y in range(0, sheet.height - size + 1, size) for x in range(0, sheet.width - size + 1, size)]

def pack(*parts):
	return os.path.join(PACKS, *parts)

def hue(frames, degrees):
	result = []
	for frame in frames:
		r, g, b, a = frame.split()
		h, s, v = Image.merge('RGB', (r, g, b)).convert('HSV').split()
		h = h.point(lambda value: (value + int(degrees * 255 / 360)) % 256)
		result.append(Image.merge('RGBA', (*Image.merge('HSV', (h, s, v)).convert('RGB').split(), a)))
	return result

ATTACKS_33 = {
	# Gigapack (the "mega" pack)
	'body_slam':    lambda: giga('Impacts', 'symmetrical_impact_003', 'yellow'),
	'hyper_blast':  lambda: giga('Explosions', 'epic_explosion_001', 'yellow'),
	'coin_toss':    lambda: giga('Magic Bursts', 'directional_coin_burst_001', 'yellow'),
	'sing':         lambda: giga('Magic Bursts', 'directional_music_burst_002', 'violet'),
	'charm':        lambda: giga('Magic Bursts', 'round_heart_burst_001', 'red'),
	'focus':        lambda: giga('Sci-fi', 'scifi_charge_up_001', 'yellow'),
	'scary_face':   lambda: giga('Symbols', 'symbol_warning_001', 'red'),
	'taunt':        lambda: giga('Symbols', 'symbol_thumbs_down_001', 'red'),
	'smoke':        lambda: giga('Smoke Bursts', 'looping_smoke_burst_001', 'white'),
	'agility':      lambda: giga('Sci-fi', 'scifi_heartbeat_fast_001', 'green'),
	'riddle':       lambda: giga('Symbols', 'symbol_question_001', 'yellow'),
	'war_cry':      lambda: giga('Symbols', 'symbol_attack_up_001', 'red'),
	'flame_wheel':  lambda: giga('Fire', 'fire_looping_003A', 'orange'),
	'blue_flame':   lambda: hue(giga('Fire', 'fire_looping_004A', 'orange'), 180),   # the free pack has one colour of each, so some are recoloured
	'heat_wave':    lambda: giga('Fire', 'fire_looping_004B', 'orange'),
	'flame_burst':  lambda: giga('Explosions', 'stylized_explosion_001', 'orange'),
	'firework':     lambda: giga('Magic Bursts', 'round_firework_burst_001', 'orange'),
	'spark_shower': lambda: giga('Sci-fi', 'scifi_spark_burst_001', 'yellow'),
	'water_gun':    lambda: hue(giga('Sci-fi', 'scifi_muzzle_flash_001', 'yellow'), 170),
	'geyser':       lambda: hue(giga('Explosions', 'symmetrical_explosion_002', 'orange'), 180),
	'mud_bomb':     lambda: tint(giga('Splatters', 'burst_splatter_001', 'red'), (190, 130, 70)),
	'ink_spray':    lambda: hue(giga('Splatters', 'directional_splatter_001', 'red'), 270),
	'ice_burst':    lambda: hue(giga('Explosions', 'symmetrical_explosion_001', 'orange'), 165),
	'diamond_dust': lambda: giga('Magic Bursts', 'round_sparkle_burst_003', 'blue'),
	'seed_cannon':  lambda: hue(giga('Sci-fi', 'scifi_muzzle_flash_003', 'yellow'), 70),
	'toxic_bomb':   lambda: hue(giga('Explosions', 'symmetrical_explosion_004', 'orange'), 250),
	'leech_bite':   lambda: hue(giga('Splatters', 'directional_splatter_006', 'red'), 100),
	'rock_slide':   lambda: tint(giga('Explosions', 'stylized_explosion_002', 'violet'), (215, 165, 110)),
	'rock_smash':   lambda: tint(giga('Impacts', 'symmetrical_impact_006', 'yellow'), (210, 160, 100)),
	'sandstorm':    lambda: giga('Smoke Bursts', 'looping_smoke_burst_002', 'brown'),
	'iron_wall':    lambda: giga('Symbols', 'symbol_defense_up_001', 'blue'),
	'zap_peck':     lambda: hue(giga('Lightning', 'lightning_burst_002', 'violet'), 150),
	'thunder_wave': lambda: hue(giga('Lightning', 'lightning_burst_003', 'violet'), 150),
	'psy_nova':     lambda: hue(giga('Explosions', 'stylized_explosion_003', 'yellow'), 250),
	'star_burst':   lambda: hue(giga('Magic Bursts', 'round_firework_burst_002', 'yellow'), 270),
	'slow_pulse':   lambda: hue(giga('Sci-fi', 'scifi_heartbeat_slow_001', 'green'), 150),
	'doom_pulse':   lambda: giga('Sci-fi', 'scifi_heartbeat_flatline_001', 'red'),
	'calm_mind':    lambda: giga('Symbols', 'symbol_magic_up_001', 'violet'),
	# the other packs
	'wood_hammer':  lambda: strip(pack('Wood VFX 01 - 02', 'Wood VFX 01 - 02', 'Wood VFX 02', 'Wood VFX 02.png'), 32),
	'root_bind':    lambda: strip(pack('Wood VFX 01 - 02', 'Wood VFX 01 - 02', 'Wood VFX 01', 'Wood VFX 01 Repeatable.png'), 32),
	'fire_blast':   lambda: grid(pack('Fire Effect 2', 'Fire Effect 2', 'Explosion SpriteSheet.png'), 64),
}

def import_attacks():
	for name, make in ATTACKS.items():
		save_attack(name, make())
	print('attacks:', len(ATTACKS))
	for name, make in ATTACKS_33.items():
		save_attack(name, make())
	print('Iteration 33 attacks:', len(ATTACKS_33))
	print('attacks:', len(ATTACKS))

# ---------- Iteration 34: moves that shared an animation each get their own version ----------
# (made from the shared picture with a new colour, so no two moves look the same)
def existing(name):
	sheet = Image.open(os.path.join(GFX, 'attacks', f'{name}.png')).convert('RGBA')
	return [sheet.crop((x, 0, x + FRAME, FRAME)) for x in range(0, sheet.width, FRAME)]

def mirrored(frames):
	return [frame.transpose(Image.FLIP_LEFT_RIGHT) for frame in frames]

VARIANTS = {
	'spark':       lambda: tint(existing('fire'), (255, 235, 120)),           # yellow sparks
	'burn':        lambda: mirrored(hue(existing('fire'), 330)),             # deep red flames
	'annihilate':  lambda: hue(existing('explosion'), 250),                  # a violet blast
	'bubble':      lambda: tint(existing('splash'), (190, 240, 255)),        # pale bubbles
	'tidal_wave':  lambda: mirrored(hue(existing('splash'), 20)),            # a deep blue wave
	'rock_throw':  lambda: tint(existing('horn'), (205, 160, 110)),          # brown rocks
}

# Iteration 35: Solar Beam drawn from scratch - a column of sunlight crashes down onto the target with a
# burst of rays where it lands, then fades. (The old light burst was small and hard to tell apart.)
def solar_beam_frames(count = 12, size = 96):
	from PIL import ImageDraw
	import math
	frames = []
	for i in range(count):
		t = i / (count - 1)
		frame = Image.new('RGBA', (size, size), (0, 0, 0, 0))
		draw = ImageDraw.Draw(frame)
		grow = min(1, t / 0.35)                       # the beam comes down...
		fade = 1 if t < 0.7 else (1 - t) / 0.3        # ...and fades at the end
		bottom = int(18 + 60 * grow)
		width = int(8 + 14 * min(1, t / 0.5))
		cx = size // 2
		for layer, (colour, extra) in enumerate((((255, 200, 40), 8), ((255, 236, 120), 3), ((255, 255, 230), -3))):
			w = max(2, width + extra)
			draw.rectangle((cx - w // 2, 0, cx + w // 2, bottom), fill = colour + (int(230 * fade),))
		if t > 0.3:   # where it lands: rays and a glowing ball
			burst = min(1, (t - 0.3) / 0.3)
			radius = int(10 + 22 * burst)
			for ray in range(12):
				angle = ray * math.pi / 6 + t * 1.5
				x2, y2 = cx + math.cos(angle) * radius * 1.5, bottom + math.sin(angle) * radius * 0.9
				draw.line((cx, bottom, x2, y2), fill = (255, 220, 80, int(200 * fade)), width = 3)
			draw.ellipse((cx - radius, bottom - radius * 0.6, cx + radius, bottom + radius * 0.6), fill = (255, 240, 150, int(220 * fade)))
			draw.ellipse((cx - radius // 2, bottom - radius * 0.3, cx + radius // 2, bottom + radius * 0.3), fill = (255, 255, 240, int(250 * fade)))
		for spark in range(10):   # little sparkles falling with the beam
			sy = (spark * 23 + i * 9) % max(1, bottom)
			sx = cx + ((spark * 37) % 31 - 15) * (1 + t)
			draw.rectangle((sx, sy, sx + 2, sy + 2), fill = (255, 255, 255, int(255 * fade)))
		frames.append(frame)
	return frames

# Iteration 35: Dark Pulse drawn from scratch - a black and violet orb swells, then bursts in rings and spikes
def dark_pulse_frames(count = 12, size = 96):
	from PIL import ImageDraw
	import math
	frames = []
	cx = cy = size // 2
	for i in range(count):
		t = i / (count - 1)
		frame = Image.new('RGBA', (size, size), (0, 0, 0, 0))
		draw = ImageDraw.Draw(frame)
		fade = 1 if t < 0.75 else (1 - t) / 0.25
		core = 6 + 16 * min(1, t / 0.4) - (10 * max(0, t - 0.6))
		for ring in range(3):   # shock rings rushing outward
			r = (t * 1.6 - ring * 0.18) * size * 0.5
			if 4 < r < size * 0.5:
				draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline = (170, 90, 255, int(220 * fade * (1 - r / (size * 0.5)))), width = 3)
		if t > 0.25:   # spikes
			for spike in range(10):
				angle = spike * math.pi / 5 + 0.3
				length = core + (8 + 22 * min(1, (t - 0.25) / 0.3)) * (1.2 if spike % 2 else 0.8)
				tip = (cx + math.cos(angle) * length, cy + math.sin(angle) * length)
				side = (math.cos(angle + math.pi / 2) * 3, math.sin(angle + math.pi / 2) * 3)
				draw.polygon([(cx + side[0], cy + side[1]), tip, (cx - side[0], cy - side[1])], fill = (110, 40, 180, int(230 * fade)))
		draw.ellipse((cx - core - 4, cy - core - 4, cx + core + 4, cy + core + 4), fill = (140, 70, 230, int(200 * fade)))
		draw.ellipse((cx - core, cy - core, cx + core, cy + core), fill = (25, 10, 40, int(255 * fade)))
		draw.ellipse((cx - core * 0.4, cy - core * 0.4, cx + core * 0.4, cy + core * 0.4), fill = (200, 150, 255, int(200 * fade)))
		frames.append(frame)
	return frames

def import_variants():
	save_attack('solar_beam', solar_beam_frames(), fill = 0.95)
	for name, make in VARIANTS.items():
		try:
			save_attack(name, make(), fill = 0.95)
		except FileNotFoundError:   # (Iteration 35: the source pictures of removed moves were deleted)
			pass
	print('variants:', len(VARIANTS))

if __name__ == '__main__':
	import_ui()
	import_menu_icons()
	import_icons()
	import_attacks()
	import_variants()
