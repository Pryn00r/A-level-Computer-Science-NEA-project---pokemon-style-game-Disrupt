# test_typing_and_balance.py
# Automated tests for Iteration 15: energy in battles, the fairer first trainer and typing in text
# boxes (passwords were sometimes missing a character, so signing in failed).
# Run with:  python test_typing_and_balance.py   (no window or assets are needed)

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'   # run pygame without opening a window
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import tempfile
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from monster import Monster
from game_data import TRAINER_DATA
from save_system import ProfileManager
from settings import ENERGY_PER_TURN, DEFEND_ENERGY
import menus

results = []   # list of (test name, expected, actual, passed)

# Records one test result. Parameters: name, expected value, actual value
def check(name, expected, actual):
	results.append((name, expected, actual, expected == actual))

# ---------- ENERGY ----------
sparchu = Monster('Sparchu', 5)
sparchu.energy = 0
sparchu.regain_energy()
check('energy gained per turn = recovery x 2', 6.0 * ENERGY_PER_TURN, sparchu.energy)
sparchu.energy = 0
sparchu.defend()
check('defending gives back 25% of max energy', (True, 50 * DEFEND_ENERGY), (sparchu.defending, sparchu.energy))
sparchu.energy = 49
sparchu.regain_energy()
check('energy never goes above the maximum', 50, sparchu.energy)

# 20 turns of a level 5 Sparchu attacking whenever it can and defending otherwise:
# before Iteration 15 it could only attack once and was then stuck
sparchu = Monster('Sparchu', 5)
attacks = 0
for turn in range(20):
	sparchu.regain_energy()
	affordable = sparchu.get_abilities(all = False)
	if affordable:
		sparchu.reduce_energy(affordable[0])
		attacks += 1
	else:
		sparchu.defend()
check('level 5 Sparchu keeps attacking over 20 turns (at least 10 attacks)', True, attacks >= 10)

# ---------- FIRST TRAINER ----------
check('first trainer has one level 3 monster', {0: ('Larvea', 3)}, TRAINER_DATA['o1']['monsters'])

# ---------- TYPING ----------
from preferences import DEFAULT_PREFERENCES
class FakeGame:   # just enough of Game for the menu screens
	def __init__(self, root):
		self.profiles = ProfileManager(root)
		self.fonts = {name: pygame.font.Font(None, 20) for name in ('regular', 'small', 'bold', 'dialog')}
		self.active_profile = None
		self.playing = False
		self.preferences = dict(DEFAULT_PREFERENCES)   # (Iteration 18: the pixel menus read brightness/volume)
		self.display_surface = pygame.Surface((1280, 720))
	def select_profile(self, profile):
		self.active_profile = profile
	def menu_closed(self):
		pass
	def return_to_title(self):
		pass
	def quit_game(self):
		pass

def key(code, mod = 0):
	return pygame.event.Event(pygame.KEYDOWN, key = code, unicode = '', mod = mod, scancode = 0)

def text(characters):
	return pygame.event.Event(pygame.TEXTINPUT, text = characters)

def type_into(ui, characters):
	ui.update(0, [text(character) for character in characters])

folder = tempfile.TemporaryDirectory()
game = FakeGame(folder.name)
ui = menus.ScreenStack(game)
ui.push(menus.CreateAccountScreen(ui))
ui.update(0, [])
for value, enter in (('Pry00r', True), ('Blue#Sky2026', True), ('Blue#Sky2026', True)):
	type_into(ui, value)
	ui.update(0, [key(pygame.K_RETURN)])
ui.update(0, [key(pygame.K_RETURN)])   # keep the first security question
type_into(ui, 'Green')
ui.update(0, [key(pygame.K_RETURN)])
check('account made by typing into the boxes', ('Pry00r', 'AccountHub'), (game.active_profile['username'], type(ui.screens[-1]).__name__))

# sign in again after "restarting" (profiles loaded from the file)
game2 = FakeGame(folder.name)
ui2 = menus.ScreenStack(game2)
ui2.push(menus.SignInScreen(ui2))
ui2.update(0, [])
type_into(ui2, 'pry00r')
ui2.update(0, [key(pygame.K_RETURN)])
ui2.update(0, [text('Blue#Sky2026')])   # a whole word arriving in one TEXTINPUT event
ui2.update(0, [key(pygame.K_RETURN)])
check('sign in after restarting works', 'AccountHub', type(ui2.screens[-1]).__name__)

# typing and Backspace
form = menus.SignInScreen(ui2)
form.handle_text('abc')
form.handle_key(key(pygame.K_BACKSPACE))
check('Backspace removes one character', 'ab', form.values['username'])
form.handle_text('x' * 40)
check('text box stops at its maximum length', form.max_length, len(form.values['username']))
form.focus = 1
form.handle_key(key(pygame.K_RIGHT))
check('Left/Right on a password box shows the password', True, form.show_secret)

# a screen opened by a key press must not also receive that key as text (e.g. R opens rename)
ui3 = menus.ScreenStack(game2)
ui3.push(menus.SignInScreen(ui3))
check('new screen ignores text in the frame it opened', '', (ui3.update(0, [text('r')]), ui3.screens[-1].values['username'])[1])
folder.cleanup()

# ---------- print results ----------
for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
