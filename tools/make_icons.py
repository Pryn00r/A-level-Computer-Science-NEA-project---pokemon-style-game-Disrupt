# make_icons.py
# Iteration 19: draws the potion and ether bottle icons used for the Bag button in battle and next to
# items in lists. Drawn from text patterns in the same style as the other battle icons (32 x 32,
# dark outline, three shades of colour). The highlighted version has a white outline.
# Run with:  python tools/make_icons.py   (writes graphics/ui/potion*.png and ether*.png)

import os
from os.path import abspath, dirname, join
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame

UI_FOLDER = join(dirname(dirname(abspath(__file__))), 'graphics', 'ui')

BOTTLE = [
	'.....######.....',
	'.....#cccC#.....',
	'.....#cccC#.....',
	'....########....',
	'.....#gwgG#.....',
	'.....#gwgG#.....',
	'....##gwgG##....',
	'...#gwgggggG#...',
	'..#gwllllllmG#..',
	'..#gwllllllmG#..',
	'..#glllllmmdG#..',
	'..#gllllmmmdG#..',
	'..#GmmmmmmddG#..',
	'...#GddddddG#...',
	'....########....',
	'................',
]

LIQUIDS = {   # light, middle, dark shade of the liquid
	'potion': ((244, 86, 86), (208, 67, 67), (174, 49, 49)),     # red - health (same reds as the sword icon)
	'ether': ((119, 165, 245), (83, 120, 212), (53, 80, 190)),    # blue - energy
}

def draw(liquid, outline):
	light, middle, dark = LIQUIDS[liquid]
	colours = {'#': outline, 'c': (190, 140, 90), 'C': (140, 95, 60), 'g': (222, 232, 240), 'G': (160, 175, 196),
	           'w': (255, 255, 255), 'l': light, 'm': middle, 'd': dark}
	surf = pygame.Surface((16, 16), pygame.SRCALPHA)
	for y, row in enumerate(BOTTLE):
		assert len(row) == 16, row
		for x, cell in enumerate(row):
			if cell in colours:
				surf.set_at((x, y), colours[cell])
	return pygame.transform.scale(surf, (32, 32))

if __name__ == '__main__':
	pygame.init()
	for liquid in LIQUIDS:
		pygame.image.save(draw(liquid, (34, 32, 52)), join(UI_FOLDER, f'{liquid}.png'))
		pygame.image.save(draw(liquid, (255, 255, 255)), join(UI_FOLDER, f'{liquid}_highlight.png'))
	print('icons written to', UI_FOLDER)
