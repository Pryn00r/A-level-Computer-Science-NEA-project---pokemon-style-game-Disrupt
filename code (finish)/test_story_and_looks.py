# test_story_and_looks.py
# Automated tests for the new game, the player's clothes colour and the monster storage box.
# Iteration 27: a new game starts with choosing a starter (no professor's lab) and the player is always the
# original trainer (only the clothes colour changes). Iteration 31: the house is empty again; the clothes
# colour and the monster box are in the menu.
# Run with:  python test_story_and_looks.py   (no window is opened; uses a temporary saves folder)

import os
import tempfile
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import save_system
from main import Game
from monster import Monster
from settings import MAX_PARTY_SIZE, asset
import looks
from localisation import t as menus_t

results = []
def check(name, expected, actual):
	results.append((name, expected, actual, expected == actual))

folder = tempfile.TemporaryDirectory()
game = Game()
game.profiles = save_system.ProfileManager(folder.name)
profile, _ = game.profiles.create('Tester', 'Blue#Sky2026', 'question_pet', 'Rex')
game.select_profile(profile)

# ---------- the player's look: the original trainer, recoloured ----------
original = game.overworld_frames['characters']['player']
check('the default look is the original trainer', original, looks.frames_for(game, looks.DEFAULT_LOOK))
check('looks from Iterations 22-26 become the original colours', [looks.DEFAULT_LOOK] * 4,
	[looks.validate(x) for x in ({'sheet': 'Male_01-1'}, {'parts': {}}, {'base': 'young_guy', 'hue': 40}, 'nonsense')])
check('a recolour of the original trainer is kept', {'hue': 180, 'gold': False}, looks.validate({'base': 'player', 'hue': 180}))
ocean = looks.frames_for(game, looks.COLOURS['ocean'])
check('a recoloured trainer has the same animations', set(original), set(ocean))
check('it keeps its see-through background', original['down'][0].get_at((0, 0)), ocean['down'][0].get_at((0, 0)))
check('its clothes change colour', True, pygame.image.tobytes(ocean['down'][0], 'RGBA') != pygame.image.tobytes(original['down'][0], 'RGBA'))
check('the player is never another character', True, all(looks.validate(look) == look for look in looks.COLOURS.values()))

# ---------- a new game ----------
game.start_new_game(1, 'Finsta', 'Splash')
check('a new game starts outside the house with the chosen starter', ('world', 'house', 'Finsta', 'Splash'),
	(game.current_map, game.current_spawn, game.player_monsters[0].name, game.player_monsters[0].nickname))
check('there is no professor and no lab', (False, False), ('lab' in game.tmx_maps, any(getattr(s, 'npc', False) for s in game.character_sprites)))
check('the new game is saved straight away', 'ok', game.saves.all_slots()[0]['status'])
check('the player looks like the original trainer', original, game.player.frames)

# ---------- the house (Iteration 31: empty again, like the original game) ----------
import importlib.util
game.change_map('house', 'world')
check('the house is empty: no furniture', (None, False), (importlib.util.find_spec('furniture'), hasattr(game, 'use_furniture')))
check('nobody is in the house', 0, len(game.character_sprites))
# the clothes colour and the monster box are in the menu instead
from game_screens import MainMenu
from story_screens import WardrobeScreen, StorageScreen
game.ui.clear()
game.ui.push(MainMenu(game.ui))
labels = [label for label, _ in game.ui.screens[-1].get_items()]
check('the menu has the Monster Box and Clothes', True, {menus_t('menu_box'), menus_t('menu_clothes')} <= set(labels))
game.ui.screens[-1].get_items()[labels.index(menus_t('menu_clothes'))][1]()
check('Clothes opens the colour choice', WardrobeScreen, type(game.ui.screens[-1]))
game.ui.screens[-1].choose('violet')
check('choosing a colour wears it', looks.COLOURS['violet'], game.look)
game.ui.pop()
game.ui.screens[-1].get_items()[labels.index(menus_t('menu_box'))][1]()
check('Monster Box opens the box', StorageScreen, type(game.ui.screens[-1]))
game.ui.clear()

# ---------- storage ----------
game.player_monsters.update({i: Monster('Pouch', 5) for i in range(1, MAX_PARTY_SIZE)})
game.storage.append(Monster('Atrox', 7))
game.move_storage(1, 0)
check('moving into a full party is refused', (MAX_PARTY_SIZE, 1), (len(game.player_monsters), len(game.storage)))
game.move_storage(0, 5)
check('a party monster can go into the box', (MAX_PARTY_SIZE - 1, 2), (len(game.player_monsters), len(game.storage)))
check('the party is renumbered with no gaps', list(range(MAX_PARTY_SIZE - 1)), sorted(game.player_monsters))
while len(game.player_monsters) > 1:
	game.move_storage(0, 0)
check('the last monster cannot be put away', 1, (game.move_storage(0, 0), len(game.player_monsters))[1])

# ---------- saving ----------
game.save_game(1)
game.storage = []
game.look = dict(looks.DEFAULT_LOOK)
game.load_game(1)
check('the colour and the storage box are saved and loaded', (looks.COLOURS['violet'], True), (game.look, len(game.storage) > 0))

folder.cleanup()
for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
