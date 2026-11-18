# extra_screens.py
# Iteration 25c: fast travel and local two-player battles.
# (Iteration 31: the daycare, crafting, move tutor, trader, bounty board, phone calls and photo mode were removed.)

from settings import *
from game_data import ATTACK_DATA
from localisation import t, attack_name
from ui_style import UI
from ui_base import *
import controls
import item_art
import town


def monster_label(monster):
	return f'{monster.display_name}  Lv {monster.level}'

def party_list(game):
	return [game.player_monsters[i] for i in sorted(game.player_monsters)]


# ---------- fast travel ----------
class TravelScreen(ListScreen):
	hint = 'hint_list'

	def places(self):
		import postgame
		spots = [('world', spot) for spot in town.visited(self.game)]
		if postgame.unlocked(self.game):
			spots.append((postgame.GLITCH_MAP, 'entrance'))
		return spots

	def get_items(self):
		return [(t(f'travel_{spawn if target == "world" else target}'), lambda target = target, spawn = spawn: self.go(target, spawn)) for target, spawn in self.places()]

	def go(self, target, spawn):
		game = self.game
		game.ui.clear()
		game.player.block()
		game.transition_target, game.tint_mode = (target, spawn), 'tint'
		game.counters['travels'] = game.counters.get('travels', 0) + 1

	def draw(self, surface):
		area = self.draw_panel(surface, t('travel_title'))
		self.draw_list(surface, pygame.FRect(area.left, area.top, area.width * 0.5, area.height - 36))
		self.draw_paragraph(surface, t('travel_info'), (area.left + area.width * 0.5 + 32, area.top), area.width * 0.5 - 32, self.theme['text'])


# ---------- local two-player battles ----------
# Player 1 uses the party from one of this account's saves. Player 2 uses another save or a rental team.
# Both play on the same keyboard, taking turns: the menu opens beside whichever monster's turn it is.
RENTAL = ('Charmadillo', 'Finiette', 'Pluma', 'Friolera', 'Jacana', 'Draem')
VERSUS_LEVEL = 50

class VersusSetupScreen(ListScreen):
	hint = 'hint_list'

	def __init__(self, ui):
		super().__init__(ui)
		self.slots = [slot for slot in self.game.saves.all_slots() if slot['status'] == 'ok']
		self.choice = []   # the teams chosen so far

	def options(self):
		options = [(t('versus_slot', slot = slot['slot']), slot['data']['party']) for slot in self.slots]
		options.append((t('versus_rental'), None))
		return options

	def get_items(self):
		return [(label, lambda party = party: self.pick(party)) for label, party in self.options()]

	def pick(self, party):
		from save_system import deserialise_monster
		from monster import Monster
		if party is None:
			team = {i: Monster(name, VERSUS_LEVEL) for i, name in enumerate(RENTAL)}
		else:
			team = {i: deserialise_monster(data) for i, data in enumerate(party)}
		for monster in team.values():   # an exhibition: everyone starts healthy, nothing is saved
			monster.health, monster.energy = monster.get_stat('max_health'), monster.get_stat('max_energy')
			monster.status, monster.charging = None, None
		self.choice.append(team)
		if len(self.choice) == 2:
			self.ui.pop()
			self.ui.push(VersusScreen(self.ui, *self.choice))
		else:
			self.index = 0

	def draw(self, surface):
		draw_backdrop(surface, self.game)
		area = self.draw_panel(surface, t('versus_title'))
		draw_text(surface, self.fonts['bold'], t('versus_pick', player = len(self.choice) + 1), UI['gold'], topleft = (area.left, area.top))
		self.draw_list(surface, pygame.FRect(area.left, area.top + 40, area.width * 0.5, area.height - 76))
		self.draw_paragraph(surface, t('versus_info'), (area.left + area.width * 0.5 + 32, area.top + 40), area.width * 0.5 - 32, self.theme['text'])


class VersusScreen(Screen):
	use_backdrop = False

	def __init__(self, ui, team_one, team_two):
		super().__init__(ui)
		from battle import Battle
		game = self.game
		self.result = None
		self.battle = Battle(team_one, team_two, game.monster_frames, game.bg_frames['forest'], game.fonts, self.finished, None, game.audio, {}, False, None)
		self.battle.versus = True
		self.battle.vs = (game.overworld_frames['characters']['player'], game.overworld_frames['characters']['player'], t('versus_title'))
		self.battle.vs_time = 2.2
		self.wait = 0
		game.set_music('battle')

	def finished(self, character, lost = False):
		self.result = t('versus_p2_wins') if lost else t('versus_p1_wins')
		self.wait = 3

	def handle_key(self, event):
		if self.result and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
			self.close()

	def close(self):
		self.game.set_music(MENU_MUSIC)
		self.back()

	def update(self, dt):
		if self.result:
			self.wait -= dt

	def draw(self, surface):
		self.battle.update(1 / 60 if not hasattr(self, 'last') else min(0.05, pygame.time.get_ticks() / 1000 - self.last))
		self.last = pygame.time.get_ticks() / 1000
		side = self.battle.acting_side() if hasattr(self.battle, 'acting_side') else None
		if side and not self.result:
			label = t('versus_turn', player = 1 if side == 'player' else 2)
			draw_text(surface, self.fonts['bold'], label, UI['gold'], midtop = (WINDOW_WIDTH / 2, 12))
		if self.result:
			shade = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
			shade.fill((0, 0, 0, 160))
			surface.blit(shade, (0, 0))
			text = pygame.transform.scale_by(self.fonts['bold'].render(self.result, False, UI['gold']), 2)
			surface.blit(text, text.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)))
			draw_text(surface, self.fonts['regular'], t('versus_again'), COLORS['white'], midtop = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 50))
