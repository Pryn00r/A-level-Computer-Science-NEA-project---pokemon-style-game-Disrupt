# test_playtest_fixes.py
# Automated tests for Iteration 19 (fixes after a full playthrough): the in-game menu, leaving the gym
# after beating its leader, the desert trainer's background, the choice after the ending, music for
# each area and battle type, the waves animating together, trainers noticing the player after
# changing map, quest order, the badge pictures and the potion / ether icons.
# Run with:  python test_playtest_fixes.py   (no window is opened)

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'   # run pygame without opening a window
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from settings import MENU_MUSIC, GYM_LEADERS, GYM_OF_LEADER, MUSIC_TRACKS, MAP_MUSIC, BIOME_MUSIC, asset
from game_data import TRAINER_DATA, QUEST_DATA, BADGE_DATA
from main import Game
from sprites import AnimatedSprite
from ui_style import BADGE_STYLE, badge_image
import menus

results = []   # list of (test name, expected, actual, passed)

# Records one test result. Parameters: name, expected value, actual value
def check(name, expected, actual):
	results.append((name, expected, actual, expected == actual))

class FakeSound:   # stands in for a pygame Sound so the tests can see what played
	def __init__(self):
		self.playing = False
	def play(self, loops = 0, fade_ms = 0):
		self.playing = True
	def fadeout(self, ms):
		self.playing = False
	def stop(self):
		self.playing = False
	def set_volume(self, volume):
		pass

# ---------- THE REAL GAME (no window) ----------
game = Game()   # loads every map and image, like the real game

# in-game menu: only things to do with the game being played
game.reset_progress()
from monster import Monster
game.player_monsters = {0: Monster('Sparchu', 5)}
labels = [label for label, action in menus.MainMenu(game.ui).get_items()]
for removed in ('change_password', 'menu_search', 'menu_support', 'menu_policies', 'menu_leaderboards', 'menu_account'):
	check(f'in-game menu no longer has "{menus.t(removed)}"', False, menus.t(removed) in labels)
check('in-game menu ends with "Back to Main Menu"', menus.t('menu_main_menu'), labels[-1])
check('in-game menu has 13 options (Records added in Iteration 25; the Monster Box and Clothes in Iteration 31; Training in Iteration 33)', 13, len(labels))

# leaving the gym after beating the leader
check('every gym leader has a gym', set(GYM_LEADERS), set(GYM_OF_LEADER))
for leader, gym in GYM_OF_LEADER.items():
	game.change_map(gym, 'entrance')
	exits = [sprite.target for sprite in game.transition_sprites]
	check(f'the {gym} gym door leads to the "{gym}" spot outside (where the player is sent)', True, ('world', gym) in exits)
game.change_map('world', 'house')
game.leaving_gym, game.evolution = 'fire', None
game.leave_gym()
check('after beating a leader the player fades to outside the gym', (('world', 'fire'), 'tint', None), (game.transition_target, game.tint_mode, game.leaving_gym))
game.transition_target, game.tint_mode = None, 'untint'
game.player.unblock()

# the desert trainer next to the fire gym
check('the trainer in the desert has the desert background (was the snow one)', 'sand', TRAINER_DATA['o6']['biome'])

# trainers notice the player after coming out of a building
game.change_map('world', 'hospital')   # o1 is listed before this start point in the map
trainer = next(sprite for sprite in game.character_sprites if sprite.character_id == 'o1')
check('trainers watch the player who is actually on the map (not the one from the last map)', True, trainer.player is game.player)
game.player.block()
trainer.has_noticed = False
trainer.raycast()
check('a trainer does not walk over while the player is busy talking to someone else', False, trainer.has_noticed)
game.player.unblock()

# waves
water = [sprite for sprite in game.all_sprites if type(sprite) is AnimatedSprite]
check('the map has animated water', True, len(water) > 100)
AnimatedSprite.world_time = 1.234
water[0].animate(0)
water[-1].animate(0)
check('two water tiles far apart show the same frame (the waves move together)', water[0].frame_index, water[-1].frame_index)

# music
check('every music track exists', [], [name for name in MUSIC_TRACKS if name not in game.audio])
game.audio = {name: FakeSound() for name in game.audio}
game.music = None
game.set_music('zone_grass')
game.set_music('zone_sand')
check('changing music fades the old track out and starts the new one', (False, True), (game.audio['zone_grass'].playing, game.audio['zone_sand'].playing))
check('houses and hospitals have their own music', 'zone_town', MAP_MUSIC['hospital'])
game.change_map('world', 'house')
check('the start of the game (grass) plays the grass music', BIOME_MUSIC['forest'], game.area_music())
game.change_map('world', 'fire')
check('outside the fire gym (desert) plays the desert music', BIOME_MUSIC['sand'], game.area_music())
game.change_map('world', 'water')
check('outside the water gym (snow) plays the snow music', BIOME_MUSIC['ice'], game.area_music())
game.change_map('fire', 'entrance')
check('inside the fire gym plays the desert music', 'zone_sand', game.area_music())
game.start_battle_music('o3')
check('a trainer battle has its own music', 'battle_trainer', game.music)
game.start_battle_music(None)
check('a wild battle has its own music', 'battle_wild', game.music)
check('the menu music is the original track', 'overworld', MENU_MUSIC)

# the choice after the ending
game.change_map('water', 'entrance')
game.continue_after_ending()
check('"Keep Playing" puts the player back at the start of the world (not in the gym)', ('world', 'house'), (game.current_map, game.current_spawn))

# quest order
quests = list(QUEST_DATA)
screen = menus.QuestScreen(game.ui)
game.claimed = {quests[0]}
game.quest_progress = lambda quest: QUEST_DATA[quest]['target'] if quest in (quests[0], quests[3]) else 0
order = [quest for quest in screen.ordered() if ':' not in quest]   # Iteration 25: daily/weekly quests always come first
check('a quest ready to claim is at the top', quests[3], order[0])
check('a claimed quest is at the bottom', quests[0], order[-1])
check('quests still in progress keep their order in the middle', [q for q in quests if q not in (quests[0], quests[3])], order[1:-1])

# badges and items
check('every badge has its own colour and picture', [], [data['badge'] for data in BADGE_DATA.values() if data['badge'] not in BADGE_STYLE])
check('every badge picture is different', len(BADGE_DATA), len({badge_image(data['badge'], True, False).get_at((48, 48))[:3] + (data['badge'],) for data in BADGE_DATA.values()}))
check('the potion and ether bottles exist (normal and highlighted)', True, all(os.path.exists(asset('graphics', 'ui', f'{name}.png')) for name in ('potion', 'potion_highlight', 'ether', 'ether_highlight')))
check('the Bag button in battle is the potion bottle', True, game.monster_frames['ui']['bag'] is game.monster_frames['ui']['potion'])
check('items show their picture in lists (orbs too since Iteration 20)', (True, True, True), (menus.item_icon(game, 'potion') is not None, menus.item_icon(game, 'ether') is not None, menus.item_icon(game, 'capture_orb') is not None))

# ---------- print results ----------
for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
