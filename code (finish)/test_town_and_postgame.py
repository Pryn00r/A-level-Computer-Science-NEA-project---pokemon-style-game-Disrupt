# test_town_and_postgame.py
# Automated tests for Iteration 25c: happiness, fast travel, rematches, boss monsters, the Glitch Zone and
# local two-player battles. (Iteration 31 removed the daycare, crafting, move tutor, trading, bounties,
# phone calls, photo mode and the people around town - the tests check they are gone.) Run with:  python test_town_and_postgame.py   (no window; temporary saves folder)

import os
import tempfile
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import save_system
save_system.SAVE_ROOT = tempfile.mkdtemp()   # photos are written here, not in the real saves folder
import town
import postgame
from main import Game
from monster import Monster
from game_data import TRAINER_DATA, BADGE_DATA, ATTACK_DATA

results = []
def check(name, expected, actual):
	results.append((name, expected, actual, expected == actual))

folder = tempfile.TemporaryDirectory()
game = Game()
game.profiles = save_system.ProfileManager(folder.name)
profile, _ = game.profiles.create('Tester', 'Blue#Sky2026', 'question_pet', 'Rex')
game.select_profile(profile)
game.start_new_game(1, 'Finsta')
game.ui.clear()
game.player.unblock()
game.player_monsters.update({1: Monster('Cindrill', 10), 2: Monster('Pouch', 10)})

# ---------- Iteration 31: removed ----------
import importlib
import extra_screens
check('the people around town, daycare, crafting, tutor, trading and bounties are gone', [],
	[name for name in ('SIDE_NPCS', 'daycare', 'craft', 'teach', 'trade', 'bounties', 'update_calls') if hasattr(town, name)])
check('the phone calls and photo mode are gone', [], [name for name in ('PhoneScreen', 'PhotoScreen', 'TownScreen', 'DaycareScreen') if hasattr(extra_screens, name)])
check('nobody stands around town', [], [s.character_id for s in game.character_sprites if s.character_id.startswith('svc_')])

# ---------- happiness ----------
monster = Monster('Pouch', 10)
check('monsters start fairly happy', 50, monster.happiness)
monster.change_happiness(500)
check('happiness stops at 255', (255, True), (monster.happiness, monster.is_happy()))
data = save_system.serialise_monster(monster)
check('happiness and taught moves are saved', (255, []), (save_system.deserialise_monster(data).happiness, save_system.deserialise_monster(data).tutored))
data['tutored'] = ['nonsense move']
try:
	save_system.deserialise_monster(data)
	rejected = False
except ValueError:
	rejected = True
check('a save with an unknown taught move is rejected', True, rejected)

# ---------- fast travel ----------
game.change_map('world', 'hospital')
check('the three towns and the three gyms can be travelled to (Iteration 32)', ['house', 'hospital2', 'ruins', 'plant', 'fire', 'water'], list(town.visited(game)))

# ---------- post-game ----------
check('the Glitch Zone map exists', True, 'glitch' in game.tmx_maps)
game.counters.pop('ending', None)
leader = next(iter(BADGE_DATA))
TRAINER_DATA[leader]['defeated'] = True
sprite = type('S', (), {'character_id': leader, 'character_data': TRAINER_DATA[leader]})()
check('no rematches before the ending', False, postgame.rematch_ready(game, sprite))
game.counters['ending'] = 1
check('after the ending a beaten badge trainer offers a rematch', True, postgame.rematch_ready(game, sprite))
team = postgame.rematch_team(game, sprite)
check('the rematch team is at your level', min(100, game.party_level() + 2), team[0].level)
postgame.rematch_done(game, leader)
check('one rematch a day', False, postgame.rematch_ready(game, sprite))
game.change_map('glitch', 'entrance')
bosses = [s for s in game.character_sprites if TRAINER_DATA.get(s.character_id, {}).get('boss')]
check('three bosses wait in the Glitch Zone', 3, len(bosses))
postgame.make_boss(bosses[0])
boss = bosses[0].monsters[0]
check('a boss has three times the health', round(Monster(boss.name, boss.level).get_stat('max_health') * 3), round(boss.health))
postgame.boss_beaten(game, bosses[0].character_id)
game.change_map('glitch', 'entrance')
check('a beaten boss does not come back', 2, len([s for s in game.character_sprites if TRAINER_DATA.get(s.character_id, {}).get('boss')]))
monsters = postgame.glitch_monsters(game)
check('Glitch Zone monsters are strong', True, all(postgame.GLITCH_LEVELS[0] <= m.level <= postgame.GLITCH_LEVELS[1] for m in monsters.values()))
game.story['glitch_steps'] = 1
game.transition_target = None
postgame.glitch_walk(game, 2)
check('walking in the Glitch Zone starts wild battles anywhere', 'Battle', type(game.transition_target).__name__)
game.transition_target = None

# ---------- local two-player battles ----------
from battle import Battle
battle = Battle({0: Monster('Finsta', 30)}, {0: Monster('Sparchu', 30)}, game.monster_frames, game.bg_frames['forest'], game.fonts, lambda c, lost = False: None, None, game.audio, {}, False, None)
battle.versus = True
p2 = battle.opponent_sprites.sprites()[0]
p2.monster.initiative = 100
for sprite in battle.player_sprites:
	sprite.monster.initiative = 0
battle.check_active()
check("on player 2's turn they get the menu", ('opponent', 'general'), (battle.acting_side(), battle.selection_mode))
check('and the sides are swapped so their attacks hit player 1', True, p2 in battle.player_sprites)
check('the menu opens on the left of a monster on the right', True, battle.place_menu(pygame.FRect(0, 0, 100, 50)).right < p2.rect.left)
battle.current_monster, battle.selection_mode = None, None
battle.update(0.016)
check('after the turn the sides go back', True, p2 in battle.opponent_sprites)


for trainer in TRAINER_DATA.values():
	trainer['defeated'] = False
folder.cleanup()
for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
