# import_packs.py
# Iteration 26 (trimmed in Iterations 27 and 31): copies the art the game uses out of the free asset packs (downloaded from itch.io) into
# the game's graphics folder, with simple file names, so the game never needs the original downloads.
# Run with:  python tools/import_packs.py "<folder that holds the unzipped packs>"
#
# Packs used (all free for games, with credit - see CREDITS in the game and README.md):
#   Shikashi's Fantasy Icons Pack v2 - Shikashi
#   Super Pixel Effects Gigapack (Free Version) - Will Tice / unTied Games
#   FREE 20+ VFX Pixel Art Asset Pack - ThePixelGame
#   Acid / Dark / Wood VFX 01-02, Fire Effect 2 (itch.io free VFX)

import os
import re
import sys
import shutil
from os.path import join, exists

from PIL import Image

PACKS = sys.argv[1] if len(sys.argv) > 1 else 'packs'
GAME = join(os.path.dirname(os.path.abspath(__file__)), '..')
GFX = join(GAME, 'graphics')

def find(*parts):
	path = join(PACKS, *parts)
	if not exists(path):
		raise FileNotFoundError(path)
	return path

ICONS = find("Shikashi's Fantasy Icons Pack v2", "Shikashi's Fantasy Icons Pack v2", '#1 - Transparent Icons.png')
GIGA = find('Super Pixel Effects Gigapack (Free Version) v3.2.0', 'Super Pixel Effects Gigapack (Free Version)', 'spritesheet')

def fresh(folder):
	path = join(GFX, folder)
	shutil.rmtree(path, ignore_errors = True)
	os.makedirs(path)
	return path

FRAME = 192

# ---------- 4. attack animations (one row of square frames, 192 x 192) ----------
def giga(group, effect, colour, size = 'large'):
	folder = join(GIGA, group, effect, f'{effect}_{size}_{colour}')
	sheet = Image.open(join(folder, 'spritesheet.png')).convert('RGBA')
	frames = []
	for line in open(join(folder, 'spritesheet.txt')):
		numbers = [int(n) for n in re.findall(r'\d+', line.split('=')[1])]
		x, y, w, h = numbers
		frames.append(sheet.crop((x, y, x + w, y + h)))
	return frames

def strip(path, frame_width, frame_height = None):
	sheet = Image.open(path).convert('RGBA')
	frame_height = frame_height or sheet.height
	return [sheet.crop((x, y, x + frame_width, y + frame_height)) for y in range(0, sheet.height, frame_height) for x in range(0, sheet.width, frame_width)]

def hue(frames, degrees):
	out = []
	for frame in frames:
		r, g, b, a = frame.split()
		h, s, v = Image.merge('RGB', (r, g, b)).convert('HSV').split()
		h = h.point(lambda value: (value + int(degrees * 255 / 360)) % 256)
		out.append(Image.merge('RGBA', (*Image.merge('HSV', (h, s, v)).convert('RGB').split(), a)))
	return out

def save_attack(name, frames, most = 10, fill = 0.9):
	if len(frames) > most:   # keep the animation short: evenly spaced frames
		frames = [frames[round(i * (len(frames) - 1) / (most - 1))] for i in range(most)]
	frames = [f for f in frames if f.getbbox()] or frames
	strip_image = Image.new('RGBA', (FRAME * len(frames), FRAME), (0, 0, 0, 0))
	biggest = max(max(f.width, f.height) for f in frames)
	scale = FRAME * fill / biggest
	for i, frame in enumerate(frames):
		big = frame.resize((max(1, int(frame.width * scale)), max(1, int(frame.height * scale))), Image.NEAREST)
		strip_image.alpha_composite(big, (i * FRAME + (FRAME - big.width) // 2, (FRAME - big.height) // 2))
	strip_image.save(join(GFX, 'attacks', f'{name}.png'))

def vfx(*parts):
	return find(*parts)

ATTACKS = {
	'tackle':   lambda: giga('Impacts', 'symmetrical_impact_001', 'yellow'),
	'quick':    lambda: giga('Fantasy Spells', 'spell_haste_001', 'green'),
	'growl':    lambda: giga('Magic Bursts', 'directional_music_burst_001', 'red'),
	'mega':     lambda: giga('Explosions', 'epic_explosion_002', 'yellow'),
	'ember':    lambda: giga('Fire', 'fire_looping_003B', 'orange'),
	'solar':    lambda: giga('Magic Bursts', 'round_light_burst_001', 'yellow'),
	'aqua':     lambda: giga('Impacts', 'symmetrical_impact_002', 'blue'),
	'soak':     lambda: hue(giga('Magic Bursts', 'directional_bubble_burst_001', 'green'), 90),
	'dive':     lambda: giga('Impacts', 'directional_impact_001', 'blue'),
	'seed':     lambda: strip(vfx('Wood VFX 01 - 02', 'Wood VFX 01 - 02', 'Wood VFX 01', 'Wood VFX 01 Hit.png'), 32),
	'spores':   lambda: giga('Fantasy Spells', 'spell_poison_001', 'green'),
	'frost':    lambda: giga('Lightning', 'lightning_aura_002', 'blue'),
	'shard':    lambda: giga('Magic Bursts', 'round_sparkle_burst_001', 'blue'),
	'blizzard': lambda: hue(giga('Magic Bursts', 'round_sparkle_burst_002', 'green'), 95),
	'acid':     lambda: strip(vfx('Acid VFX 01 - 02', 'Acid VFX 01 - 02', 'Acid VFX 1', 'Acid VFX 01.png'), 32),
	'venom':    lambda: giga('Fantasy Spells', 'status_poison_001', 'green'),
	'toxic':    lambda: giga('Fantasy Spells', 'spell_death_002', 'green'),
	'sting':    lambda: giga('Impacts', 'directional_impact_003', 'violet'),
	'silk':     lambda: giga('Smoke Bursts', 'directional_smoke_burst_001', 'white'),
	'swarm':    lambda: giga('Splatters', 'burst_splatter_003', 'green'),
	'bite':     lambda: giga('Splatters', 'directional_splatter_003', 'red'),
	'peck':     lambda: giga('Impacts', 'directional_impact_002', 'white'),
	'wing':     lambda: giga('Smoke Bursts', 'symmetrical_smoke_burst_001', 'brown'),
	'feather':  lambda: giga('Fantasy Spells', 'status_sparkling_001', 'yellow'),
	'horn':     lambda: giga('Impacts', 'directional_impact_004', 'yellow'),
	'mind':     lambda: strip(vfx('Dark VFX 01 - 02', 'Dark VFX 1', 'Dark VFX 1 (40x32).png'), 40),
	'hypno':    lambda: strip(vfx('Dark VFX 01 - 02', 'Dark VFX 2', 'Dark VFX 2 (48x64).png'), 48),
	'future':   lambda: giga('Fantasy Spells', 'spell_absorb_001', 'violet'),
	'blink':    lambda: giga('Sci-fi', 'scifi_warp_003', 'blue'),
	'glitch':   lambda: giga('Sci-fi', 'scifi_warp_002', 'red'),
	'heal_sparkle': lambda: giga('Fantasy Spells', 'spell_heal_001', 'red'),
}
def import_attacks():
	for name, make in ATTACKS.items():
		save_attack(name, make())
	print('attacks:', len(ATTACKS))

# ---------- 5. item and status icons (32 x 32 cells, 16 per row) ----------
ICON_CELLS = {
	'capture_orb': (18, 0), 'great_orb': (18, 1), 'prime_orb': (18, 3), 'debug_orb': (18, 2),
	'potion': (9, 0), 'ether': (9, 1), 'max_ether': (9, 9), 'party_heal': (9, 8), 'full_cure': (9, 10),
	'burn_heal': (9, 13), 'thaw_spray': (19, 5), 'antidote': (9, 2), 'wake_bell': (9, 14),
	'repel': (9, 3), 'escape_rope': (10, 13), 'illuminator': (10, 9),
	'power_band': (8, 4), 'vital_charm': (8, 6), 'focus_ring': (8, 5), 'wise_feather': (17, 10),
	'swift_scarf': (7, 9), 'guard_shell': (16, 10), 'lucky_coin': (12, 7), 'shiny_charm': (21, 0),
	'fishing_rod': (16, 0), 'shovel': (10, 3), 'swift_cap': (7, 0), 'snow_boots': (8, 3),
	'pearl': (17, 4), 'fossil': (16, 13), 'crystal': (12, 14), 'scrap': (17, 1), 'herb': (11, 15), 'egg': (15, 6),
	# menu and HUD icons that have a good match in the pack (ui_style.icon uses these)
	'ui_bag': (8, 9), 'ui_map': (13, 12), 'ui_book': (13, 0), 'ui_scroll': (13, 11), 'ui_coin': (12, 7), 'ui_heal': (9, 0),
	'ui_sword': (5, 1), 'ui_sun': (21, 8), 'ui_moon': (21, 10), 'ui_clock': (10, 15),
	# status effects and stat changes
	'status_burn': (0, 9), 'status_poison': (0, 1), 'status_sleep': (0, 7), 'status_freeze': (21, 13),
	'stat_up': (2, 0), 'stat_down': (2, 1),
}
def import_icons():
	out = fresh('item_icons')
	sheet = Image.open(ICONS).convert('RGBA')
	for name, (row, col) in ICON_CELLS.items():
		sheet.crop((col * 32, row * 32, col * 32 + 32, row * 32 + 32)).save(join(out, f'{name}.png'))
	# the battle menu's Bag button and the potion/ether pictures, with a white outline for the highlighted version
	for name in ('potion', 'ether'):
		icon = Image.open(join(out, f'{name}.png')).convert('RGBA')
		icon.save(join(GFX, 'ui', f'{name}.png'))
		outline = Image.new('RGBA', icon.size, (0, 0, 0, 0))
		alpha = icon.getchannel('A')
		for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
			white = Image.new('RGBA', icon.size, (255, 255, 255, 255))
			shifted = Image.new('L', icon.size, 0)
			shifted.paste(alpha, (dx, dy))
			outline.paste(white, (0, 0), shifted)
		outline.alpha_composite(icon)
		outline.save(join(GFX, 'ui', f'{name}_highlight.png'))
	print('icons:', len(ICON_CELLS))

if __name__ == '__main__':
	import_attacks()
	import_icons()
