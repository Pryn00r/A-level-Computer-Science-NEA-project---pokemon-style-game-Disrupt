# test_monsters.py
# Automated tests for Iteration 27, which took the game back to only the 16 original monsters (the ones
# added in Iterations 23-26, including Codeus, were removed), and Iteration 31, which removed the rival.
# Run with:  python test_monsters.py   (no window is opened)

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from game_data import MONSTER_DATA, WILD_ENCOUNTERS, NIGHT_ENCOUNTERS, TRAINER_DATA, QUEST_DATA, CAPTURE_ORB_DATA, current_name
from settings import asset
from monster import Monster
from save_system import deserialise_monster, serialise_monster
from main import Game

results = []
def check(name, expected, actual):
	results.append((name, expected, actual, expected == actual))

ORIGINAL = ('Plumette', 'Ivieron', 'Pluma', 'Sparchu', 'Cindrill', 'Charmadillo', 'Finsta', 'Gulfin', 'Finiette',
            'Atrox', 'Pouch', 'Draem', 'Larvea', 'Cleaf', 'Jacana', 'Friolera')
REMOVED = ('Venofrog', 'Toxitoad', 'Mothlit', 'Chirpi', 'Galeon', 'Mindle', 'Cerebloom', 'Frostbun', 'Glacihare', 'Codeus',
           'Gloop', 'Toxwraith', 'Gremlit', 'Puffghost', 'Galewraith', 'Hexie', 'Hexmage', 'Frostie', 'Glacigolem')

# ---------- only the original monsters ----------
check('exactly the 16 original monsters', sorted(ORIGINAL), sorted(MONSTER_DATA))
check('every species has a sprite sheet and an icon', [], [n for n in MONSTER_DATA if not (os.path.exists(asset('graphics', 'monsters', n + '.png')) and os.path.exists(asset('graphics', 'icons', n + '.png')))])
check('no pictures left for removed monsters', [], [n for n in REMOVED if os.path.exists(asset('graphics', 'monsters', n + '.png'))])
wild = {name for zone in WILD_ENCOUNTERS.values() for name in zone['monsters']} | {name for names in NIGHT_ENCOUNTERS.values() for name in names}
check('only original monsters in the wild', [], sorted(wild - set(ORIGINAL)))
check('the Debug Orb is gone', False, 'debug_orb' in CAPTURE_ORB_DATA)
check('the "catch them all" quest counts the 16 species', 16, QUEST_DATA['complete_dex']['target'])
check('a removed monster in an old save becomes an original one of the same type', ('Atrox', 'Friolera', 'Draem'), (current_name('Venofrog'), current_name('Glacigolem'), current_name('Codeus')))
data = serialise_monster(Monster('Pouch', 12))
data['name'] = 'Hexie'
loaded = deserialise_monster(data)
check('so an old save still loads', ('Draem', 12), (loaded.name, loaded.level))

# ---------- Iteration 31: the rival was removed ----------
import importlib.util
check('there is no rival any more', (None, False), (importlib.util.find_spec('rival'), 'rival' in TRAINER_DATA))
game = Game()
game.reset_progress()
game.player_monsters = {0: Monster('Finsta', 8)}
game.change_map('world', 'house')
check('nobody extra appears in the world (Codeus and the rival were removed)', False, any(s.character_id in ('codeus', 'rival') for s in game.character_sprites))

for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
