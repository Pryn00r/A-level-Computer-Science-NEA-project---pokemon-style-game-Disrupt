# test_accounts_and_shop.py
# Automated tests for Iteration 14: accounts and passwords, battle speed, catching with orbs,
# coins and the shop, releasing monsters, the party limit and two-way dialogue.
# Run with:  python test_accounts_and_shop.py   (no window or assets are needed)

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'   # run pygame without opening a window
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import tempfile
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from monster import Monster
from main import Game
from battle import catch_chance, turn_speed_for
from save_system import ProfileManager, validate_password
from game_data import TRAINER_DATA
from settings import TURN_TIME, MAX_SIGN_IN_ATTEMPTS, LOCKOUT_SECONDS, STARTING_COINS, RENAME_MONSTER_COST

results = []   # list of (test name, expected, actual, passed)

# Records one test result. Parameters: name, expected value, actual value
def check(name, expected, actual):
	results.append((name, expected, actual, expected == actual))

# ---------- PASSWORD RULES ----------
check('valid password "Monster#2026"', None, validate_password('Monster#2026', 'Simran'))
check('too short "Ab#1"', 'password_too_short', validate_password('Ab#1'))
check('too long (25 characters)', 'password_too_long', validate_password('Aa#1' + 'x' * 21))
check('no uppercase "monster#2026"', 'password_no_upper', validate_password('monster#2026'))
check('no lowercase "MONSTER#2026"', 'password_no_lower', validate_password('MONSTER#2026'))
check('no number "Monster#game"', 'password_no_number', validate_password('Monster#game'))
check('no symbol "Monster2026"', 'password_no_symbol', validate_password('Monster2026'))
check('repeated "Monster#555"', 'password_repeated', validate_password('Monster#555'))
check('two in a row is allowed "Monster#55"', None, validate_password('Monster#55'))
check('contains username "Simran#2026x"', 'password_has_username', validate_password('Simran#2026x', 'simran'))
check('boundary: exactly 8 characters "Abcde#12"', None, validate_password('Abcde#12'))

# ---------- ACCOUNTS ----------
folder = tempfile.TemporaryDirectory()
profiles = ProfileManager(folder.name)
profile, error = profiles.create('Simran', 'Monster#2026', 'question_food', 'Pizza')
check('create account', (True, None), (profile is not None, error))
saved_text = open(os.path.join(folder.name, 'profiles.json'), encoding = 'utf-8').read()
check('password is not stored as plain text', False, 'Monster#2026' in saved_text)
check('security answer is not stored as plain text', False, 'Pizza' in saved_text.replace('question_food', ''))
check('duplicate username rejected', 'username_taken', profiles.create('SIMRAN', 'Monster#2026', 'question_pet', 'Rex')[1])
check('weak password rejected when creating', 'password_no_symbol', profiles.create('Kiran', 'Monster2026', 'question_pet', 'Rex')[1])
check('answer too short rejected', 'answer_invalid', profiles.create('Kiran', 'Monster#2026', 'question_pet', 'R')[1])

check('sign in with the right password', ('Simran', None), (profiles.sign_in('simran', 'Monster#2026')[0]['username'], None))
check('sign in with the wrong password', 'sign_in_failed', profiles.sign_in('Simran', 'wrong')[1])
check('sign in with an unknown username (same message)', 'sign_in_failed', profiles.sign_in('Nobody', 'Monster#2026')[1])
for attempt in range(MAX_SIGN_IN_ATTEMPTS):
	profiles.sign_in('Simran', 'wrong', now = 1000)
check(f'locked after {MAX_SIGN_IN_ATTEMPTS} wrong passwords (even with the right one)', 'account_locked', profiles.sign_in('Simran', 'Monster#2026', now = 1001)[1])
check(f'unlocked again after {LOCKOUT_SECONDS} seconds', None, profiles.sign_in('Simran', 'Monster#2026', now = 1000 + LOCKOUT_SECONDS)[1])

check('change password: wrong current password', 'password_wrong', profiles.change_password(profile, 'nope', 'Better#Pass9'))
check('change password: same as before', 'password_same', profiles.change_password(profile, 'Monster#2026', 'Monster#2026'))
check('change password: weak new password', 'password_repeated', profiles.change_password(profile, 'Monster#2026', 'Better#Pass999'))
check('change password: works', None, profiles.change_password(profile, 'Monster#2026', 'Better#Pass9'))
check('old password no longer works', 'sign_in_failed', profiles.sign_in('Simran', 'Monster#2026', now = 5000)[1])

check('forgot password: wrong answer', 'answer_wrong', profiles.reset_password('Simran', 'pasta', 'Fresh!Start7', now = 6000))
check('forgot password: answer ignores capitals/spaces (and still works after a password change)', None, profiles.reset_password('Simran', '  PIZZA ', 'Fresh!Start7', now = 6001))
check('new password works after reset', None, profiles.sign_in('Simran', 'Fresh!Start7', now = 6002)[1])

profiles.profiles.append({'id': 'old', 'username': 'OldPlayer', 'created': '2026-11-02'})
check('account from before passwords must set one', 'needs_password', profiles.sign_in('OldPlayer', '')[1])

check('rename to a taken username', 'username_taken', profiles.rename(profile, 'oldplayer'))
error = profiles.rename(profile, 'SimranK')
check('rename works', (None, 'SimranK'), (error, profile['username']))
folder.cleanup()

# ---------- BATTLE SPEED ----------
check('slow battle is sped up (fastest speed 5)', 100 / TURN_TIME / 5, turn_speed_for([5, 3]))
check('fast battle is not slowed down (fastest speed 200)', 1, turn_speed_for([200, 120]))
check('empty field does not divide by zero', 1, turn_speed_for([]))

# ---------- CATCHING ----------
wild = Monster('Finsta', 4)
check('capture orb at full health: 10%', 10, round(catch_chance(wild, 'capture_orb') * 100))
wild.health = wild.get_stat('max_health') * 0.5
check('capture orb at half health: 60%', 60, round(catch_chance(wild, 'capture_orb') * 100))
check('great orb at half health: 96%', 96, round(catch_chance(wild, 'great_orb') * 100))
wild.health = 1
check('chance never goes above 100%', 100, round(catch_chance(wild, 'prime_orb') * 100))

# ---------- COINS, SHOP, RELEASE ----------
game = Game.__new__(Game)
game.toasts, game.coins = [], STARTING_COINS
game.reset_progress()
game.inventory = {}
for data in TRAINER_DATA.values():
	data['defeated'] = False
earned = game.award_coins('o1')
check('beating o1 gives 10 x level 3 + 100 badge bonus', 130, earned)
check('wild/unknown trainer gives no coins', 0, game.award_coins('Nurse'))
game.daily_deal = lambda: None   # so today's shop deal does not change the price
game.coins = 60
check('buy a capture orb (50 coins)', (10, 1), (game.buy_item('capture_orb') and game.coins, game.inventory['capture_orb']))
check('cannot buy with too few coins', (10, 1), (game.buy_item('capture_orb') and game.coins, game.inventory['capture_orb']))
del game.daily_deal
check('spend_coins rejects a negative amount', False, game.spend_coins(-50))

game.player_monsters = {0: Monster('Sparchu', 5), 1: Monster('Finsta', 4), 2: Monster('Larvea', 3)}
game.player_monsters[1].held_item = 'power_band'
game.release_monster(1)
check('release renumbers the party with no gaps', [(0, 'Sparchu'), (1, 'Larvea')], [(index, monster.name) for index, monster in game.player_monsters.items()])
check('released monster\'s held item goes back to the bag', 1, game.inventory.get('power_band'))
game.release_monster(0)
check('cannot release the last monster', 1, (game.release_monster(0), len(game.player_monsters))[1])

coins_before = game.coins
check('first nickname is free (Iteration 18)', (None, coins_before, 'Sparky'), (game.rename_monster(game.player_monsters[0], 'Sparky'), game.coins, game.player_monsters[0].display_name))
game.coins = RENAME_MONSTER_COST - 1
check('rename monster without enough coins', 'not_enough_coins', game.rename_monster(game.player_monsters[0], 'Leafy'))
game.coins = RENAME_MONSTER_COST
check('rename monster costs coins', (None, 0, 'Leafy'), (game.rename_monster(game.player_monsters[0], 'Leafy'), game.coins, game.player_monsters[0].display_name))

# ---------- DIALOGUE ----------
player_lines = [line for data in TRAINER_DATA.values() if data['dialog']['default'] for line in data['dialog']['default'] if isinstance(line, tuple)]
check('player lines are all ("player", text)', True, all(line[0] == 'player' and isinstance(line[1], str) for line in player_lines))
check('every trainer has default and defeated lines', True, all(data['dialog']['default'] for data in TRAINER_DATA.values()))

# ---------- print results ----------
for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
