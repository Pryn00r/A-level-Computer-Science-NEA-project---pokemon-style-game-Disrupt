# online_screens.py
# Iteration 37: online battles - the screens and the online version of the battle.
#   OnlineHubScreen      the Online menu: your rating, find a player, team builder, rankings, your battles
#   FindPlayerScreen     type a username, see if they are online, then challenge them
#   ChallengeScreen      choose the battle size (1 v 1 to 6 v 6) and where the teams come from
#   ChallengePopup       "Speedy challenges you!" - shown wherever you are in the game, Accept / Decline
#   OnlineBattleScreen   the battle itself, then Rematch or Leave
#   NetBattle            the normal Battle, except the server decides what happens (see online_engine.py)
# pump(game) is called once a frame by Game.frame: it reads the server's messages and passes them on.

from collections import deque

from settings import *
from game_data import ATTACK_DATA, MONSTER_DATA
from localisation import t, attack_name
from save_system import deserialise_monster, serialise_monster
from ui_base import *
from ui_style import UI, hud_tag, pixel_frame
from account_screens import FormScreen
from battle import Battle
from sprites import AttackSprite, DamageNumberSprite
import battle_rules as rules
import item_art
import online_client

FORMATS = ('fmt_1v1', 'fmt_2v2', 'fmt_3v3', 'fmt_6v6')
TEAM_SIZE = {'1v1': 1, '2v2': 2, '3v3': 3, '6v6': 6}
TEAM_RULES = ('team_random', 'team_story', 'team_built')
FINAL_FORMS = [name for name, data in MONSTER_DATA.items() if not data.get('evolve')]


# ---------- the connection ----------
def client(game):
	if getattr(game, 'online', None) is None:
		game.online = online_client.OnlineClient()
		game.online_invites = []
	return game.online

# Signs in to the server with the saved token, or returns False if the password is needed first.
def go_online(game, password = None):
	online = client(game)
	profile = game.active_profile
	if online.status in ('online', 'connecting') or profile is None:
		return True
	token = profile.get('online_token')
	if not token and not password:
		return False
	online.connect(profile['username'], password = password, token = None if password else token)
	return True

def go_offline(game):
	online = getattr(game, 'online', None)
	if online is not None:
		online.close()
		game.online = None

# Called every frame from Game.frame.
def pump(game):
	online = getattr(game, 'online', None)
	if online is None:
		return
	for message in online.pump():
		kind = message.get('type')
		if kind == 'welcome':
			game.online_tries, game.online_retry_at = 0, None
		if kind == 'welcome' and game.active_profile is not None:
			game.active_profile['online_token'] = message['token']   # the next sign in needs no password
			game.profiles.save()
		elif kind == 'error' and message.get('code') == 'token_expired' and game.active_profile is not None:
			game.active_profile.pop('online_token', None)
			game.profiles.save()
		elif kind == 'challenge_in':
			game.online_invites.append(message)
		elif kind in ('challenge_cancelled', 'challenge_expired'):
			game.online_invites = [invite for invite in game.online_invites if invite['id'] != message['id']]
		elif kind == 'disconnected' and online.battle is not None and online.error == 'no_connection':
			# dropped out in the middle of a battle - try to get back in every 3 seconds for a minute
			# (the server keeps the battle for 60 seconds)
			tries = getattr(game, 'online_tries', 0)
			if tries < 20:
				game.online_tries, game.online_retry_at = tries + 1, pygame.time.get_ticks() + 3000
		elif kind == 'battle_start':
			online.battle = message
			if not any(isinstance(screen, OnlineBattleScreen) for screen in game.ui.screens):
				# the screens used to send the challenge are closed, so leaving the battle goes back to the Online menu
				game.ui.screens[:] = [screen for screen in game.ui.screens if not isinstance(screen, (FindPlayerScreen, ChallengeScreen, WaitingScreen, ChallengePopup))]
				game.ui.push(OnlineBattleScreen(game.ui, message))
				continue
		for screen in list(game.ui.screens):
			if hasattr(screen, 'on_online'):
				screen.on_online(message)
	if getattr(game, 'online_retry_at', None) and pygame.time.get_ticks() >= game.online_retry_at and online.status != 'connecting':
		game.online_retry_at = None
		online.status, online.error = 'offline', None
		go_online(game)
	# a challenge pops up as soon as you are not in the middle of something
	if game.online_invites and can_interrupt(game):
		game.ui.push(ChallengePopup(game.ui, game.online_invites.pop(0)))

def can_interrupt(game):
	if game.playing and (game.battle or game.evolution or game.dialog_tree):
		return False
	busy = ('OnlineBattleScreen', 'ChallengePopup', 'TrainingScreen', 'VersusScreen', 'IntroScreen', 'WaitingScreen')
	return not any(type(screen).__name__ in busy for screen in game.ui.screens)


# ---------- teams ----------
# The team for a 'story' battle: the party you are playing with now, or the party in your most recently
# saved game. Returns (list of saved monsters, None) or (None, error key).
def story_team(game):
	if game.playing and getattr(game, 'player_monsters', None):
		return [serialise_monster(game.player_monsters[i]) for i in sorted(game.player_monsters)], None
	saves = getattr(game, 'saves', None)
	newest = None
	if saves is not None:
		for info in saves.all_slots():
			data = info['data']
			if info['status'] == 'ok' and data.get('party') and (newest is None or data.get('saved_at', '') > newest.get('saved_at', '')):
				newest = data
	if newest is None:
		return None, 'online_no_story_team'
	return list(newest['party']), None

def built_team(game):
	names = [name for name in (game.active_profile or {}).get('online_team', []) if name in FINAL_FORMS]
	if not names:
		return None, 'online_no_built_team'
	return [{'name': name} for name in names[:6]], None

def team_for(game, rule):
	if rule == 'random':
		return None, None
	return story_team(game) if rule == 'story' else built_team(game)


# ---------- the Online menu ----------
class OnlineHubScreen(ListScreen):
	hint = 'hint_list'

	def __init__(self, ui):
		super().__init__(ui)
		self.ask_password = not go_online(self.game)   # (the password screen opens on top once this screen is showing)

	def update(self, dt):
		if self.ask_password:
			self.ask_password = False
			self.ui.push(OnlinePasswordScreen(self.ui))

	def get_items(self):
		online = client(self.game)
		if not online.online:
			return [(t('online_retry'), self.retry), (t('menu_back'), self.back)]
		return [(t('online_find'), lambda: self.ui.push(FindPlayerScreen(self.ui))),
		        (t('online_team_builder'), lambda: self.ui.push(TeamBuilderScreen(self.ui))),
		        (t('online_rankings'), lambda: self.ui.push(OnlineListScreen(self.ui, 'leaderboard'))),
		        (t('online_my_battles'), lambda: self.ui.push(OnlineListScreen(self.ui, 'history'))),
		        (t('online_go_offline'), self.offline)]

	def row_picture(self, index, selected):
		icons = ('search', 'sword', 'trophy', 'scroll', 'door') if client(self.game).online else ('power', 'door')
		return row_icon(icons[index], selected) if index < len(icons) else None

	def retry(self):
		online = client(self.game)
		online.status, online.error = 'offline', None
		if not go_online(self.game):
			self.ask_password = True

	def offline(self):
		go_offline(self.game)
		self.back()

	def on_resume(self):
		self.index = 0

	def on_online(self, message):
		if message.get('type') == 'welcome':
			client(self.game).send({'type': 'me'})
		if message.get('type') == 'error' and message.get('code') == 'token_expired':
			self.ask_password = True

	def draw(self, surface):
		area = self.draw_panel(surface, t('online_title'))
		split = area.width * 0.45
		self.draw_list(surface, pygame.FRect(area.left, area.top, split, area.height - 20))
		left, width = area.left + split + 36, area.width - split - 36
		online = client(self.game)
		name = self.game.active_profile['username']
		draw_text(surface, self.fonts['bold'], name, UI['gold'], topleft = (left, area.top))
		if online.online and online.me:
			me = online.me
			y = draw_text(surface, self.fonts['regular'], t('online_rating', rating = me['rating']), self.theme['text'], topleft = (left, area.top + 40)).bottom
			y = draw_text(surface, self.fonts['regular'], t('online_record', wins = me['wins'], losses = me['losses']), self.theme['text'], topleft = (left, y + 6)).bottom
			draw_text(surface, self.fonts['small'], t('online_connected'), COLORS['plant'], topleft = (left, y + 14))
			self.draw_paragraph(surface, t('online_help'), (left, y + 52), width, self.theme['muted'])
		elif online.status == 'connecting':
			dots = '.' * (int(pygame.time.get_ticks() / 400) % 4)
			y = self.draw_paragraph(surface, t('online_connecting') + dots, (left, area.top + 44), width, self.theme['text'])
			self.draw_paragraph(surface, t('online_waking'), (left, y + 10), width, self.theme['muted'], 'small')
		else:
			error = online.error or 'no_connection'
			self.draw_paragraph(surface, t(f'online_error_{error}') if f'online_error_{error}' in STRINGS_EN else t('online_error_no_connection'),
			                    (left, area.top + 44), width, COLORS['red'])


# The first time you go online: your password, to register your name on the server (or prove it is yours).
class OnlinePasswordScreen(FormScreen):
	title_key = 'online_title'
	fields = (('password', 'secret'), ('go_online', 'button'))

	def __init__(self, ui):
		super().__init__(ui)
		self.sent = False

	def submit(self):
		profile = self.game.active_profile
		if not self.game.profiles.check_password(profile, self.values['password']):
			self.values['password'] = ''
			return 'password_wrong'
		online = client(self.game)
		online.status, online.error = 'offline', None
		go_online(self.game, self.values['password'])
		self.values['password'] = ''
		self.sent = True
		return None

	def update(self, dt):
		super().update(dt)
		online = client(self.game)
		if self.sent and online.online:
			self.back()
		elif self.sent and online.status == 'failed':
			self.sent, self.error = False, f'online_error_{online.error}' if online.error in ('name_taken', 'locked', 'old_version', 'bad_username', 'no_websockets') else 'online_error_no_connection'

	def back(self):
		super().back()
		top = self.ui.screens[-1] if self.ui.screens else None
		if isinstance(top, OnlineHubScreen) and not client(self.game).online and client(self.game).status != 'connecting':
			top.back()

	def draw_extra(self, surface, area):
		online = client(self.game)
		text = t('online_connecting') + '.' * (int(pygame.time.get_ticks() / 400) % 4) if online.status == 'connecting' else t('online_password_help')
		y = self.draw_paragraph(surface, text, area.topleft, area.width, self.theme['muted'])
		if online.status == 'connecting':
			self.draw_paragraph(surface, t('online_waking'), (area.left, y + 10), area.width, self.theme['muted'], 'small')


# Type a username and see if that player is online.
class FindPlayerScreen(FormScreen):
	title_key = 'online_find'
	fields = (('username', 'text'), ('search', 'button'), ('challenge', 'button'))

	def __init__(self, ui):
		super().__init__(ui)
		self.result = None
		self.searching = False

	def press(self, key):
		if key == 'challenge':
			if not self.result or not self.result['online']:
				return 'online_search_first'
			if self.result['busy']:
				return 'online_error_player_busy'
			self.ui.push(ChallengeScreen(self.ui, self.result['username']))
			return None
		return self.submit()

	def submit(self):
		name = self.values['username'].strip()
		if not name:
			return 'online_search_first'
		if name.casefold() == self.game.active_profile['username'].casefold():
			return 'online_error_challenge_self'
		self.result, self.searching = None, True
		client(self.game).send({'type': 'search', 'username': name})
		return None

	def on_online(self, message):
		if message.get('type') == 'search_result':
			self.result, self.searching = message, False
			if message['found'] and message['online']:
				self.focus = 2   # straight to the Challenge button

	def draw_extra(self, surface, area):
		result = self.result
		if self.searching:
			self.draw_paragraph(surface, t('online_searching'), area.topleft, area.width, self.theme['muted'])
		elif result is None:
			self.draw_paragraph(surface, t('online_find_help'), area.topleft, area.width, self.theme['muted'])
		elif not result['found']:
			self.draw_paragraph(surface, t('online_not_found', name = result['username']), area.topleft, area.width, COLORS['red'])
		else:
			draw_text(surface, self.fonts['bold'], result['username'], UI['gold'], topleft = area.topleft)
			online = result['online']
			color = COLORS['plant'] if online and not result['busy'] else COLORS['red'] if not online else UI['gold']
			state = t('online_busy') if result['busy'] else t('online_yes') if online else t('online_no')
			y = draw_text(surface, self.fonts['regular'], state, color, topleft = (area.left, area.top + 40)).bottom
			y = draw_text(surface, self.fonts['regular'], t('online_rating', rating = result['rating']), self.theme['text'], topleft = (area.left, y + 8)).bottom
			draw_text(surface, self.fonts['regular'], t('online_record', wins = result['wins'], losses = result['losses']), self.theme['text'], topleft = (area.left, y + 6))


# Choose the kind of battle and send the challenge.
class ChallengeScreen(FormScreen):
	title_key = 'online_challenge_title'
	fields = (('battle_size', FORMATS), ('team_source', TEAM_RULES), ('send_challenge', 'button'))

	def __init__(self, ui, opponent):
		super().__init__(ui)
		self.opponent = opponent

	def submit(self):
		format_name = self.values['battle_size'].split('_')[1]
		rule = self.values['team_source'].split('_')[1]
		team, error = team_for(self.game, rule)
		if error:
			return error
		if team is not None:
			team = team[:TEAM_SIZE[format_name]]
		client(self.game).send({'type': 'challenge', 'to': self.opponent, 'format': format_name, 'rule': rule, 'team': team})
		self.ui.push(WaitingScreen(self.ui, self.opponent))
		return None

	def feedback(self, key):
		if key == 'team_source':
			return (t(f"{self.values['team_source']}_help"), self.theme['muted'])
		return None

	def draw_extra(self, surface, area):
		self.draw_paragraph(surface, t('online_challenge_help', name = self.opponent), area.topleft, area.width, self.theme['muted'])


# "Waiting for Speedy to answer..." - Esc takes the challenge back.
class WaitingScreen(Screen):
	overlay = True

	def __init__(self, ui, opponent):
		super().__init__(ui)
		self.opponent = opponent
		self.challenge = None
		self.message = t('online_sending')
		self.closing = 0

	def handle_key(self, event):
		if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
			if self.challenge and not self.closing:
				client(self.game).send({'type': 'cancel', 'id': self.challenge['id']})
			self.back()

	def on_online(self, message):
		kind = message.get('type')
		if kind == 'challenge_sent':
			self.challenge = message
			self.message = t('online_waiting', name = message['to'])
		elif kind == 'challenge_declined':
			self.message, self.closing = t('online_declined', name = message['by']), 2.5
		elif kind == 'challenge_expired':
			self.message, self.closing = t('online_no_answer', name = self.opponent), 2.5
		elif kind == 'error':
			self.message, self.closing = t(f"online_error_{message.get('code')}") if f"online_error_{message.get('code')}" in STRINGS_EN else t('online_error_bad_challenge'), 2.5
		elif kind == 'battle_start':
			self.ui.screens.remove(self)

	def update(self, dt):
		if self.closing:
			self.closing = max(0, self.closing - dt)
			if self.closing == 0 and self in self.ui.screens:
				self.back()

	def draw(self, surface):
		shade = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
		shade.fill((0, 0, 0, 140))
		surface.blit(shade, (0, 0))
		box = pygame.FRect(0, 0, 640, 200).move_to(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
		pygame.draw.rect(surface, (40, 38, 46), box)
		pixel_frame(surface, box, 5)
		lines = wrap_text(self.fonts['regular'], self.message, 560)
		for row, line in enumerate(lines):
			draw_text(surface, self.fonts['regular'], line, UI['text'], midtop = (box.centerx, box.top + 40 + row * 30))
		dots = '.' * (int(pygame.time.get_ticks() / 400) % 4) if not self.closing else ''
		draw_text(surface, self.fonts['bold'], dots, UI['gold'], midtop = (box.centerx, box.top + 40 + len(lines) * 30))
		draw_key_hints(surface, self.fonts['small'], t('online_waiting_keys'), COLORS['light'], midbottom = (box.centerx, box.bottom - 16))


# Someone has challenged you. Shown on top of whatever you are doing (the world waits).
class ChallengePopup(ChoiceScreen):
	def __init__(self, ui, invite):
		self.invite = invite
		self.time_left = invite.get('seconds', 30)
		size, rule = t(f"fmt_{invite['format']}"), t(f"team_{invite['rule']}")
		title = t('online_challenged', name = invite['from'], rating = invite['rating'], size = size, rule = rule)
		super().__init__(ui, title, [(t('online_accept'), self.accept), (t('online_decline'), self.decline)])
		self.game.play('notice') if hasattr(self.game, 'play') else None

	def accept(self):
		team, error = team_for(self.game, self.invite['rule'])
		if error:
			client(self.game).send({'type': 'answer', 'id': self.invite['id'], 'accept': False})
			self.title = t(error)
			self.choices = [(t('menu_back'), self.back)]
			return
		if team is not None:
			team = team[:TEAM_SIZE[self.invite['format']]]
		client(self.game).send({'type': 'answer', 'id': self.invite['id'], 'accept': True, 'team': team})
		self.back()

	def decline(self):
		client(self.game).send({'type': 'answer', 'id': self.invite['id'], 'accept': False})
		self.back()

	def handle_key(self, event):
		if event.key == pygame.K_ESCAPE:
			self.decline()
		else:
			super().handle_key(event)

	def on_online(self, message):
		if message.get('type') in ('challenge_cancelled', 'challenge_expired') and message.get('id') == self.invite['id'] and self in self.ui.screens:
			self.back()

	def update(self, dt):
		self.time_left -= dt
		if self.time_left <= 0 and self in self.ui.screens:
			self.back()

	def draw(self, surface):
		super().draw(surface)
		# (the same size as the box ChoiceScreen draws, so the countdown sits just under it)
		lines = wrap_text(self.fonts['regular'], self.title, 520)
		height = 72 + len(lines) * 28 + min(len(self.choices), 7) * (self.row_height + self.row_gap)
		text = t('online_seconds', seconds = max(0, int(self.time_left)))
		hud_tag(surface, text, self.fonts['small'], 'clock', color = UI['gold'], midtop = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + height / 2 + 10))


# ---------- rankings and battle history ----------
class OnlineListScreen(Screen):
	def __init__(self, ui, kind):
		super().__init__(ui)
		self.kind = kind
		self.rows = None
		client(self.game).send({'type': kind})

	def handle_key(self, event):
		if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
			self.back()

	def on_online(self, message):
		if message.get('type') == self.kind:
			self.rows = message['rows']

	def draw(self, surface):
		area = self.draw_panel(surface, t('online_rankings' if self.kind == 'leaderboard' else 'online_my_battles'))
		if self.rows is None:
			draw_text(surface, self.fonts['regular'], t('online_loading'), self.theme['muted'], topleft = area.topleft)
			return
		if not self.rows:
			draw_text(surface, self.fonts['regular'], t('online_none_yet'), self.theme['muted'], topleft = area.topleft)
			return
		if self.kind == 'leaderboard':
			columns = ((0, 'leaderboard_rank'), (0.1, 'leaderboard_player'), (0.5, 'online_rating_short'), (0.68, 'online_wins'), (0.84, 'online_losses'))
			rows = [(str(n + 1), name, str(rating), str(wins), str(losses)) for n, (name, rating, wins, losses) in enumerate(self.rows)]
		else:
			columns = ((0, 'online_date'), (0.18, 'online_opponent'), (0.44, 'online_result'), (0.6, 'online_kind'), (0.86, 'online_change'))
			rows = [(row['date'], row['opponent'], t('online_won') if row['won'] else t('online_lost'), f"{t('fmt_' + row['format'])}", f"{row['change']:+d}") for row in self.rows]
		for ratio, key in columns:
			draw_text(surface, self.fonts['small'], t(key), self.theme['muted'], topleft = (area.left + 16 + ratio * area.width, area.top))
		me = self.game.active_profile['username']
		for number, row in enumerate(rows[:12]):
			y = area.top + 30 + number * 36
			mine = self.kind == 'leaderboard' and row[1] == me
			rect = pygame.FRect(area.left, y, area.width, 32)
			pygame.draw.rect(surface, UI['selected'] if mine else UI['row'], rect, 0, 4)
			for (ratio, _), value in zip(columns, row):
				color = UI['selected_text'] if mine else UI['text']
				if self.kind == 'history' and value in (t('online_won'), t('online_lost')):
					color = COLORS['plant'] if value == t('online_won') else COLORS['red']
				draw_text(surface, self.fonts['small'], value, color, midleft = (area.left + 16 + ratio * area.width, rect.centery))


# ---------- team builder ----------
# Pick up to 6 fully evolved monsters for 'Built team' battles (all level 50, so only your choices matter).
class TeamBuilderScreen(ListScreen):
	hint = 'hint_team_builder'

	def __init__(self, ui):
		super().__init__(ui)
		profile = self.game.active_profile
		self.team = [name for name in profile.get('online_team', []) if name in FINAL_FORMS]

	def get_items(self):
		return [(f"{'[x]' if name in self.team else '[ ]'}  {name}" + (f'   #{self.team.index(name) + 1}' if name in self.team else ''), lambda name = name: self.toggle(name)) for name in FINAL_FORMS]

	def row_picture(self, index, selected):
		return item_art.type_icon(MONSTER_DATA[FINAL_FORMS[index]]['stats']['element'], 22)

	def toggle(self, name):
		if name in self.team:
			self.team.remove(name)
		elif len(self.team) >= 6:
			self.message = t('online_team_full')
			return
		else:
			self.team.append(name)
		self.game.active_profile['online_team'] = list(self.team)
		self.game.profiles.save()

	def draw(self, surface):
		area = self.draw_panel(surface, t('online_team_builder'))
		split = area.width * 0.45
		self.draw_list(surface, pygame.FRect(area.left, area.top, split, area.height - 30))
		left, width = area.left + split + 36, area.width - split - 36
		y = self.draw_paragraph(surface, t('online_team_help'), (left, area.top), width, self.theme['muted'])
		for number, name in enumerate(self.team):
			icon = self.game.monster_frames['icons'][name]
			x = left + (number % 3) * 130
			row_y = y + 16 + (number // 3) * 110
			surface.blit(icon, icon.get_frect(midtop = (x + 50, row_y)))
			draw_text(surface, self.fonts['small'], name, self.theme['text'], midtop = (x + 50, row_y + icon.get_height() + 2))
		if self.message:
			draw_text(surface, self.fonts['regular'], self.message, COLORS['red'], bottomleft = (left, area.bottom))


# ---------- the battle ----------
STRINGS_EN = __import__('localisation').STRINGS['en']

# Turns a message from the server ([key, values]) into text in the player's language.
def message_text(message):
	key, values = message
	values = dict(values)
	if 'attack' in values:
		values['attack'] = attack_name(values['attack'])
	if 'stat' in values:
		values['stat'] = t(f"stat_{values['stat']}")
	text = t(key, **values)
	if key == 'battle_used' and values.get('effect'):
		text = f"{text} {t(f'battle_effect_' + values['effect'])}"
	return text


class NetBattle(Battle):
	# start: the server's battle_start message. send: function that sends a message to the server.
	def __init__(self, game, start, send):
		self.start = start
		self.me = start['side']
		self.them = 'b' if self.me == 'a' else 'a'
		self.send = send
		self.teams = {side: [deserialise_monster(dict(data, xp = 0)) for data in start['teams'][side]] for side in ('a', 'b')}
		self.events = deque()
		self.pending = None          # the attack event whose animation is playing
		self.waiting_reply = False   # an action was sent and the server has not answered yet
		self.forfeit_armed = False
		self.turn_left = None        # seconds left to choose (shown at the top)
		self.ended = None
		super().__init__({i: m for i, m in enumerate(self.teams[self.me])}, {i: m for i, m in enumerate(self.teams[self.them])},
		                 game.monster_frames, game.bg_frames['forest'], game.fonts, lambda *_: None, None, game.audio, {}, False, None)
		self.apply_state(start['state'], instant = True)
		waiting = start['state'].get('waiting')
		if waiting and not start['state'].get('winner'):
			self.begin_turn(waiting)

	# the monsters on the field come from the server's state, not from the first ones in each team
	def setup(self):
		state = self.start['state']
		for side, entity in ((self.me, 'player'), (self.them, 'opponent')):
			for pos, index in enumerate(state['field'][side]):
				if index is not None:
					self.create_monster(self.teams[side][index], index, pos, entity)

	def sprite_at(self, side, pos):
		group = self.player_sprites if side == self.me else self.opponent_sprites
		return next((sprite for sprite in group if sprite.pos_index == pos and not sprite.timers['kill'].active), None)

	# Copies the server's numbers onto the monsters, and swaps any monster that fainted or was switched out.
	def apply_state(self, state, instant = False):
		for side in ('a', 'b'):
			for monster, data in zip(self.teams[side], state['teams'][side]):
				monster.health, monster.energy = data['health'], data['energy']
				monster.status, monster.stages, monster.defending = data['status'], dict(data['stages']), data['defending']
				monster.initiative = data['initiative']
				monster.charging = (None, data['charging']) if data['charging'] else None
		for side in ('a', 'b'):
			entity = 'player' if side == self.me else 'opponent'
			for pos, index in enumerate(state['field'][side]):
				sprite = self.sprite_at(side, pos)
				if sprite is not None and sprite.index == index:
					continue
				new = (self.teams[side][index], index, pos, entity) if index is not None else None
				if sprite is None:
					if new:
						self.create_monster(*new)
				elif instant or sprite.monster.health > 0:   # switched out
					sprite.kill()
					if new:
						self.create_monster(*new)
				else:   # fainted - it shrinks and fades, then the next monster comes out
					sprite.delayed_kill(new)

	# ---------- the server decides, so the normal turn system is switched off ----------
	def update_all_monsters(self, option):
		for sprite in self.player_sprites.sprites() + self.opponent_sprites.sprites():
			sprite.monster.paused = True

	def check_stuck(self, dt):
		pass

	def check_end_battle(self):
		pass

	def check_death(self):
		pass

	def busy(self):
		sprites = self.player_sprites.sprites() + self.opponent_sprites.sprites()
		return self.pending is not None or any(s.state == 'attack' or s.timers['kill'].active for s in sprites)

	# Called every frame instead of the normal turn check: plays the next thing the server said happened.
	def check_active(self):
		while self.events and not self.busy():
			self.play_event(self.events.popleft())

	def play_event(self, event):
		kind = event['kind']
		message = event.get('message')
		if kind == 'turn':
			self.apply_state(event['state'])
			self.begin_turn(event['who'])
			return
		if kind == 'attack':
			attacker = self.sprite_at(*event['who'])
			target = self.sprite_at(*event['target'])
			if attacker is not None and target is not None:
				self.pending = event
				attacker.activate_attack(target, event['move'], pay = False)   # apply_attack runs when the animation ends
				return
			self.show_result(event, target)
			return
		if message:
			self.show_message(message_text(message))
		if kind == 'status' and event.get('damage'):
			sprite = self.sprite_at(*event['who'])
			if sprite is not None:
				DamageNumberSprite(sprite.rect.midtop, str(max(1, round(event['damage']))), self.fonts['bold'], COLORS['fire'], self.battle_sprites)
		if kind in ('charge', 'status'):
			self.play_sound('status')
		self.apply_state(event['state'])
		if kind == 'end':
			self.ended = event

	def begin_turn(self, who):
		side, pos = who
		sprite = self.sprite_at(side, pos)
		self.turn_left = self.start.get('seconds', 60)
		self.current_monster = None
		self.selection_mode = None
		if sprite is None:
			return
		sprite.set_highlight(True)
		if side == self.me:
			self.current_monster = sprite
			self.selection_mode = 'general'
			self.indexes = {key: 0 for key in self.indexes}
			self.play_sound('menu_select')
		self.acting = (side, pos)

	# The attack animation has finished - show what the server said happened.
	def apply_attack(self, target_sprite, attack, amount, attacker = None):
		event, self.pending = self.pending, None
		if event is None:
			return
		self.show_result(event, target_sprite)

	def show_result(self, event, target_sprite):
		data = ATTACK_DATA[event['move']]
		if target_sprite is not None:
			AttackSprite(target_sprite.rect.center, self.monster_frames['attacks'][data['animation']], self.battle_sprites, rules.animation_scale(event['move']))
		sound = data.get('sound', data['animation'])
		self.play_sound(sound if sound in self.sounds else f"hit_{data['element']}" if f"hit_{data['element']}" in self.sounds else 'hit_normal')
		if event.get('missed'):
			self.play_sound('miss')
		elif target_sprite is not None and event.get('healed') is not None:
			DamageNumberSprite(target_sprite.rect.midtop, f"+{max(0, round(event['healed']))}", self.fonts['bold'], COLORS['plant'], self.battle_sprites)
		elif target_sprite is not None and event.get('damage') is not None:
			effect = event.get('effect')
			color = {'super': COLORS['fire'], 'weak': COLORS['light']}.get(effect, COLORS['white'])
			DamageNumberSprite(target_sprite.rect.midtop, str(max(1, round(event['damage']))), self.fonts['bold'], color, self.battle_sprites)
			target_sprite.knock = 1.0
			if effect == 'super':
				self.shake_time = 0.25
				self.play_sound('super_hit')
			if event.get('critical'):
				self.play_sound('crit')
				self.shake_time = 0.35
		self.show_message(' '.join(message_text(m) for m in event['messages']))
		self.apply_state(event['state'])

	# ---------- the player's choices go to the server ----------
	def use_move(self, sprite, target, attack):
		side = self.me if target in self.player_sprites else self.them
		self.choose({'type': 'move', 'move': attack, 'target': [side, target.pos_index]})

	def switch_to(self, index, new_monster):
		self.choose({'type': 'switch', 'index': index})

	def choose_defend(self):
		self.choose({'type': 'defend'})

	def choose(self, action):
		self.send({'type': 'action', 'battle': self.start['battle'], 'action': action})
		self.current_monster, self.selection_mode, self.selected_attack = None, None, None
		self.waiting_reply = True
		self.forfeit_armed = False

	# 'Run' gives up the battle - pressed twice, so it cannot happen by accident
	def run_away(self):
		if self.forfeit_armed:
			self.send({'type': 'forfeit', 'battle': self.start['battle']})
			self.current_monster, self.selection_mode = None, None
		else:
			self.forfeit_armed = True
			self.show_message(t('online_forfeit_confirm'))

	def rejected(self, message):
		self.apply_state(message['state'])
		waiting = message['state'].get('waiting')
		if waiting:
			self.begin_turn(waiting)
		self.show_message(t('online_rejected'))

	def update(self, dt):
		if self.turn_left is not None:
			self.turn_left = max(0, self.turn_left - dt)
		super().update(dt)


class OnlineBattleScreen(Screen):
	use_backdrop = False

	def __init__(self, ui, start):
		super().__init__(ui)
		self.previous_music = getattr(self.game, 'music', None)
		self.game.set_music('battle')
		self.new_battle(start)

	def new_battle(self, start):
		self.start = start
		self.battle = NetBattle(self.game, start, client(self.game).send)
		self.result = start.get('result')
		self.note = ''
		self.opponent_gone = False
		self.rematch_sent = False
		self.dt = 1 / 60

	def on_online(self, message):
		kind = message.get('type')
		if kind == 'battle_start':
			if message['battle'] != self.start['battle'] or message.get('resume'):
				self.new_battle(message)
		elif kind == 'events' and message['battle'] == self.start['battle']:
			self.battle.events.extend(message['events'])
			self.battle.waiting_reply = False
		elif kind == 'action_rejected':
			self.battle.waiting_reply = False
			self.battle.rejected(message)
		elif kind == 'battle_end' and message['battle'] == self.start['battle']:
			self.result = message
		elif kind == 'opponent_left':
			self.note = t('online_opponent_left', seconds = int(message['seconds']))
		elif kind == 'opponent_gone':
			self.opponent_gone, self.note = True, t('online_opponent_gone')
		elif kind == 'rematch_asked':
			self.note = t('online_rematch_asked', name = message['by'])
		elif kind == 'disconnected':
			self.note = t('online_reconnecting')
		elif kind == 'welcome':
			self.note = ''

	def finished(self):
		return self.result is not None and self.battle.ended is not None and not self.battle.events and not self.battle.busy()

	def handle_key(self, event):
		if not self.finished():
			return
		if event.key == pygame.K_r and not self.opponent_gone and not self.rematch_sent:
			rule = self.start['rule']
			team, error = team_for(self.game, rule)
			if error:
				self.note = t(error)
				return
			if team is not None:
				team = team[:TEAM_SIZE[self.start['format']]]
			client(self.game).send({'type': 'rematch', 'team': team})
			self.rematch_sent = True
			self.note = t('online_rematch_waiting')
		elif event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
			self.leave()

	def leave(self):
		client(self.game).send({'type': 'leave'})
		client(self.game).battle = None
		client(self.game).send({'type': 'me'})
		if self.previous_music:
			self.game.set_music(self.previous_music)
		if self in self.ui.screens:
			if self.ui.screens[-1] is self:
				self.back()
			else:
				self.ui.screens.remove(self)

	def update(self, dt):
		self.dt = min(0.05, dt)

	def draw(self, surface):
		battle = self.battle
		battle.update(self.dt)
		names = self.start['names']
		size, rule = t(f"fmt_{self.start['format']}"), t(f"team_{self.start['rule']}")
		title = f"{names[battle.me]}  vs  {names[battle.them]}   -   {size}, {rule}"
		tag = hud_tag(surface, title, self.fonts['bold'], 'sword', color = UI['gold'], midtop = (WINDOW_WIDTH / 2, 10))
		acting = getattr(battle, 'acting', None)
		if not self.finished() and acting and not (acting[0] == battle.me and battle.current_monster is None):
			mine = acting[0] == battle.me
			text = t('online_your_turn' if mine else 'online_their_turn', name = names[battle.them])
			if battle.turn_left is not None:
				text += f'   {int(battle.turn_left)}s'
			hud_tag(surface, text, self.fonts['regular'], 'clock', color = COLORS['white'] if mine else COLORS['light'], midtop = (WINDOW_WIDTH / 2, tag.bottom + 6))
		if self.note and not self.finished():
			hud_tag(surface, self.note, self.fonts['small'], 'help', color = UI['gold'], midtop = (WINDOW_WIDTH / 2, tag.bottom + 48))
		if self.finished():
			self.draw_result(surface)

	def draw_result(self, surface):
		shade = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
		shade.fill((0, 0, 0, 170))
		surface.blit(shade, (0, 0))
		won = self.result['winner'] == self.battle.me
		heading = pygame.transform.scale_by(self.fonts['bold'].render(t('online_you_won' if won else 'online_you_lost'), False, UI['gold'] if won else COLORS['red']), 2)
		surface.blit(heading, heading.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 60)))
		old, new = self.result['ratings'][self.battle.me]
		draw_text(surface, self.fonts['regular'], t('online_rating_change', old = old, new = new, change = f'{new - old:+d}'), COLORS['white'], midtop = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
		reason = self.result.get('reason')
		if reason in ('forfeit', 'disconnect'):
			draw_text(surface, self.fonts['small'], t(f'online_reason_{reason}'), COLORS['light'], midtop = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 34))
		keys = t('online_after_keys_no_rematch') if self.opponent_gone else t('online_after_keys')
		draw_key_hints(surface, self.fonts['regular'], keys, COLORS['white'], midtop = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 70))
		if self.note:
			draw_text(surface, self.fonts['small'], self.note, UI['gold'], midtop = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 112))
