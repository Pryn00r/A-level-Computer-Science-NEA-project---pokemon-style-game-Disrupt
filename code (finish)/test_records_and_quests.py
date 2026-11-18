# test_records_and_quests.py
# Automated tests for Iteration 25b: achievements, the stats counters, daily and weekly quests, the
# speedrun time, index habitats and filters, the extra leaderboards and stopping an evolution.
# Run with:  python test_records_and_quests.py   (no window; uses a temporary saves folder)

import os
import tempfile
from datetime import date, timedelta
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import save_system
import records
from main import Game
from monster import Monster
from game_data import MONSTER_DATA

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

# ---------- achievements ----------
check('nothing is unlocked at the start', [], records.check(game))
game.counters['steps'] = 1000
coins = game.coins
check('walking 1000 tiles unlocks First Steps', ['first_steps'], records.check(game))
check('its reward is given', coins + 100, game.coins)
check('an achievement only unlocks once', [], records.check(game))
game.caught |= set(list(MONSTER_DATA)[:20])
records.check(game)
check('catching 20 species gives the Shiny Charm', 1, game.inventory.get('shiny_charm'))
check('the Shiny Charm triples the shiny chance', True, game.shiny_chance() > 0 and abs(game.shiny_chance() / 3 - __import__('settings').SHINY_CHANCE) < 1e-9)
game.story['finish_time'] = 3 * 60 * 60
check('finishing in 3 hours is not a speedrun', 0, records.progress(game, 'speedrun'))
game.story['finish_time'] = 90 * 60
check('finishing in 90 minutes is', 1, records.progress(game, 'speedrun'))
game.achievement_popups.clear()
game.check_quests()
check('a new achievement shows a pop-up', True, any(name == 'speedrunner' for name, _ in game.achievement_popups))
check('the speedrun time is shown to a tenth of a second', '1:02:03.4', records.format_time(3723.45))

# ---------- counters ----------
game.coins = 500
game.spend_coins(200)
check('spending coins is counted', 200, game.counters.get('spent'))
before = game.counters.get('steps', 0)
game.outdoors.walked(64 * 5)
check('walking is counted in whole tiles', before + 5, game.counters['steps'])

# ---------- daily and weekly quests ----------
day = date(2026, 11, 12)
check('3 daily quests a day', 3, len(records.daily_quests(day)))
check('the same quests all day', records.daily_quests(day), records.daily_quests(day))
check('different quests on another day', True, any(records.daily_quests(day + timedelta(days = n)) != records.daily_quests(day) for n in range(1, 4)))
check('the weekly quest is the same all week', records.weekly_quest(date(2026, 11, 9)), records.weekly_quest(date(2026, 11, 15)))
quest = 'daily:wins:3:150'
game.story.pop('daily', None)
game.counters['wins'] = 10
check('a daily quest only counts from the start of the day', 0, records.timed_progress(game, quest))
game.counters['wins'] = 12
check('it counts what happens today', 2, records.timed_progress(game, quest))
check('it cannot be claimed early', 'quest_not_done', records.claim_timed(game, quest))
game.counters['wins'] = 13
coins = game.coins
check('when done it can be claimed', ('quest_claimed', coins + 150), (records.claim_timed(game, quest), game.coins))
check('only once', 'quest_already', records.claim_timed(game, quest))
check('daily quests done are counted', 1, game.counters.get('dailies'))
game.story['daily']['key'] = '2000-01-01'
check('a new day starts again from zero', 0, records.timed_progress(game, quest))

# ---------- habitats ----------
check('Finsta: a starter (no fishing since Iteration 31)', (True, False), ('habitat_starter' in {key for key, _ in records.habitat('Finsta')}, 'habitat_fishing' in {key for key, _ in records.habitat('Finsta')}))
check('Draem also comes out at night in the forest', True, ('habitat_night', 'forest') in records.habitat('Draem'))
check('Charmadillo comes from evolving Cindrill', True, ('habitat_evolve', 'Cindrill') in records.habitat('Charmadillo'))
check('every monster has somewhere to be found', [], [n for n in MONSTER_DATA if not records.habitat(n)])

# ---------- index filters ----------
from info_screens import DexScreen
screen = DexScreen(game.ui)
screen.filter = screen.FILTERS.index('caught')
check('the Caught filter only shows caught monsters', True, all(name in game.caught for name in screen.shown()))
screen.filter = screen.FILTERS.index('water')
check('a type filter only shows seen monsters of that type', True, all(MONSTER_DATA[n]['stats']['element'] == 'water' and n in game.seen | game.caught for n in screen.shown()))

# ---------- stopping an evolution ----------
game.player_monsters = {0: Monster('Finsta', 40)}
game.evolution = None
game.check_evolution()
check('Finsta starts evolving at level 40', 'Gulfin', game.player_monsters[0].name)
game.cancel_evolution()
check('stopping it keeps Finsta', ('Finsta', None), (game.player_monsters[0].name, game.evolution))
game.check_evolution()
check('it does not try again at the same level', 'Finsta', game.player_monsters[0].name)
game.player_monsters[0].level = 41
game.check_evolution()
check('it tries again at the next level', 'Gulfin', game.player_monsters[0].name)
game.end_evolution()

# ---------- saving and leaderboards ----------
game.player_monsters = {0: Monster('Finsta', 20)}
game.player_monsters[0].declined = 20
game.save_game(1)
game.load_game(1)
check('the stopped evolution is saved', 20, game.player_monsters[0].declined)
board = game.profiles.leaderboard()[0]
check('the leaderboard has species, shinies and the fastest finish', (len(game.caught), 90 * 60), (board['caught'], board['finish']))
data = game.saves.read_slot(1)
data['party'][0]['declined'] = -3
try:
	save_system.deserialise_monster(data['party'][0])
	rejected = False
except ValueError:
	rejected = True
check('a save with a negative stopped-evolution level is rejected', True, rejected)

folder.cleanup()
for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
