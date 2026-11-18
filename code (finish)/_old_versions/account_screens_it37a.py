# account_screens.py
# Iteration 18 (split from menus.py): the title screen, signing in, creating an account,
# passwords, the account hub and the account menu.

from settings import *
from localisation import t
from save_system import validate_username, validate_password, password_rules, validate_answer
from ui_style import UI, pixel_frame, icon_button

from ui_base import *


# The first screen: Sign In, Create Account and Quit (Iteration 15), drawn in the pixel style (Iteration 18).
class TitleScreen(PixelMenuScreen):
	def __init__(self, ui):
		super().__init__(ui)
		self.focus = 0 if self.game.profiles.profiles else 1   # nobody has an account yet -> Create Account

	def widgets(self):
		push = self.ui.push
		centre = WINDOW_WIDTH / 2
		return [
			{'kind': 'button', 'label': t('sign_in'), 'rect': pygame.FRect(0, 0, 420, 62).move_to(center = (centre, 300)), 'action': lambda: push(SignInScreen(self.ui))},
			{'kind': 'button', 'label': t('create_account'), 'rect': pygame.FRect(0, 0, 420, 62).move_to(center = (centre, 380)), 'action': lambda: push(CreateAccountScreen(self.ui))},
			{'kind': 'button', 'label': t('quit_game'), 'rect': pygame.FRect(0, 0, 420, 62).move_to(center = (centre, 460)), 'action': self.game.quit_game},
		] + self.quick_widgets()

	def back(self):
		pass

	def draw_extra(self, surface):
		draw_text(surface, self.fonts['regular'], t('title_tagline'), UI['text'], center = (WINDOW_WIDTH / 2, 210))
		draw_text(surface, self.fonts['small'], t('title_accounts', amount = len(self.game.profiles.profiles)), UI['muted'], center = (WINDOW_WIDTH / 2, 620))


# Base class for screens where the player fills in boxes (sign in, create account, passwords).
# fields = list of (key, kind) where kind is 'text', 'secret' (shown as *), 'button' or a tuple of choices.
# Up/Down/Tab move between boxes, Enter goes to the next box and submits on the last box.
# Iteration 15: Left/Right on a password box shows or hides the password so it can be checked.
class FormScreen(Screen):
	hint = 'hint_form'
	title_key = ''
	fields = ()
	max_length = 24
	field_gap = 90

	def __init__(self, ui):
		super().__init__(ui)
		self.values = {key: (kind[0] if isinstance(kind, tuple) else '') for key, kind in self.fields if kind != 'button'}
		self.focus = 0          # which box is selected
		self.error = None       # error key shown in red after Enter
		self.cursor_time = 0
		self.show_secret = False   # True shows passwords as normal text

	def handle_key(self, event):
		key, kind = self.fields[self.focus]
		if event.key == pygame.K_ESCAPE:
			self.back()
		elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
			step = -1 if event.key == pygame.K_UP or event.mod & pygame.KMOD_SHIFT else 1
			self.focus = (self.focus + step) % len(self.fields)
		elif event.key == pygame.K_RETURN:
			next_kind = self.fields[self.focus + 1][1] if self.focus < len(self.fields) - 1 else 'button'
			if kind == 'button':
				self.error = self.press(key)
			elif next_kind != 'button':
				self.focus += 1
			else:
				self.error = self.submit()
		elif kind == 'secret' and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
			self.show_secret = not self.show_secret
		elif isinstance(kind, tuple):
			# choice box: Left/Right change the choice (MOD wraps round)
			if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
				position = kind.index(self.values[key]) + (1 if event.key == pygame.K_RIGHT else -1)
				self.values[key] = kind[position % len(kind)]
		elif event.key == pygame.K_BACKSPACE and kind in ('text', 'secret'):
			self.values[key] = self.values[key][:-1]
			self.error = None

	# Iteration 16: tapping a box selects it, tapping a button presses it.
	def handle_click(self, pos):
		for rect, index in getattr(self, 'field_rects', []):
			if rect.collidepoint(pos):
				self.focus = index
				key, kind = self.fields[index]
				if kind == 'button':
					self.error = self.press(key)
				return

	# Adds typed characters to the selected text or password box (up to max_length).
	def handle_text(self, text):
		key, kind = self.fields[self.focus]
		text = ''.join(character for character in text if character.isprintable())
		if kind in ('text', 'secret') and text:
			self.values[key] = (self.values[key] + text)[:self.max_length]
			self.error = None

	# Overridden by each form. Returns an error key to show, or None if it worked.
	def submit(self):
		return None

	# Overridden by forms with buttons: runs when Enter is pressed on a button. Returns an error key or None.
	def press(self, key):
		return self.submit()

	# Overridden by each form: returns (text, colour) to show under a box while typing, or None.
	def feedback(self, key):
		return None

	# Checks the password and confirm boxes match. Used by every form that sets a password.
	def passwords_match(self, first = 'password', second = 'confirm'):
		return self.values[first] == self.values[second]

	def update(self, dt):
		self.cursor_time += dt

	def draw_extra(self, surface, area):
		pass

	def draw(self, surface):
		if not self.game.playing:
			draw_backdrop(surface, self.game)
		area = self.draw_panel(surface, t(self.title_key))
		width = area.width * 0.55
		top = area.top
		self.field_rects = []
		for index, (key, kind) in enumerate(self.fields):
			selected = index == self.focus
			if kind == 'button':
				button = pygame.FRect(area.left, top + 6, width, 40)
				self.field_rects.append((button, index))
				pygame.draw.rect(surface, self.theme['selected'] if selected else self.theme['row'], button, 0, 6)
				draw_text(surface, self.fonts['regular'], t(f'button_{key}'), self.theme['selected_text'] if selected else self.theme['text'], center = button.center)
				top += 54
				continue
			label = t(f'field_{key}') + (f"    ({t('show_password_hint')})" if kind == 'secret' else '')
			draw_text(surface, self.fonts['small'], label, self.theme['accent'] if selected else self.theme['muted'], topleft = (area.left, top))
			box = pygame.FRect(area.left, top + 20, width, 40)
			self.field_rects.append((box, index))
			top += self.field_gap
			pygame.draw.rect(surface, self.theme['row'], box, 0, 6)
			if selected:
				pygame.draw.rect(surface, self.theme['accent'], box, 2, 6)
			if isinstance(kind, tuple):
				text = f'<  {t(self.values[key])}  >'
			else:
				text = '*' * len(self.values[key]) if kind == 'secret' and not self.show_secret else self.values[key]
				if selected and int(self.cursor_time * 2) % 2 == 0:
					text += '_'
			draw_text(surface, self.fonts['regular'], text, self.theme['text'], midleft = box.midleft + vector(12, 0))
			message = self.feedback(key)
			if message:
				draw_text(surface, self.fonts['small'], message[0], message[1], topleft = box.bottomleft + vector(0, 4))
		self.draw_extra(surface, pygame.FRect(area.left + width + 32, area.top, area.width - width - 32, area.height))
		if self.error:
			color = COLORS['plant'] if self.error == 'password_reset_done' else COLORS['red']
			draw_text(surface, self.fonts['regular'], t(self.error), color, bottomleft = area.bottomleft)

	# Draws the list of password rules on the right, each one ticked in green once it is met.
	def draw_password_rules(self, surface, area, key = 'password'):
		draw_text(surface, self.fonts['regular'], t('password_rules_title'), self.theme['text'], topleft = area.topleft)
		for row, (rule, passed) in enumerate(password_rules(self.values[key], self.values.get('username', self.game.active_profile['username'] if self.game.active_profile else ''))):
			color = COLORS['plant'] if passed else self.theme['muted']
			mark = '+' if passed else '-'
			draw_text(surface, self.fonts['small'], f"{mark} {t(f'rule_{rule}', minimum = PASSWORD_MIN_LENGTH, maximum = PASSWORD_MAX_LENGTH)}", color, topleft = (area.left, area.top + 36 + row * 26))
		y = area.top + 36 + 7 * 26 + 10
		if self.values.get('confirm'):
			same = self.passwords_match(key, 'confirm')
			draw_text(surface, self.fonts['small'], t('passwords_match' if same else 'passwords_differ'), COLORS['plant'] if same else COLORS['red'], topleft = (area.left, y))


# Sign up: username (checked live), password (rules ticked live), confirm password, a security
# question and its answer (used if the password is forgotten).
class CreateAccountScreen(FormScreen):
	title_key = 'create_account'
	fields = (('username', 'text'), ('password', 'secret'), ('confirm', 'secret'), ('question', SECURITY_QUESTIONS), ('answer', 'text'))

	def feedback(self, key):
		if key == 'username' and self.values['username']:
			error = validate_username(self.values['username'], self.game.profiles.usernames())
			return (t(error), COLORS['red']) if error else (t('username_available'), COLORS['plant'])
		if key == 'answer':
			return (t('answer_note'), self.theme['muted'])
		return None

	def submit(self):
		if not self.passwords_match():
			return 'passwords_differ'
		try:
			profile, error = self.game.profiles.create(self.values['username'], self.values['password'], self.values['question'], self.values['answer'])
		except OSError:
			return 'username_save_failed'
		if error:
			return error
		self.game.select_profile(profile)
		self.ui.replace(AccountHub(self.ui))
		return None

	def draw_extra(self, surface, area):
		self.draw_password_rules(surface, area)


# Sign in with a username and password.
class SignInScreen(FormScreen):
	title_key = 'sign_in'
	fields = (('username', 'text'), ('password', 'secret'), ('sign_in', 'button'), ('forgot', 'button'))

	# Iteration 15: Forgot Password is a button on the sign in screen
	def press(self, key):
		if key == 'forgot':
			self.ui.push(ForgotPasswordScreen(self.ui, self.values['username']))
			return None
		return self.submit()

	def submit(self):
		profile, error = self.game.profiles.sign_in(self.values['username'], self.values['password'])
		if error == 'needs_password':
			# an account made before passwords existed - the player must set one now
			self.ui.replace(SetPasswordScreen(self.ui, profile))
			return None
		if error:
			self.values['password'] = ''
			return error
		self.game.select_profile(profile)
		self.ui.replace(AccountHub(self.ui))
		return None

	def draw_extra(self, surface, area):
		self.draw_paragraph(surface, t('sign_in_help'), area.topleft, area.width, self.theme['muted'])


# For accounts made before Iteration 14: sets a password and security question the first time they sign in.
class SetPasswordScreen(FormScreen):
	title_key = 'set_password'
	fields = (('password', 'secret'), ('confirm', 'secret'), ('question', SECURITY_QUESTIONS), ('answer', 'text'))

	def __init__(self, ui, profile):
		super().__init__(ui)
		self.profile = profile
		self.values['username'] = profile['username']

	def submit(self):
		error = (validate_password(self.values['password'], self.profile['username'])
			or (None if self.passwords_match() else 'passwords_differ') or validate_answer(self.values['answer']))
		if error:
			return error
		self.game.profiles.set_password(self.profile, self.values['password'], self.values['question'], self.values['answer'])
		self.game.select_profile(self.profile)
		self.ui.replace(AccountHub(self.ui))
		return None

	def draw_extra(self, surface, area):
		self.draw_password_rules(surface, area)


# Forgotten password: type the username, answer the security question, then choose a new password.
class ForgotPasswordScreen(FormScreen):
	title_key = 'forgot_password'
	fields = (('username', 'text'), ('answer', 'text'), ('password', 'secret'), ('confirm', 'secret'))

	def __init__(self, ui, username = ''):
		super().__init__(ui)
		self.values['username'] = username   # filled in from the sign in screen

	def feedback(self, key):
		if key == 'username' and self.values['username']:
			profile = self.game.profiles.find(self.values['username'])
			if profile and 'question' in profile:
				return (t(profile['question']), self.theme['accent'])
			return (t('forgot_no_question'), self.theme['muted'])
		return None

	def submit(self):
		if self.game.profiles.find(self.values['username']) is None:
			return 'forgot_no_account'
		if not self.passwords_match():
			return 'passwords_differ'
		error = self.game.profiles.reset_password(self.values['username'], self.values['answer'], self.values['password'])
		if error:
			return error
		self.ui.pop()   # back to the sign in screen underneath
		self.ui.screens[-1].values['username'] = self.values['username']
		self.ui.screens[-1].values['password'] = ''
		self.ui.screens[-1].focus = 1
		self.ui.screens[-1].error = 'password_reset_done'
		return None

	def draw_extra(self, surface, area):
		self.draw_password_rules(surface, area)


# Change password: needs the current password first.
class ChangePasswordScreen(FormScreen):
	title_key = 'change_password'
	fields = (('old_password', 'secret'), ('password', 'secret'), ('confirm', 'secret'))

	def submit(self):
		if not self.passwords_match():
			return 'passwords_differ'
		error = self.game.profiles.change_password(self.game.active_profile, self.values['old_password'], self.values['password'])
		if error:
			return error
		self.back()
		return None

	def draw_extra(self, surface, area):
		self.draw_password_rules(surface, area)


# Change username (Iteration 19: done from the main menu after signing in, so it is free).
class ChangeUsernameScreen(FormScreen):
	title_key = 'change_username'
	fields = (('username', 'text'),)
	max_length = USERNAME_MAX_LENGTH

	def feedback(self, key):
		if self.values['username']:
			others = [name for name in self.game.profiles.usernames() if name != self.game.active_profile['username']]
			error = validate_username(self.values['username'], others)
			return (t(error), COLORS['red']) if error else (t('username_available'), COLORS['plant'])
		return None

	def submit(self):
		error = self.game.profiles.rename(self.game.active_profile, self.values['username'])
		if error:
			return error
		self.back()
		return None

	def draw_extra(self, surface, area):
		self.draw_paragraph(surface, t('change_username_info'), area.topleft, area.width, self.theme['text'])


# After signing in (Iteration 18 redesign): avatar, username and level top left, the logo, quick
# buttons top right, Load / New / Online in the middle, Settings, Search, Players and Customer
# Service down the right, and Log Out and Policies in the bottom left.
class AccountHub(PixelMenuScreen):
	def widgets(self):
		push = self.ui.push
		centre = WINDOW_WIDTH / 2
		def side(icon_name, label, y, action, where = 'right'):
			x = WINDOW_WIDTH - 32 if where == 'right' else 32
			rect = pygame.FRect(0, 0, 300, 58)
			rect = rect.move_to(midright = (x, y)) if where == 'right' else rect.move_to(midleft = (x, y))
			return {'kind': 'side', 'icon': icon_name, 'label': label, 'rect': rect, 'action': action, 'side': where}
		return [
			{'kind': 'button', 'label': t('hub_load'), 'rect': pygame.FRect(0, 0, 420, 62).move_to(center = (centre, 300)), 'action': lambda: push(SlotScreen(self.ui, in_game = False))},
			{'kind': 'button', 'label': t('hub_new'), 'rect': pygame.FRect(0, 0, 420, 62).move_to(center = (centre, 380)), 'action': self.new_game},
			{'kind': 'button', 'label': t('hub_online'), 'rect': pygame.FRect(0, 0, 420, 62).move_to(center = (centre, 460)), 'action': self.online, 'enabled': False},
			{'kind': 'button', 'label': t('hub_versus'), 'rect': pygame.FRect(0, 0, 250, 50).move_to(center = (centre - 132, 534)), 'action': self.versus},   # Iteration 25
			{'kind': 'button', 'label': t('hub_credits'), 'rect': pygame.FRect(0, 0, 250, 50).move_to(center = (centre + 132, 534)), 'action': lambda: push(CreditsScreen(self.ui))},   # Iteration 24
			side('settings', t('menu_settings'), 420, lambda: push(SettingsScreen(self.ui))),
			side('search', t('menu_search'), 490, lambda: push(SearchScreen(self.ui))),
			side('trophy', t('menu_leaderboards'), 560, lambda: push(LeaderboardScreen(self.ui))),
			side('help', t('menu_support'), 630, lambda: push(support_screen(self.ui))),
			side('person', t('change_password'), 420, lambda: push(ChangePasswordScreen(self.ui)), 'left'),
			side('person', t('change_username'), 490, lambda: push(ChangeUsernameScreen(self.ui)), 'left'),
			side('door', t('log_out'), 560, self.game.return_to_title, 'left'),
			side('policy', t('menu_policies'), 630, lambda: push(policy_screen(self.ui)), 'left'),
		] + self.quick_widgets()

	# Returns the highest monster level in any of this account's saves. The save files are only read
	# again when the hub is shown again (not every frame), because reading them is slow.
	def best_level(self):
		if not hasattr(self, 'cached_level'):
			saves = getattr(self.game, 'saves', None)
			slots = saves.all_slots() if saves else []
			datas = [slot['data'] for slot in slots if slot['status'] == 'ok']
			self.cached_level = max((monster['level'] for data in datas for monster in data['party']), default = None)
		return self.cached_level

	def on_resume(self):
		super().on_resume()
		if hasattr(self, 'cached_level'):
			del self.cached_level

	# Starts a new game in the first empty slot (the Load screen can also delete old slots).
	def new_game(self):
		empty = [info['slot'] for info in self.game.saves.all_slots() if info['status'] == 'empty']
		if empty:
			slot = empty[0]
			self.ui.push(StarterScreen(self.ui, slot, self))   # Iteration 27: back to choosing the starter first
		else:
			self.message = t('hub_slots_full')

	def online(self):
		self.message = t('hub_online_soon')

	# Iteration 25: a local two-player battle needs at least one save (or uses rental teams)
	def versus(self):
		from extra_screens import VersusSetupScreen
		self.ui.push(VersusSetupScreen(self.ui))

	# Iteration 37: Esc no longer logs out (players stay signed in until they choose Log Out)
	def back(self):
		self.message = t('hub_esc_hint')

	# the player's card in the top left: a person icon, the username and their highest level
	def draw_extra(self, surface):
		profile = self.game.active_profile
		level = self.best_level()
		icon_button(surface, (64, 58), 'person', False, 72)
		card = pygame.FRect(112, 22, 300, 72)
		pixel_frame(surface, card, 5)
		draw_text(surface, self.fonts['bold'], profile['username'], UI['text'], midleft = card.midleft + vector(22, -12))
		detail = t('hub_level', level = level) if level else t('hub_no_saves')
		draw_text(surface, self.fonts['small'], detail, UI['gold'], midleft = card.midleft + vector(22, 16))


# Iteration 24: the credits from the ending, playable any time from the hub.
class CreditsScreen(Screen):
	use_backdrop = False

	def __init__(self, ui):
		super().__init__(ui)
		import ending
		self.ending = ending
		self.time = ending.CREDITS_TIME

	def handle_key(self, event):
		if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
			self.back()

	def handle_click(self, pos):
		self.back()

	def update(self, dt):
		self.time += dt
		if self.time > self.ending.CREDITS_TIME + self.ending.CREDITS_LENGTH + 1:
			self.back()

	def draw(self, surface):
		surface.fill((14, 12, 20))
		self.ending.EndingScreen.draw_credits(self, surface)


# In-game account options from the main menu.
# screens from the other menu modules (imported at the end so the modules can refer to each other)
from game_screens import SlotScreen, StarterScreen
from info_screens import LeaderboardScreen, SearchScreen, SettingsScreen, policy_screen, support_screen
