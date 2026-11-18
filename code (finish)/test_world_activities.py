# test_world_activities.py
# Automated tests for Iteration 25a: day and night, night-only monsters, Party Heal, the last hospital,
# the growing shop, the daily deal and the new held items. (Iteration 31 removed fishing, digging, hidden
# items, Repel, Escape Rope and selling materials - the tests check they are gone.) Run with:  python test_world_activities.py   (no window; uses a temporary saves folder)

import os
import tempfile
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import save_system
import outdoors
from main import Game
from monster import Monster
from game_data import NIGHT_ONLY, NIGHT_ENCOUNTERS, SHOP_UNLOCK, MATERIALS, TRAINER_DATA, BADGE_DATA, SHOP_PRICES, DAILY_DISCOUNT

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

# ---------- day and night ----------
check('midday is fully light', 0.0, outdoors.darkness(12))
check('midnight is fully dark', 1.0, outdoors.darkness(0))
check('dusk is half way', 0.5, outdoors.darkness(19.5))
check('20:00 to 6:00 is night', (True, True, False), (outdoors.is_night(21), outdoors.is_night(3), outdoors.is_night(6)))
game.outdoors.set_hour(23.9)
game.outdoors.update(10 * outdoors.MINUTES_PER_HOUR / 60, True)   # 10 game minutes
check('the clock wraps round past midnight', True, game.outdoors.hour < 1)
check('the clock shows hours and minutes', '00:00', game.outdoors.clock_text())

class Patch:
	def __init__(self, biome):
		self.biome, self.monsters, self.level = biome, [], 5
game.outdoors.set_hour(12)
day = {m.name for _ in range(300) for m in game.create_wild_monsters(Patch('forest')).values()}
game.outdoors.set_hour(23)
night = {m.name for _ in range(300) for m in game.create_wild_monsters(Patch('forest')).values()}
check('night-only monsters never appear in the day', set(), day & set(NIGHT_ONLY))
check('night brings extra monsters', True, set(NIGHT_ENCOUNTERS['forest']) <= night)

# ---------- Iteration 31: fishing, digging, hidden items, Repel and Escape Rope were removed ----------
import game_data
check('those items are gone', [], [name for name in game_data.REMOVED_ITEMS if name in game_data.ITEM_DATA or name in SHOP_PRICES or name in game_data.KEY_ITEMS])
check('the Space key does nothing extra in the world (only talking)', False, hasattr(game.outdoors, 'interact'))
game.player_monsters[0].level = 20
game.inventory.update({'repel': 3, 'fishing_rod': 1, 'pearl': 2})
game.save_game(1)
game.load_game(1)
check('removed items in an old save are dropped when it loads', [], [name for name in ('repel', 'fishing_rod', 'pearl') if name in game.inventory])

# ---------- hospitals and Party Heal ----------
check('before healing anywhere you go back home', ('world', 'house'), game.respawn_point())
game.change_map('hospital', 'world')
nurse = next(s for s in game.character_sprites if s.nurse)
game.end_dialog(nurse)
game.ui.clear()
check('after healing at a hospital you come back there', ('hospital', 'world'), game.respawn_point())
game.change_map('world', 'house')
game.inventory['party_heal'] = 1
check('Party Heal is not wasted on a healthy party', 1, (game.use_field_item('party_heal'), game.inventory['party_heal'])[1])
game.player_monsters[0].health = 1
game.use_field_item('party_heal')
check('Party Heal heals the party', game.player_monsters[0].get_stat('max_health'), game.player_monsters[0].health)

# ---------- shop ----------
for trainer in TRAINER_DATA.values():
	trainer['defeated'] = False
check('without badges the strong items are not sold', False, 'prime_orb' in game.shop_stock())
for trainer in list(BADGE_DATA)[:5]:
	TRAINER_DATA[trainer]['defeated'] = True
check('with 5 badges the Prime Orb is sold', True, 'prime_orb' in game.shop_stock())
game.inventory['shiny_charm'] = 1
check('key items you own are not sold again', False, 'shiny_charm' in game.shop_stock())
deal = game.daily_deal()
check("the daily deal is 30% off", round(SHOP_PRICES[deal] * (1 - DAILY_DISCOUNT)), game.shop_price(deal))
game.coins = 0
check('cannot buy without coins', 0, (game.buy_item('potion'), game.coins)[1])
check('nothing to sell any more (no materials)', {}, MATERIALS)
check('an item that is not unlocked cannot be bought', True, 'illuminator' not in game.shop_stock() and game.buy_item('illuminator') == game.buy_item('nonsense'))

# ---------- held items ----------
monster = Monster('Pouch', 10)
speed = monster.get_stat('speed')
monster.held_item = 'swift_scarf'
check('the Swift Scarf raises speed by 20%', round(speed * 1.2, 4), round(monster.get_stat('speed'), 4))
monster.held_item = 'guard_shell'
check('the Guard Shell raises defence by 25%', round(Monster('Pouch', 10).get_stat('defense') * 1.25, 4), round(monster.get_stat('defense'), 4))
game.coins = 0
game.player_monsters[0].held_item = 'lucky_coin'
TRAINER_DATA['o1']['defeated'] = False
earned = game.award_coins('o1')
game.player_monsters[0].held_item = None
check('the Lucky Coin gives 50% more coins', int(game.award_coins('o1') * 1.5), earned)

# ---------- cooldown after a battle ----------
game.end_battle(None)
game.transition_target, game.tint_mode = None, 'untint'
check('right after a battle nothing can start another', True, game.cooldown > 0)
game.transition_target = None
patch = next(iter(game.monster_sprites))   # stand in some long grass
game.player.hitbox.center = patch.rect.center
game.player.direction = pygame.Vector2(1, 0)
game.monster_encounter()
check('no wild battle during the cooldown', None, game.transition_target)
game.cooldown = 0
game.monster_encounter()
check('after the cooldown the grass works again', 'Battle', type(game.transition_target).__name__)
game.transition_target, game.tint_mode = None, 'untint'
game.player.unblock()
game.player.direction = pygame.Vector2()

# ---------- saving ----------
game.outdoors.set_hour(21)
game.save_game(1)
game.story = {}
game.load_game(1)
check('the time of day and the last hospital are saved', (21, ['hospital', 'world']), (round(game.outdoors.hour), game.story.get('hospital')))

folder.cleanup()
for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
