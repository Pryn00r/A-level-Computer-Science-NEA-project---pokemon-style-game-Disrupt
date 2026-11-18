# game_screens.py
# Iteration 18 (split from menus.py): the screens used while playing - shop, save slots, the
# in-game menu, party, bag, choosing a starter and naming monsters.

from math import sin

from settings import *
from game_data import ATTACK_DATA, MONSTER_DATA, STARTER_MONSTERS, STARTER_LEVEL, BADGE_DATA, HELD_ITEM_DATA, KEY_ITEMS, MATERIALS, ITEM_DATA
from localisation import t, attack_name, stat_name, move_effects
from save_system import format_play_time
from monster import Monster, NICKNAME_MAX_LENGTH
from support import draw_bar, stat_color
from ui_style import UI, icon, badge_image
import controls

from ui_base import *



# The nurse's shop. Enter buys one of the selected item.
class ShopScreen(ListScreen):
	hint = 'hint_shop'

	# Iteration 25: what is for sale grows with your badges, key items you own are not sold again, and the
	# materials you found can be sold at the bottom of the list.
	def names(self):
		stock = self.game.shop_stock()
		sell = [name for name in MATERIALS if self.game.inventory.get(name, 0) > 0]
		return [('buy', name) for name in stock] + [('sell', name) for name in sell]

	def get_items(self):
		items = []
		for action, name in self.names():
			if action == 'buy':
				price = self.game.shop_price(name)
				deal = '  -30%!' if name == self.game.daily_deal() else ''
				items.append((f"{item_name(name)}   {price}c{deal}", lambda name = name: self.buy(name)))
			else:
				items.append((t('shop_sell_row', item = item_name(name), price = MATERIALS[name], amount = self.game.inventory[name]), lambda name = name: self.sell(name)))
		return items

	def row_picture(self, index, selected):
		names = self.names()
		return small_item_icon(self.game, names[index][1]) if index < len(names) else None

	def buy(self, name):
		self.message = self.game.buy_item(name)

	def sell(self, name):
		self.message = self.game.sell_item(name)
		self.index = min(self.index, len(self.names()) - 1)

	def draw(self, surface):
		area = self.draw_panel(surface, t('shop_title'))
		split = area.width * 0.45
		self.draw_list(surface, pygame.FRect(area.left, area.top, split, area.height - 36))
		action, name = self.names()[min(self.index, len(self.names()) - 1)]
		left, width = area.left + split + 32, area.width - split - 32
		image = item_icon(self.game, name)
		if image:
			image = pygame.transform.scale(image, (64, 64))
			surface.blit(image, image.get_frect(topright = (area.right, area.top - 6)))
		draw_text(surface, self.fonts['bold'], item_name(name), self.theme['text'], topleft = (left, area.top))
		y = self.draw_paragraph(surface, item_description(name), (left, area.top + 40), width, self.theme['text']) + 16
		price = self.game.shop_price(name) if action == 'buy' else MATERIALS[name]
		draw_text(surface, self.fonts['regular'], t('shop_price' if action == 'buy' else 'shop_sell_price', price = price), self.theme['text'], topleft = (left, y))
		if action == 'buy' and name == self.game.daily_deal():
			draw_text(surface, self.fonts['bold'], t('shop_daily_deal'), COLORS['gold'], topleft = (left, y + 64))
		locked = self.game.next_shop_unlock()
		if locked:
			draw_text(surface, self.fonts['small'], t('shop_more_with_badges', amount = locked), self.theme['muted'], bottomleft = area.bottomleft - vector(0, 30))
		draw_text(surface, self.fonts['regular'], t('item_owned', amount = self.game.inventory.get(name, 0)), self.theme['muted'], topleft = (left, y + 32))
		draw_text(surface, self.fonts['bold'], t('hud_coins', amount = self.game.coins), COLORS['gold'], bottomright = area.bottomright)
		draw_text(surface, self.fonts['regular'], self.message, self.theme['accent'], bottomleft = area.bottomleft)


# Shows a player's three save slots. in_game is False from the title screen (start/continue)
# and True from the menu (save/overwrite/load). Every destructive action asks for confirmation.
class SlotScreen(ListScreen):
	hint = 'hint_slots'
	row_height = 96

	def __init__(self, ui, in_game):
		super().__init__(ui)
		self.in_game = in_game
		self.on_resume()

	def on_resume(self):
		self.slots = self.game.saves.all_slots()

	def get_items(self):
		return [(str(slot['slot']), lambda slot = slot: self.open_slot(slot)) for slot in self.slots]

	def choice(self, title, choices):
		self.ui.push(ChoiceScreen(self.ui, title, choices + [(t('cancel'), self.ui.pop)]))

	# Decides what choosing a slot does depending on whether it is empty, corrupted or in use.
	def open_slot(self, info):
		slot, status = info['slot'], info['status']
		title = t('slot_name', slot = slot)
		delete = (t('slot_delete'), lambda: self.confirm_delete(slot))

		if self.in_game:
			if status == 'empty':
				self.save(slot)
			elif status == 'corrupted':
				self.choice(f"{title}: {t('slot_corrupted')}", [(t('slot_overwrite'), lambda: self.after_choice(self.save, slot)), delete])
			else:
				save_option = t('slot_save') if slot == self.game.active_slot else t('slot_overwrite')
				self.choice(title, [(save_option, lambda: self.after_choice(self.save, slot)), (t('slot_load'), lambda: self.load(slot)), delete])
		else:
			if status == 'empty':
				self.start(slot)
			elif status == 'corrupted':
				self.choice(f"{title}: {t('slot_corrupted')}", [delete])
			else:
				self.choice(title, [(t('slot_continue'), lambda: self.load(slot)), delete])

	def after_choice(self, action, slot):
		self.ui.pop()
		action(slot)

	# Asks "Delete slot n? This cannot be undone." with No as the default option.
	def confirm_delete(self, slot):
		self.ui.pop()
		self.ui.push(ChoiceScreen(self.ui, t('confirm_delete', slot = slot), [
			(t('no'), self.ui.pop),
			(t('yes'), lambda: self.after_choice(self.delete, slot))]))

	# Iteration 13: a new game now opens the starter screen first instead of starting straight away.
	# (Iterations 22-26 added a character screen and the professor's lab; Iteration 27 removed them again.)
	def start(self, slot):
		self.ui.push(StarterScreen(self.ui, slot, self))   # Iteration 27: back to choosing the starter first

	def load(self, slot):
		if not self.game.load_game(slot):
			if self.ui.screens[-1] is not self:
				self.ui.pop()
			self.message = t('slot_load_error')

	def save(self, slot):
		saved = self.game.save_game(slot)
		self.message = t('slot_saved', slot = slot) if saved else t('slot_error')
		self.on_resume()

	def delete(self, slot):
		try:
			self.game.saves.delete_slot(slot)
			self.message = t('slot_deleted', slot = slot)
			if slot == self.game.active_slot:
				self.game.active_slot = None
		except OSError:
			self.message = t('slot_error')
		self.on_resume()

	def draw_row(self, surface, rect, text, selected, picture = None):
		info = self.slots[int(text) - 1]
		text_color = self.theme['selected_text'] if selected else self.theme['text']
		detail_color = self.theme['selected_text'] if selected else self.theme['muted']
		pygame.draw.rect(surface, self.theme['selected'] if selected else self.theme['row'], rect, 0, 6)

		name = t('slot_name', slot = info['slot'])
		if self.in_game and info['slot'] == self.game.active_slot:
			name = f"{name} {t('slot_current')}"
		draw_text(surface, self.fonts['regular'], name, text_color, topleft = rect.topleft + vector(16, 12))

		if info['status'] == 'ok':
			data = info['data']
			draw_text(surface, self.fonts['small'], t('slot_summary',
				party = len(data['party']),
				level = max(monster['level'] for monster in data['party']),
				trainers = len(data['defeated_trainers']),
				time = format_play_time(data['play_time'])), detail_color, topleft = rect.topleft + vector(16, 40))
			draw_text(surface, self.fonts['small'], t('slot_saved_at', date = data['saved_at']), detail_color, topleft = rect.topleft + vector(16, 62))
			self.draw_preview(surface, rect, data)
		else:
			key = 'slot_corrupted' if info['status'] == 'corrupted' else 'slot_empty'
			color = COLORS['red'] if info['status'] == 'corrupted' else detail_color
			draw_text(surface, self.fonts['small'], t(key), color, topleft = rect.topleft + vector(16, 40))

	# Iteration 24: a preview of the save - the trainer's look, the party's icons and the badges
	def draw_preview(self, surface, rect, data):
		import looks
		progress = data.get('progress', {}) if isinstance(data.get('progress'), dict) else {}
		try:
			trainer = looks.frames_for(self.game, looks.validate(progress.get('look')))['down'][0]
			face = trainer.subsurface(trainer.get_bounding_rect())
			face = pygame.transform.scale_by(face, (rect.height - 16) / face.get_height())
			surface.blit(face, face.get_frect(midright = rect.midright - vector(16, 0)))
		except (pygame.error, ValueError, TypeError):
			pass
		right = rect.right - 80
		for number, monster in enumerate(data['party'][:6]):
			name = monster.get('name')
			kind = 'shiny_icons' if monster.get('shiny') else 'icons'
			picture = self.game.monster_frames[kind].get(name)
			if picture:
				picture = pygame.transform.scale(picture, (36, 36))
				surface.blit(picture, picture.get_frect(midright = (right - (5 - number) * 38, rect.centery - 12)))
		badges = [trainer for trainer in BADGE_DATA if trainer in data['defeated_trainers']]
		for number, trainer in enumerate(BADGE_DATA):
			medal = pygame.transform.scale_by(badge_image(BADGE_DATA[trainer]['badge'], trainer in badges, True), 0.24)
			surface.blit(medal, medal.get_frect(midright = (right - (len(BADGE_DATA) - 1 - number) * 26, rect.centery + 26)))

	def draw(self, surface):
		if not self.in_game:
			draw_backdrop(surface, self.game)
		area = self.draw_panel(surface, f"{t('slots_title')} - {self.game.active_profile['username']}")
		self.draw_list(surface, pygame.FRect(area.left, area.top, area.width, area.height - 32))
		draw_text(surface, self.fonts['regular'], self.message, self.theme['accent'], bottomleft = area.bottomleft)


# central menu
# The menu opened with Esc: a list of options, a description of the selected one, and the player card.
class MainMenu(ListScreen):
	row_height = 42

	def get_items(self):
		push = self.ui.push
		return [
			(t('menu_party'), lambda: push(PartyScreen(self.ui))),
			(t('menu_map'), lambda: push(MapScreen(self.ui))),
			(t('menu_badges'), lambda: push(BadgeScreen(self.ui))),
			(t('menu_dex'), lambda: push(DexScreen(self.ui))),
			(t('menu_quests') + (' (!)' if self.game.claimable_quests() else ''), lambda: push(QuestScreen(self.ui))),
			(t('menu_records'), lambda: push(RecordsScreen(self.ui))),   # Iteration 25
			(t('menu_training'), lambda: push(__import__('training').TrainingSetupScreen(self.ui))),   # Iteration 33
			# Iteration 31: the monster box and the clothes colour (they were the desk and the dresser in the bedroom)
			(t('menu_box'), lambda: push(__import__('story_screens').StorageScreen(self.ui))),
			(t('menu_clothes'), lambda: push(__import__('story_screens').WardrobeScreen(self.ui))),
			(t('menu_inventory'), lambda: push(InventoryScreen(self.ui))),
			(t('menu_slots'), lambda: push(SlotScreen(self.ui, in_game = True))),
			(t('menu_settings'), lambda: push(SettingsScreen(self.ui))),
			(t('menu_main_menu'), self.game.back_to_hub)]
	ROW_ICONS = ('monsters', 'map', 'badge', 'book', 'scroll', 'trophy', 'sword', 'box', 'person', 'bag', 'save', 'settings', 'door')   # Iteration 33: every row has its own icon
	def row_picture(self, index, selected):
		return row_icon(self.ROW_ICONS[index], selected) if index < len(self.ROW_ICONS) else None

	# Iteration 19: only things to do with the game being played are here. Account things (password,
	# username, log out), search, players, customer service and policies moved to the main menu
	# after signing in, which "Back to Main Menu" goes to (the game is saved first).

	def draw(self, surface):
		area = self.draw_panel(surface, t('menu_title'))
		split = area.width * 0.45
		self.draw_list(surface, pygame.FRect(area.left, area.top, split, area.height))

		# description of the selected option
		keys = ('party', 'map', 'badges', 'dex', 'quests', 'records', 'training', 'box', 'clothes', 'inventory', 'slots', 'settings', 'main_menu')
		left, width = area.left + split + 32, area.width - split - 32
		bottom = self.draw_paragraph(surface, t(f'desc_{keys[self.index]}'), (left, area.top), width, self.theme['text'])

		# Iteration 18: a trainer card in the style of the starter screen - a coloured header with the
		# player's icon, name and party, then their progress underneath
		slot = self.game.active_slot
		rows = (
			('card_slot', slot if slot else '-'),
			('card_time', format_play_time(self.game.play_time)),
			('card_trainers', len(self.game.defeated_trainers())),
			('card_badges', f'{len(self.game.earned_badges())}/{len(BADGE_DATA)}'),
			('card_coins', self.game.coins))
		card = pygame.FRect(left, max(bottom + 16, area.top + 90), width, 110 + len(rows) * 34)
		pygame.draw.rect(surface, (20, 18, 24), card.move(5, 5), 0, 10)
		pygame.draw.rect(surface, COLORS['dark'], card, 0, 10)
		header = pygame.FRect(card.left, card.top, card.width, 92)
		lead = list(self.game.player_monsters.values())[0]
		pygame.draw.rect(surface, COLORS[lead.element], header, 0, 10, 10, 10, 0, 0)
		surface.set_clip(header.inflate(-10, 0))   # diagonal stripes like the starter card, kept inside the header
		for x in range(int(header.left) - 92, int(header.right) + 92, 26):
			pygame.draw.line(surface, pygame.Color(COLORS[lead.element]).lerp('black', 0.12), (x, header.bottom), (x + 92, header.top), 10)
		surface.set_clip(None)
		surface.blit(icon('person', 4, UI['frame_dark'], UI['frame_light']), (header.left + 16, header.top + 18))
		draw_text(surface, self.fonts['bold'], self.game.active_profile['username'], COLORS['white'], topleft = (header.left + 84, header.top + 18))
		for number, monster in enumerate(self.game.player_monsters.values()):
			icon_surf = self.game.monster_frames['shiny_icons' if monster.shiny else 'icons'][monster.name]
			surface.blit(icon_surf, icon_surf.get_frect(midleft = (header.left + 84 + number * 46, header.top + 64)))
		for index, (key, value) in enumerate(rows):
			y = header.bottom + 26 + index * 34
			draw_text(surface, self.fonts['regular'], t(key), self.theme['muted'], midleft = (card.left + 16, y))
			draw_text(surface, self.fonts['regular'], value, self.theme['text'], midright = (card.right - 16, y))


# Reuses the MonsterIndex from Iteration 4 inside the menu system.
# Iteration 32: choose which 4 of a monster's moves it uses in battle.
class MovesScreen(ListScreen):
	hint = 'hint_moves'

	def __init__(self, ui, monster):
		super().__init__(ui)
		self.monster = monster

	def get_items(self):
		equipped = self.monster.equipped_moves()
		rows = []
		for move in self.monster.known_moves():
			mark = '[x]' if move in equipped else '[ ]'
			rows.append((f'{mark}  {attack_name(move)}  ({t("element_" + ATTACK_DATA[move]["element"])})', lambda move = move: self.toggle(move)))
		return rows

	def toggle(self, move):
		error = self.monster.toggle_move(move)
		self.message = t(error) if error else ''

	def draw(self, surface):
		area = self.draw_panel(surface, t('moves_title', monster = self.monster.display_name))
		split = area.width * 0.48
		self.draw_list(surface, pygame.FRect(area.left, area.top, split, area.height - 36))
		moves = self.monster.known_moves()
		left, width = area.left + split + 32, area.width - split - 32
		y = self.draw_paragraph(surface, t('moves_info'), (left, area.top), width, self.theme['muted'])
		if moves:
			move = moves[min(self.index, len(moves) - 1)]
			data = ATTACK_DATA[move]
			y += 12
			chip = __import__('item_art').type_chip(data['element'], self.fonts['small'], t(f"element_{data['element']}"))
			surface.blit(chip, (left, y))
			y += chip.get_height() + 10
			power = __import__('battle_rules').move_power(move) or '-'   # Iteration 34: 60 instead of 1.2
			for key, value in (('moves_power', power), ('moves_cost', data['cost']), ('moves_accuracy', f"{data.get('accuracy', 100)}%")):
				draw_text(surface, self.fonts['regular'], f'{t(key)}: {value}', self.theme['text'], topleft = (left, y))
				y += 30
			for line in move_effects(data):   # Iteration 32: what the move does
				draw_text(surface, self.fonts['regular'], '- ' + line, self.theme['muted'], topleft = (left, y))
				y += 30
			state = t('moves_equipped') if move in self.monster.equipped_moves() else t('moves_spare')
			draw_text(surface, self.fonts['bold'], state, self.theme['accent'], topleft = (left, y + 6))
		draw_text(surface, self.fonts['regular'], self.message, self.theme['accent'], bottomleft = area.bottomleft)


# Iteration 13: R renames the selected monster and T takes its held item back.
class PartyScreen(Screen):
	use_backdrop = False
	hint = 'hint_party'

	def __init__(self, ui):
		super().__init__(ui)
		self.game.monster_index.index = 0
		self.game.monster_index.selected_index = None
		self.first_frame = True
		self.dt = 0

	def handle_key(self, event):
		monster = self.game.monster_index.monsters[self.game.monster_index.index]
		if event.key == pygame.K_ESCAPE:
			self.back()
		elif event.key == pygame.K_r:
			# Iteration 18: naming a monster that has no nickname yet is free, renaming it later costs coins
			cost = RENAME_MONSTER_COST if monster.nickname else 0
			self.ui.push(NicknameScreen(self.ui, monster, lambda text: self.rename(monster, text), cost = cost))
		elif event.key == pygame.K_t:
			self.message = self.game.take_held_item(monster)
		elif event.key == pygame.K_m:
			self.ui.push(MovesScreen(self.ui, monster))   # Iteration 32: choose the 4 moves used in battle
		elif event.key == pygame.K_b:
			# Iteration 36: the Monster Box - swap monsters between the team of 6 and the box
			self.ui.push(__import__('story_screens').StorageScreen(self.ui))
		elif event.key == pygame.K_x:
			# Iteration 14: release a monster (asks first, No is selected by default)
			index = self.game.monster_index.index
			if len(self.game.player_monsters) <= 1:
				self.message = t('release_last')
			else:
				self.ui.push(ChoiceScreen(self.ui, t('confirm_release', monster = monster.display_name), [
					(t('no'), self.ui.pop),
					(t('yes'), lambda: self.release(index))]))

	def release(self, index):
		self.ui.pop()
		self.message = self.game.release_monster(index)
		party_index = self.game.monster_index
		party_index.index = min(party_index.index, len(self.game.player_monsters) - 1)
		party_index.selected_index = None

	def on_resume(self):
		self.first_frame = True   # the key that closed a pop-up must not also move the list

	# Called by NicknameScreen when the player presses Enter. Returns an error key, or None if it worked.
	# Iteration 14: renaming costs coins (game.rename_monster checks and takes them).
	def rename(self, monster, text):
		error = self.game.rename_monster(monster, text)
		if error:
			return error
		self.ui.pop()
		self.message = t('nickname_set', monster = monster.display_name)
		return None

	def update(self, dt):
		self.dt = dt

	message = ''

	def draw(self, surface):
		index = self.game.monster_index
		# the key that opened this screen must not also select a monster
		if self.first_frame:
			self.first_frame = False
		else:
			index.input()
		surface.blit(index.tint_surf, (0, 0))
		index.display_list()
		index.display_main(self.dt)
		text = self.message or t(self.hint)
		draw_text(surface, self.fonts['regular'], text, COLORS['white'], midbottom = (WINDOW_WIDTH / 2, WINDOW_HEIGHT - 20))


# Lists the items the player owns and lets them use one on a monster.
class InventoryScreen(ListScreen):
	def get_names(self):
		return [name for name, amount in self.game.inventory.items() if amount > 0]

	def get_items(self):
		return [(f"{item_name(name)} x{self.game.inventory[name]}", lambda name = name: self.choose_monster(name)) for name in self.get_names()]

	def row_picture(self, index, selected):
		names = self.get_names()
		return small_item_icon(self.game, names[index]) if index < len(names) else None

	# Iteration 13: held items show what each monster is holding, other items show health and energy.
	def choose_monster(self, name):
		# Iteration 25: key items, field items (Repel, Escape Rope, Party Heal) and materials need no monster
		if name in KEY_ITEMS or name in MATERIALS or 'field' in ITEM_DATA.get(name, {}):
			if name in MATERIALS:
				self.message = t('material_hint')
			else:
				self.message = self.game.use_field_item(name)
			return
		choices = []
		for monster in self.game.player_monsters.values():
			if name in HELD_ITEM_DATA:
				holding = item_name(monster.held_item) if monster.held_item else t('held_none')
				label = f"{monster.display_name}  ({holding})"
			else:
				label = f"{monster.display_name}  HP {int(monster.health)}/{int(monster.get_stat('max_health'))}  EP {int(monster.energy)}/{int(monster.get_stat('max_energy'))}"
			choices.append((label, lambda monster = monster: self.use_item(name, monster)))
		choices.append((t('cancel'), self.ui.pop))
		self.ui.push(ChoiceScreen(self.ui, t('item_choose', item = item_name(name)), choices))

	def use_item(self, name, monster):
		self.ui.pop()
		self.message = self.game.use_item(name, monster)

	def draw(self, surface):
		area = self.draw_panel(surface, t('inventory_title'))
		names = self.get_names()
		if names:
			split = area.width * 0.45
			self.draw_list(surface, pygame.FRect(area.left, area.top, split, area.height - 32))
			name = names[self.index]
			left, width = area.left + split + 32, area.width - split - 32
			image = item_icon(self.game, name)
			if image:
				image = pygame.transform.scale(image, (64, 64))
				surface.blit(image, image.get_frect(topright = (area.right, area.top - 6)))
			draw_text(surface, self.fonts['bold'], item_name(name), self.theme['text'], topleft = (left, area.top))
			self.draw_paragraph(surface, item_description(name), (left, area.top + 40), width, self.theme['text'])
			draw_text(surface, self.fonts['regular'], t('item_owned', amount = self.game.inventory[name]), self.theme['muted'], topleft = (left, area.top + 120))
		else:
			draw_text(surface, self.fonts['regular'], t('inventory_empty'), self.theme['muted'], center = area.center)
		draw_text(surface, self.fonts['regular'], self.message, self.theme['accent'], bottomleft = area.bottomleft)




# Iteration 13 - starter, nickname, map and badge screens

# Carousel shown on a new game. Left/Right move between the three starters, Enter picks one.
# Each card shows the monster's animation, element, stats, moves and evolution line on a background
# in the colour of its element (green for plant, orange for fire, blue for water).
class StarterScreen(Screen):
	hint = 'hint_starter'

	def __init__(self, ui, slot, slot_screen):
		super().__init__(ui)
		self.slot = slot
		self.slot_screen = slot_screen
		self.index = 0
		self.frame_index = 0
		self.slide = 0   # slides the card in from the side when the choice changes
		self.frames = self.game.monster_frames
		# the idle animation of each starter, made 1.6 times bigger once here instead of every frame
		self.big_frames = {name: [pygame.transform.scale_by(frame, 1.6) for frame in self.frames['monsters'][name]['idle']] for name in STARTER_MONSTERS}

	def handle_key(self, event):
		if event.key == pygame.K_ESCAPE:
			if self.slot is not None:   # in the lab the professor is waiting - a starter has to be picked
				self.back()
		elif controls.menu_key(event.key) in (pygame.K_LEFT, pygame.K_RIGHT):
			direction = -1 if controls.menu_key(event.key) == pygame.K_LEFT else 1
			# MOD wraps round so Right on the last starter goes back to the first
			self.index = (self.index + direction) % len(STARTER_MONSTERS)
			self.slide = direction * 120
		elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
			name = STARTER_MONSTERS[self.index]
			self.ui.push(ChoiceScreen(self.ui, t('starter_confirm', monster = name), [
				(t('yes'), lambda: self.choose(name)),
				(t('no'), self.ui.pop)]))

	# After confirming, the player can give the starter a nickname (or press Enter to skip).
	def choose(self, name):
		self.ui.pop()
		self.ui.push(NicknameScreen(self.ui, None, lambda text: self.start(name, text), species = name))

	# Starts the game. Returns an error key for NicknameScreen to show, or None if it worked.
	def start(self, name, text):
		test = Monster(name, STARTER_LEVEL)
		if not test.set_nickname(text):
			return 'nickname_invalid'
		# start_new_game closes every menu screen, so any problem is shown as a message at the top
		if self.game.start_new_game(self.slot, name, test.nickname):
			self.game.toast(t('starter_chosen', monster = test.display_name))
		else:
			self.game.toast(t('slot_error'))
		return None

	def update(self, dt):
		self.frame_index += ANIMATION_SPEED * dt
		self.slide -= self.slide * min(1, 12 * dt)   # ease the card back into the centre

	# Returns a darker version of a colour, used for the patterned background and the card.
	@staticmethod
	def shade(color, amount):
		color = pygame.Color(color)
		return (int(color.r * amount), int(color.g * amount), int(color.b * amount))

	def draw(self, surface):
		name = STARTER_MONSTERS[self.index]
		data = MONSTER_DATA[name]
		element = data['stats']['element']
		color = COLORS[element]

		# background in the element colour with diagonal stripes
		surface.fill(self.shade(color, 0.55))
		for x in range(-WINDOW_HEIGHT, WINDOW_WIDTH, 80):
			pygame.draw.line(surface, self.shade(color, 0.62), (x, WINDOW_HEIGHT), (x + WINDOW_HEIGHT, 0), 30)

		draw_text(surface, self.fonts['dialog'], t('starter_title'), COLORS['white'], midtop = (WINDOW_WIDTH / 2, 24))

		# card
		card = pygame.FRect(0, 0, 860, 540).move_to(center = (WINDOW_WIDTH / 2 + self.slide, WINDOW_HEIGHT / 2 + 20))
		pygame.draw.rect(surface, self.shade(color, 0.3), card.move(6, 6), 0, 16)
		pygame.draw.rect(surface, COLORS['dark'], card, 0, 16)
		top = pygame.FRect(card.left, card.top, card.width, 230)
		pygame.draw.rect(surface, color, top, 0, 16, 16, 16, 0, 0)

		# animated monster (idle frames) bobbing up and down
		frames = self.big_frames[name]
		monster_surf = frames[int(self.frame_index) % len(frames)]
		bob = sin(self.frame_index * 0.8) * 4
		surface.blit(monster_surf, monster_surf.get_frect(center = (top.centerx, top.centery + 4 + bob)))

		draw_text(surface, self.fonts['bold'], name, COLORS['white'], topleft = top.topleft + vector(24, 20))
		draw_text(surface, self.fonts['regular'], t(f'element_{element}'), COLORS['white'], topright = top.topright + vector(-24, 20))
		draw_text(surface, self.fonts['regular'], t('starter_level', level = STARTER_LEVEL), COLORS['white'], bottomleft = top.bottomleft + vector(24, -16))

		# stats at the starting level
		stats = Monster(name, STARTER_LEVEL).get_stats()
		left = pygame.FRect(card.left + 24, top.bottom + 20, card.width / 2 - 36, card.bottom - top.bottom - 40)
		draw_text(surface, self.fonts['regular'], t('starter_stats'), COLORS['white'], topleft = left.topleft)
		highest = {stat: max(MONSTER_DATA[other]['stats'][key] for other in STARTER_MONSTERS) for stat, key in
			(('health', 'max_health'), ('energy', 'max_energy'), ('attack', 'attack'), ('defense', 'defense'), ('speed', 'speed'), ('recovery', 'recovery'))}
		for row, (stat, value) in enumerate(stats.items()):
			y = left.top + 36 + row * 40
			icon = self.frames['ui'][stat]
			surface.blit(icon, icon.get_frect(midleft = (left.left, y + 8)))
			draw_text(surface, self.fonts['small'], f'{stat_name(stat)}  {int(value)}', COLORS['white'], topleft = (left.left + 30, y - 4))
			bar = pygame.FRect(left.left + 30, y + 16, left.width - 40, 6)
			draw_bar(surface, bar, value, highest[stat] * STARTER_LEVEL, stat_color(value / (highest[stat] * STARTER_LEVEL)), COLORS['black'], 2)

		# moves (with the level they unlock at) and evolution line
		right = pygame.FRect(card.centerx + 12, top.bottom + 20, card.width / 2 - 36, left.height)
		draw_text(surface, self.fonts['regular'], t('starter_moves'), COLORS['white'], topleft = right.topleft)
		for row, (level, ability) in enumerate(data['abilities'].items()):
			x = right.left + (row % 2) * right.width / 2
			y = right.top + 34 + (row // 2) * 36
			text = f'{attack_name(ability)} ({t("starter_lvl_short")} {max(1, level)})'
			text_rect = draw_text(surface, self.fonts['small'], text, COLORS['black'], topleft = (x + 6, y + 4))
			pygame.draw.rect(surface, COLORS[ATTACK_DATA[ability]['element']], text_rect.inflate(12, 10), 0, 4)
			draw_text(surface, self.fonts['small'], text, COLORS['black'], topleft = (x + 6, y + 4))

		draw_text(surface, self.fonts['regular'], t('starter_evolution'), COLORS['white'], topleft = (right.left, right.top + 140))
		x, y = right.left, right.top + 200
		for step, (species, level) in enumerate(self.evolution_line(name)):
			icon = self.frames['icons'][species]
			icon_rect = icon.get_frect(midleft = (x, y))
			surface.blit(icon, icon_rect)
			label = species if level is None else f'{species} {level}'
			label_rect = draw_text(surface, self.fonts['small'], label, COLORS['white'], midtop = (icon_rect.centerx, y + 30))
			x = max(icon_rect.right, label_rect.right) + 14
			if step < 2 and MONSTER_DATA[species]['evolve']:
				draw_text(surface, self.fonts['regular'], '>', color, midleft = (x, y))
				x += 24

		# arrows and dots showing which of the three is selected
		for side, x in ((-1, card.left - 40), (1, card.right + 40)):
			points = [(x - side * 14, card.centery - 24), (x + side * 14, card.centery), (x - side * 14, card.centery + 24)]
			pygame.draw.polygon(surface, COLORS['white'], points)
		for dot in range(len(STARTER_MONSTERS)):
			centre = (WINDOW_WIDTH / 2 + (dot - 1) * 28, card.bottom + 26)
			pygame.draw.circle(surface, COLORS['white'], centre, 7 if dot == self.index else 4)

		draw_text(surface, self.fonts['small'], t(self.hint), COLORS['white'], midbottom = (WINDOW_WIDTH / 2, WINDOW_HEIGHT - 8))

	# Returns [(species, level it evolves into it or None), ...] starting from the given monster.
	@staticmethod
	def evolution_line(name):
		line = [(name, None)]
		while MONSTER_DATA[line[-1][0]]['evolve']:
			species, level = MONSTER_DATA[line[-1][0]]['evolve']
			line.append((species, level))
		return line


# Lets the player type a nickname. on_submit is a function that gets the text and returns an error
# key to show (or None when it worked). An empty name keeps the species name.
class NicknameScreen(Screen):
	overlay = True
	hint = 'hint_nickname'

	def __init__(self, ui, monster, on_submit, species = None, cost = 0):
		super().__init__(ui)
		self.cost = cost   # coins it costs (0 when naming the starter)
		self.on_submit = on_submit
		self.species = species or monster.name
		self.text = monster.nickname if monster and monster.nickname else ''
		self.error = None
		self.cursor_time = 0

	def handle_key(self, event):
		if event.key == pygame.K_ESCAPE:
			self.back()
		elif event.key == pygame.K_RETURN:
			self.error = self.on_submit(self.text)
		elif event.key == pygame.K_BACKSPACE:
			self.text = self.text[:-1]
			self.error = None

	def handle_text(self, text):
		text = ''.join(character for character in text if character.isprintable())
		if text:
			self.text = (self.text + text)[:NICKNAME_MAX_LENGTH]
			self.error = None

	def update(self, dt):
		self.cursor_time += dt

	def draw(self, surface):
		rect = pygame.FRect(0, 0, 620, 300).move_to(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
		pygame.draw.rect(surface, self.theme['panel'], rect, 0, 12)
		pygame.draw.rect(surface, self.theme['accent'], rect, 2, 12)
		draw_text(surface, self.fonts['bold'], t('nickname_title', monster = self.species), self.theme['accent'], topleft = rect.topleft + vector(32, 28))

		icon = self.game.monster_frames['icons'][self.species]
		surface.blit(icon, icon.get_frect(topright = rect.topright + vector(-32, 20)))

		box = pygame.FRect(rect.left + 32, rect.top + 90, rect.width - 64, 60)
		pygame.draw.rect(surface, self.theme['row'], box, 0, 6)
		pygame.draw.rect(surface, self.theme['accent'], box, 2, 6)
		cursor = '_' if int(self.cursor_time * 2) % 2 == 0 else ''
		text, color = (self.text + cursor, self.theme['text']) if self.text else (cursor or ' ', self.theme['text'])
		draw_text(surface, self.fonts['dialog'], text, color, midleft = box.midleft + vector(16, 0))
		if not self.text:
			draw_text(surface, self.fonts['regular'], self.species, self.theme['muted'], midleft = box.midleft + vector(40, 0))

		rules = t('nickname_rules', maximum = NICKNAME_MAX_LENGTH)
		if self.cost:
			rules = t('nickname_cost', cost = self.cost, coins = self.game.coins)
		draw_text(surface, self.fonts['small'], rules, self.theme['muted'], topleft = box.bottomleft + vector(0, 12))
		if self.error:
			draw_text(surface, self.fonts['regular'], t(self.error), COLORS['red'], topleft = box.bottomleft + vector(0, 40))
		draw_text(surface, self.fonts['small'], t(self.hint), self.theme['muted'], midbottom = rect.midbottom + vector(0, -16))


# screens from the other menu modules (imported at the end so the modules can refer to each other)
from info_screens import BadgeScreen, DexScreen, MapScreen, QuestScreen, SettingsScreen, RecordsScreen
