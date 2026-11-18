# info_screens.py
# Iteration 18 (split from menus.py): screens that show information - leaderboard, search,
# settings, help documents, the map, badges, the monster index and quests.

from math import sin

from settings import *
from game_data import SPECIAL_ITEMS, ATTACK_DATA, ITEM_DATA, MONSTER_DATA, BADGE_DATA, HELD_ITEM_DATA, QUEST_DATA
from localisation import LANGUAGES, get_document, t, attack_name
from support import draw_bar
from ui_style import UI, pixel_frame, draw_badge, icon
import controls
import item_art

from ui_base import *



# Shows the top 8 players on this computer, highlighting the current player.
class LeaderboardScreen(Screen):
	# Iteration 25: four boards - score, species caught, fastest finish and shiny monsters (Left/Right)
	BOARDS = ('score', 'caught', 'finish', 'shiny')

	def __init__(self, ui):
		super().__init__(ui)
		self.all_entries = self.game.profiles.leaderboard()
		self.board = 0

	@property
	def entries(self):
		board = self.BOARDS[self.board]
		if board == 'score':
			return self.all_entries
		if board == 'finish':
			finished = [entry for entry in self.all_entries if entry.get('finish') is not None]
			return sorted(finished, key = lambda entry: (entry['finish'], entry['username'].casefold()))
		return sorted(self.all_entries, key = lambda entry: (-entry.get(board, 0), entry['username'].casefold()))

	def handle_key(self, event):
		key = controls.menu_key(event.key)
		if key in (pygame.K_LEFT, pygame.K_RIGHT):
			self.board = (self.board + (1 if key == pygame.K_RIGHT else -1)) % len(self.BOARDS)
		elif event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
			self.back()

	def value(self, entry):
		import records
		board = self.BOARDS[self.board]
		if board == 'finish':
			return records.format_time(entry['finish'])
		return entry.get(board, 0)

	def draw(self, surface):
		area = self.draw_panel(surface, t('leaderboard_title') + '  -  ' + t(f'board_{self.BOARDS[self.board]}'))
		columns = ((0, 'leaderboard_rank'), (0.14, 'leaderboard_player'), (0.5, f'board_{self.BOARDS[self.board]}'), (0.66, 'leaderboard_trainers'), (0.86, 'leaderboard_level'))
		for ratio, key in columns:
			draw_text(surface, self.fonts['small'], t(key), self.theme['muted'], topleft = (area.left + 16 + ratio * area.width, area.top))
		# arrows to show Left/Right changes the board
		for number, board in enumerate(self.BOARDS):
			pygame.draw.circle(surface, UI['gold'] if number == self.board else self.theme['row'], (area.right - 80 + number * 20, area.top - 30), 6)

		entries = self.entries
		if not entries:
			draw_text(surface, self.fonts['regular'], t('leaderboard_empty'), self.theme['muted'], center = area.center)

		for rank, entry in enumerate(entries[:8], start = 1):
			rect = pygame.FRect(area.left, area.top + 28 + (rank - 1) * 44, area.width, 38)
			current = entry['id'] == self.game.active_profile['id']
			pygame.draw.rect(surface, self.theme['selected'] if current else self.theme['row'], rect, 0, 6)
			color = self.theme['selected_text'] if current else self.theme['text']
			values = (rank, entry['username'], self.value(entry), entry['trainers'], entry['top_level'])
			for (ratio, _), value in zip(columns, values):
				draw_text(surface, self.fonts['regular'], value, color, midleft = (area.left + 16 + ratio * area.width, rect.centery))
			if rank <= 3:   # Iteration 20: gold, silver and bronze medals for the top three
				picture = item_art.medal(rank)
				surface.blit(picture, picture.get_frect(midleft = (area.left + 40, rect.centery)))

		draw_text(surface, self.fonts['small'], t('leaderboard_note') + '   ' + t('board_hint'), self.theme['muted'], bottomleft = area.bottomleft)


# Search monsters, attacks and items by name or element as the player types.
class SearchScreen(ListScreen):
	hint = 'hint_search'
	row_height = 36

	def __init__(self, ui):
		super().__init__(ui)
		self.query = ''
		self.entries = self.build_entries()
		self.results = self.entries

	# Builds one searchable entry for every monster, attack and item from the game data.
	def build_entries(self):
		entries = []
		owned = [monster.name for monster in self.game.player_monsters.values()]   # species, not nicknames

		for name, data in MONSTER_DATA.items():
			stats = data['stats']
			evolve = data['evolve']
			entries.append({
				'name': name,
				'category': t('category_monster'),
				'keywords': f"{name} {stats['element']}",
				'details': [
					t('search_element', value = t(f"element_{stats['element']}")),
					t('search_stats', health = stats['max_health'], energy = stats['max_energy'], attack = stats['attack'], defense = stats['defense'], speed = stats['speed']),
					t('search_abilities', value = ', '.join(attack_name(attack) for attack in data['abilities'].values())),
					t('search_evolves', monster = evolve[0], level = evolve[1]) if evolve else t('search_no_evolution'),
					t('search_owned', amount = owned.count(name))]})

		for name, data in ATTACK_DATA.items():
			entries.append({
				'name': attack_name(name),
				'category': t('category_attack'),
				'keywords': f"{name} {attack_name(name)} {data['element']} {t(f'element_{data['element']}')}",
				'details': [
					t('search_element', value = t(f"element_{data['element']}")),
					t('search_power', value = abs(data['amount'])),
					t('search_cost', value = data['cost']),
					t(f"search_target_{data['target']}")]})

		for name in list(ITEM_DATA) + list(HELD_ITEM_DATA) + list(SPECIAL_ITEMS):
			entries.append({
				'name': item_name(name),
				'category': t('category_item'),
				'keywords': f"{name} {item_name(name)}",
				'details': [item_description(name), t('item_owned', amount = self.game.inventory.get(name, 0))]})

		return entries

	def get_items(self):
		return [(f"{entry['name']}  ({entry['category']})", lambda: None) for entry in self.results]

	# Keeps only entries whose keywords contain the search text (case is ignored).
	def filter_results(self):
		query = self.query.strip().casefold()
		self.results = [entry for entry in self.entries if query in entry['keywords'].casefold()]
		self.index, self.scroll = 0, 0

	def handle_key(self, event):
		if event.key in (pygame.K_ESCAPE, pygame.K_UP, pygame.K_DOWN):
			super().handle_key(event)
		elif event.key == pygame.K_BACKSPACE:
			self.query = self.query[:-1]
			self.filter_results()

	def handle_text(self, text):
		text = ''.join(character for character in text if character.isprintable())
		if text and len(self.query) < 24:
			self.query = (self.query + text)[:24]
			self.filter_results()

	def draw(self, surface):
		area = self.draw_panel(surface, t('search_title'))
		box = pygame.FRect(area.topleft, (area.width, 44))
		pygame.draw.rect(surface, self.theme['row'], box, 0, 6)
		pygame.draw.rect(surface, self.theme['accent'], box, 2, 6)
		text, color = (self.query, self.theme['text']) if self.query else (t('search_prompt'), self.theme['muted'])
		draw_text(surface, self.fonts['regular'], text, color, midleft = box.midleft + vector(16, 0))

		top = box.bottom + 16
		height = area.bottom - top
		if not self.results:
			draw_text(surface, self.fonts['regular'], t('search_none'), self.theme['muted'], midtop = (area.centerx, top + 40))
			return

		split = area.width * 0.45
		self.draw_list(surface, pygame.FRect(area.left, top, split, height))
		entry = self.results[self.index]
		left, width = area.left + split + 32, area.width - split - 32
		draw_text(surface, self.fonts['bold'], entry['name'], self.theme['text'], topleft = (left, top))
		y = top + 40
		for detail in entry['details']:
			y = self.draw_paragraph(surface, detail, (left, y), width, self.theme['text']) + 8


# Brightness, night mode, language, sound and music. Left/Right change the selected setting.
class SettingsScreen(Screen):
	hint = 'hint_settings'
	rows = ('brightness', 'night_mode', 'language', 'music_volume', 'sound_volume', 'minimap', 'control_hints', 'intro',
	        'colour_blind', 'large_text', 'difficulty', 'autosave', 'encounter_rate', 'speedrun_timer', 'controls')   # Iteration 24/25: the last 7
	ROW_ICONS = {'brightness': 'sun', 'night_mode': 'moon', 'language': 'book', 'music_volume': 'note', 'sound_volume': 'sound',
	             'minimap': 'map', 'control_hints': 'keyboard', 'intro': 'film', 'colour_blind': 'eye', 'large_text': 'text',
	             'difficulty': 'sword', 'autosave': 'clock', 'encounter_rate': 'grass', 'speedrun_timer': 'hourglass', 'controls': 'pad'}   # Iteration 20
	visible = 9   # Iteration 25: the list scrolls when there are more rows than fit

	def __init__(self, ui):
		super().__init__(ui)
		self.index = 0
		self.top = 0

	def handle_key(self, event):
		if event.key == pygame.K_ESCAPE:
			self.back()
		elif controls.menu_key(event.key) == pygame.K_UP:
			self.index = (self.index - 1) % len(self.rows)
		elif controls.menu_key(event.key) == pygame.K_DOWN:
			self.index = (self.index + 1) % len(self.rows)
		elif controls.menu_key(event.key) in (pygame.K_LEFT, pygame.K_RIGHT) or event.key in (pygame.K_RETURN, pygame.K_SPACE):
			self.change(-1 if controls.menu_key(event.key) == pygame.K_LEFT else 1)
		# keep the selected row on screen
		self.top = min(max(self.top, self.index - self.visible + 1), self.index)

	# tapping a setting changes it
	def handle_click(self, pos):
		for rect, index in getattr(self, 'row_rects', []):
			if rect.collidepoint(pos):
				self.index = index
				self.change(1)

	def change(self, direction):
		import options
		row = self.rows[self.index]
		preferences = self.game.preferences
		match row:
			case 'brightness': preferences.change_brightness(direction)
			case 'language': preferences.cycle_language(direction)
			case 'music_volume' | 'sound_volume': preferences.change_volume(row, direction)
			case 'intro': preferences.cycle_intro(direction)
			case 'difficulty': preferences.cycle('difficulty', options.DIFFICULTIES, direction)
			case 'autosave': preferences.cycle('autosave', options.AUTOSAVE_CHOICES, direction)
			case 'encounter_rate': preferences.cycle('encounter_rate', options.ENCOUNTER_RATES, direction)
			case 'controls': self.ui.push(KeysScreen(self.ui))
			case 'colour_blind':
				preferences.toggle(row)
				options.apply_colour_blind(preferences[row])
			case 'large_text':
				preferences.toggle(row)
				options.build_fonts(self.game.fonts, preferences[row])
			case _: preferences.toggle(row)
		preferences.apply_audio(self.game.audio)

	def value_of(self, row):
		preferences = self.game.preferences
		match row:
			case 'language': return LANGUAGES[preferences['language']]
			case 'brightness': return f"{preferences['brightness']}%"
			case 'music_volume' | 'sound_volume': return f'{preferences[row]}%'
			case 'intro': return t(f"intro_mode_{preferences['intro']}")
			case 'difficulty': return t(f"difficulty_{preferences['difficulty']}")
			case 'autosave': return t('off') if not preferences['autosave'] else t('autosave_minutes', minutes = preferences['autosave'] // 60)
			case 'encounter_rate': return t(f"rate_{preferences['encounter_rate']}")
			case 'controls': return '>'
		return t('on') if preferences[row] else t('off')

	def draw(self, surface):
		area = self.draw_panel(surface, t('settings_title'))
		preferences = self.game.preferences
		step = min(56, (area.height - 30) / self.visible)
		self.row_rects = []
		for position, index in enumerate(range(self.top, min(len(self.rows), self.top + self.visible))):
			row = self.rows[index]
			rect = pygame.FRect(area.left, area.top + position * step, area.width - 18, step - 8)
			self.row_rects.append((rect, index))
			selected = index == self.index
			self.draw_row(surface, rect, t(f'setting_{row}'), selected, row_icon(self.ROW_ICONS[row], selected))
			color = self.theme['selected_text'] if selected else self.theme['text']
			value = self.value_of(row)
			if row in ('brightness', 'music_volume', 'sound_volume'):
				bar = pygame.FRect(0, 0, 200, 10).move_to(midright = rect.midright + vector(-90, 0))
				low, high = (BRIGHTNESS_MIN, BRIGHTNESS_MAX) if row == 'brightness' else (0, 100)
				draw_bar(surface, bar, preferences[row] - low, high - low, self.theme['accent'], COLORS['black'], 2)
			elif row == 'language':
				# Iteration 20: the language's flag next to its name
				picture = item_art.flag(preferences['language'])
				width = self.fonts['regular'].size(value)[0]
				surface.blit(picture, picture.get_frect(midright = rect.midright + vector(-28 - width, 0)))
			elif row == 'colour_blind':
				# a strip of the type colours, so the change can be seen straight away
				for i, element in enumerate(('fire', 'water', 'plant', 'poison', 'bug', 'psychic')):
					pygame.draw.rect(surface, item_art.TYPE_COLOURS[element], (rect.right - 210 + i * 18, rect.centery - 7, 14, 14), 0, 3)
			draw_text(surface, self.fonts['regular'], value, color, midright = rect.midright + vector(-16, 0))
		# a scroll bar on the right
		track = pygame.FRect(area.right - 8, area.top, 6, self.visible * step - 8)
		pygame.draw.rect(surface, self.theme['row'], track, 0, 3)
		thumb = track.copy()
		thumb.height = track.height * self.visible / len(self.rows)
		thumb.top = track.top + (track.height - thumb.height) * self.top / max(1, len(self.rows) - self.visible)
		pygame.draw.rect(surface, self.theme['accent'], thumb, 0, 3)
		self.draw_paragraph(surface, t(f'setting_{self.rows[self.index]}_desc'), (area.left, area.top + self.visible * step + 4), area.width, self.theme['muted'])


# Iteration 25: choose the second key for moving and sprinting (the arrow keys and Left Shift always work).
class KeysScreen(Screen):
	hint = 'hint_keys'

	def __init__(self, ui):
		super().__init__(ui)
		self.index = 0
		self.waiting = False
		self.message = ''

	def actions(self):
		import options
		return list(options.REBINDABLE) + ['reset']

	def handle_key(self, event):
		import options
		keys = dict(self.game.preferences['keys'])
		if self.waiting:
			self.waiting = False
			if event.key == pygame.K_ESCAPE:
				self.message = ''
				return
			action = self.actions()[self.index]
			error = options.rebind(keys, action, event.key)
			if error:
				self.message = t(error)
				return
			self.save(keys)
			self.message = t('keys_set', action = t(f'action_{action}'), key = pygame.key.name(event.key).upper())
			return
		if event.key == pygame.K_ESCAPE:
			self.back()
		elif controls.menu_key(event.key) in (pygame.K_UP, pygame.K_DOWN) and event.key in (pygame.K_UP, pygame.K_DOWN):
			self.index = (self.index + (1 if event.key == pygame.K_DOWN else -1)) % len(self.actions())
		elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
			if self.actions()[self.index] == 'reset':
				self.save(dict(options.DEFAULT_KEYS))
				self.message = t('keys_reset')
			else:
				self.waiting = True
				self.message = t('keys_press')

	def save(self, keys):
		import options
		self.game.preferences.set('keys', keys)
		options.apply_keys(keys)

	def draw(self, surface):
		area = self.draw_panel(surface, t('keys_title'))
		keys = self.game.preferences['keys']
		arrows = {'up': 'UP', 'down': 'DOWN', 'left': 'LEFT', 'right': 'RIGHT', 'sprint': 'L SHIFT'}
		for index, action in enumerate(self.actions()):
			rect = pygame.FRect(area.left, area.top + index * 58, area.width, 48)
			selected = index == self.index
			self.draw_row(surface, rect, t(f'action_{action}'), selected, row_icon('pad' if action != 'reset' else 'settings', selected))
			if action != 'reset':
				for offset, label in ((-16, pygame.key.name(keys[action]).upper() if not (self.waiting and selected) else '...'), (-160, arrows[action])):
					cap = item_art.key_cap(label, self.fonts['small'])
					surface.blit(cap, cap.get_frect(midright = rect.midright + vector(offset, 0)))
		draw_text(surface, self.fonts['regular'], self.message, self.theme['accent'], bottomleft = area.bottomleft)
		self.draw_paragraph(surface, t('keys_note'), (area.left, area.top + len(self.actions()) * 58 + 10), area.width, self.theme['muted'])


# Lists the documents in the customer service or policy section.
class DocumentMenu(ListScreen):
	def __init__(self, ui, title_key, document_keys):
		super().__init__(ui)
		self.title_key = title_key
		self.document_keys = document_keys

	def get_items(self):
		return [(t(key), lambda key = key: self.ui.push(DocumentScreen(self.ui, key))) for key in self.document_keys]

	def draw(self, surface):
		if not self.game.playing:
			draw_backdrop(surface, self.game)
		area = self.draw_panel(surface, t(self.title_key))
		self.draw_list(surface, area)


# Shows one document with word wrapping and scrolling.
class DocumentScreen(Screen):
	hint = 'hint_document'
	line_height = 26

	def __init__(self, ui, key):
		super().__init__(ui)
		self.key = key
		self.scroll = 0
		self.lines = None

	def build_lines(self, width):
		lines = []
		for heading, body in get_document(self.key):
			for line in wrap_text(self.fonts['regular'], heading, width):
				lines.append((line, 'accent'))
			for line in wrap_text(self.fonts['regular'], body.format(email = SUPPORT_EMAIL), width):
				lines.append((line, 'text'))
			lines.append(('', 'text'))
		return lines[:-1]

	def handle_key(self, event):
		if event.key == pygame.K_ESCAPE:
			self.back()
		elif event.key == pygame.K_UP:
			self.scroll = max(0, self.scroll - 1)
		elif event.key == pygame.K_DOWN:
			self.scroll = min(self.max_scroll, self.scroll + 1)

	def draw(self, surface):
		if not self.game.playing:
			draw_backdrop(surface, self.game)
		area = self.draw_panel(surface, t(self.key))
		self.lines = self.lines or self.build_lines(area.width - 8)

		visible = int(area.height // self.line_height)
		self.max_scroll = max(0, len(self.lines) - visible)
		for row, (line, color) in enumerate(self.lines[self.scroll:self.scroll + visible]):
			draw_text(surface, self.fonts['regular'], line, self.theme[color], topleft = (area.left, area.top + row * self.line_height))

	max_scroll = 0


# Returns the customer service menu (FAQs, troubleshooting, contact).
def support_screen(ui):
	return DocumentMenu(ui, 'support_title', ('support_faq', 'support_troubleshooting', 'support_contact'))

# Returns the policies menu (terms, privacy, data usage).
def policy_screen(ui):
	return DocumentMenu(ui, 'policy_title', ('policy_terms', 'policy_privacy', 'policy_data'))


# map markers
# colours used on the map for how strong a trainer is compared with the player's best monster
DIFFICULTY_COLORS = {'easy': '#5fd35f', 'close': '#f8c050', 'hard': '#f03131', 'beaten': '#8d8a96'}

# Returns 'easy', 'close' or 'hard' for a trainer, by comparing levels (used for the marker colour).
def trainer_difficulty(game, character_id):
	difference = game.trainer_level(character_id) - game.party_level()
	if difference <= 0:
		return 'easy'
	return 'close' if difference <= 5 else 'hard'

# Returns the map position the player should head to next: the next badge trainer if they are on
# this map, otherwise the entrance that leads towards them. Returns None when every badge is earned.
def next_target(game):
	trainer = game.next_badge_trainer()
	if trainer is None or trainer not in game.trainer_locations:
		return None
	map_name, position = game.trainer_locations[trainer]
	if map_name == game.current_map:
		for character in game.character_sprites:
			if character.character_id == trainer:
				return vector(character.rect.center)
		return vector(position)
	# the trainer is on another map - point at the door to that map (or the exit back to the world)
	wanted = map_name if game.current_map == 'world' else 'world'
	for sprite in game.transition_sprites:
		if sprite.target[0] == wanted:
			return vector(sprite.rect.center)
	return None

# Draws trainers, the next target and the player on a minimap.
# Parameters: game, surface, scale (map pixels -> minimap pixels), offset (where map (0, 0) is drawn),
# clip (rectangle markers must be inside), small (True for the corner minimap - smaller markers).
def draw_minimap_markers(game, surface, scale, offset, clip, small = False):
	radius = 5 if small else 8
	for character in game.character_sprites:
		if character.nurse or not character.character_id or not character.monsters:
			continue   # Iteration 25: the people around town are not trainers
		pos = vector(character.rect.center) * scale + offset
		if not clip.collidepoint(pos):
			continue
		if character.character_data['defeated']:
			# beaten trainers are crossed out with an X
			color = DIFFICULTY_COLORS['beaten']
			pygame.draw.line(surface, color, pos - (radius, radius), pos + (radius, radius), 3)
			pygame.draw.line(surface, color, pos + (-radius, radius), pos + (radius, -radius), 3)
		else:
			color = DIFFICULTY_COLORS[trainer_difficulty(game, character.character_id)]
			if not small:
				# Iteration 20: on the big map each trainer is shown by their face, ringed in the difficulty colour
				head = item_art.trainer_head(character.frames, 22)
				pygame.draw.circle(surface, color, pos, 15)
				pygame.draw.circle(surface, COLORS['black'], pos, 15, 2)
				surface.blit(head, head.get_frect(center = pos))
				if character.character_id in BADGE_DATA:
					pygame.draw.circle(surface, COLORS['gold'], pos, 19, 2)
				continue
			pygame.draw.circle(surface, COLORS['black'], pos, radius + 2)
			pygame.draw.circle(surface, color, pos, radius)
			if character.character_id in BADGE_DATA:
				pygame.draw.circle(surface, COLORS['gold'], pos, radius + 4, 2)

	# pulsing ring on where to go next
	target = next_target(game)
	if target is not None:
		pos = target * scale + offset
		pos.x = max(clip.left + 6, min(clip.right - 6, pos.x))
		pos.y = max(clip.top + 6, min(clip.bottom - 6, pos.y))
		pulse = (sin(pygame.time.get_ticks() / 150) + 1) * 3
		pygame.draw.circle(surface, COLORS['gold'], pos, radius + 6 + pulse, 3)

	# player
	pos = vector(game.player.rect.center) * scale + offset
	if clip.collidepoint(pos):
		pygame.draw.circle(surface, COLORS['black'], pos, radius + 1)
		pygame.draw.circle(surface, COLORS['white'], pos, radius - 1)


# Full map of the current area (opened with M or from the menu). Shows the player, every trainer
# coloured by difficulty, an X on trainers already beaten, the entrances to the gyms and a gold
# ring on where to go next, with a key on the right.
class MapScreen(Screen):
	hint = 'hint_map'
	# entrance target -> text key for its label
	PLACES = {'house': 'place_house', 'hospital': 'place_hospital', 'hospital2': 'place_hospital',
	          'plant': 'place_plant', 'fire': 'place_fire', 'water': 'place_water', 'world': 'place_world'}

	def handle_key(self, event):
		if event.key in (pygame.K_ESCAPE, pygame.K_m, pygame.K_RETURN):
			self.back()

	def draw(self, surface):
		area = self.draw_panel(surface, t('map_title', place = t(self.PLACES.get(self.game.current_map, 'place_world'))))
		map_surf, scale = self.game.get_minimap(self.game.current_map)

		# the map picture is shrunk if needed so it fits on the left of the panel
		fit = min(1, area.height / map_surf.get_height(), area.width * 0.62 / map_surf.get_width())
		if fit < 1:
			map_surf = pygame.transform.smoothscale(map_surf, (int(map_surf.get_width() * fit), int(map_surf.get_height() * fit)))
			scale *= fit
		map_rect = map_surf.get_frect(midleft = area.midleft)
		surface.blit(map_surf, map_rect)
		pygame.draw.rect(surface, self.theme['row'], map_rect.inflate(6, 6), 3, 4)

		# entrance labels
		for sprite in self.game.transition_sprites:
			key = self.PLACES.get(sprite.target[0])
			if key:
				pos = vector(sprite.rect.center) * scale + map_rect.topleft
				text = t(key)
				# Iteration 16: gyms show the levels of their trainers so the player knows how strong to be
				levels = [self.game.trainer_level(trainer) for trainer, (map_name, _) in self.game.trainer_locations.items() if map_name == sprite.target[0]]
				if levels and sprite.target[0] != self.game.current_map:
					text = f'{text} (Lv {min(levels)}-{max(levels)})'
				label = draw_text(surface, self.fonts['small'], text, COLORS['black'], midbottom = pos + vector(0, -8))
				pygame.draw.rect(surface, COLORS['white'], label.inflate(8, 4), 0, 4)
				draw_text(surface, self.fonts['small'], text, COLORS['black'], midbottom = pos + vector(0, -8))

		draw_minimap_markers(self.game, surface, scale, vector(map_rect.topleft), map_rect)

		# key
		left = map_rect.right + 32
		width = area.right - left
		y = area.top
		trainer = self.game.next_badge_trainer()
		if trainer:
			location = self.game.trainer_locations.get(trainer, ('world', None))[0]
			y = self.draw_paragraph(surface, t('map_next', badge = BADGE_DATA[trainer]['badge'], level = self.game.trainer_level(trainer), place = t(self.PLACES.get(location, 'place_world'))), (left, y), width, self.theme['accent']) + 12
		else:
			y = self.draw_paragraph(surface, t('map_all_badges'), (left, y), width, self.theme['accent']) + 12
		y = self.draw_paragraph(surface, t('map_your_level', level = self.game.party_level()), (left, y), width, self.theme['text']) + 16

		rows = (('easy', 'map_easy'), ('close', 'map_close'), ('hard', 'map_hard'))
		for difficulty, key in rows:
			pygame.draw.circle(surface, DIFFICULTY_COLORS[difficulty], (left + 8, y + 10), 8)
			y = self.draw_paragraph(surface, t(key), (left + 26, y), width - 26, self.theme['text']) + 10
		color = DIFFICULTY_COLORS['beaten']
		pygame.draw.line(surface, color, (left, y + 2), (left + 16, y + 18), 3)
		pygame.draw.line(surface, color, (left, y + 18), (left + 16, y + 2), 3)
		y = self.draw_paragraph(surface, t('map_beaten'), (left + 26, y), width - 26, self.theme['text']) + 10
		pygame.draw.circle(surface, COLORS['gold'], (left + 8, y + 10), 10, 2)
		y = self.draw_paragraph(surface, t('map_badge'), (left + 26, y), width - 26, self.theme['text']) + 10
		pygame.draw.circle(surface, COLORS['gold'], (left + 8, y + 10), 12, 3)
		y = self.draw_paragraph(surface, t('map_target'), (left + 26, y), width - 26, self.theme['text']) + 10
		pygame.draw.circle(surface, COLORS['white'], (left + 8, y + 10), 6)
		self.draw_paragraph(surface, t('map_you'), (left + 26, y), width - 26, self.theme['text'])


# Shows every badge: earned ones in gold with the trainer's reward, missing ones greyed out.
# Iteration 19 redesign: every badge has its own colour and picture (a leaf, a flame, a snowflake...),
# gym leader badges are hexagons, earned badges shine, and the arrow keys pick a badge to see who
# gives it and what the reward is.
class BadgeScreen(Screen):
	hint = 'hint_badges'
	columns = 5

	def __init__(self, ui):
		super().__init__(ui)
		self.index = 0
		self.time = 0

	def handle_key(self, event):
		key = controls.menu_key(event.key)
		count = len(BADGE_DATA)
		if key == pygame.K_RIGHT:
			self.index = (self.index + 1) % count
		elif key == pygame.K_LEFT:
			self.index = (self.index - 1) % count
		elif key in (pygame.K_DOWN, pygame.K_UP):
			self.index = (self.index + self.columns) % count
		elif event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
			self.back()

	def update(self, dt):
		self.time += dt

	def draw(self, surface):
		earned = self.game.earned_badges()
		area = self.draw_panel(surface, t('badges_title', amount = len(earned), total = len(BADGE_DATA)))
		width = area.width / self.columns
		for number, (trainer, data) in enumerate(BADGE_DATA.items()):
			centre = vector(area.left + (number % self.columns + 0.5) * width, area.top + 76 + (number // self.columns) * 168)
			got = trainer in earned
			selected = number == self.index
			if selected:
				pixel_frame(surface, pygame.FRect(0, 0, width - 16, 160).move_to(center = centre + vector(0, 10)), 4, fill = (255, 255, 255, 18))
			bob = sin(self.time * 4) * 3 if selected and got else 0
			# Iteration 24: when the case opens, the badges drop into place one after another
			appear = max(0, min(1, (self.time - 0.35 - number * 0.07) / 0.25))
			if appear <= 0:
				continue
			bob -= (1 - appear) ** 2 * 50
			draw_badge(surface, centre + vector(0, bob - 6), data['badge'], got, trainer in GYM_LEADERS, self.time + number * 0.7)
			text_color = self.theme['text'] if got else self.theme['muted']
			draw_text(surface, self.fonts['regular'], t('badge_name', badge = data['badge']), text_color, midtop = centre + vector(0, 58))

		# details of the selected badge along the bottom
		trainer, data = list(BADGE_DATA.items())[self.index]
		got = trainer in earned
		y = area.top + 76 + 2 * 168 - 40
		pygame.draw.line(surface, self.theme['muted'], (area.left, y - 12), (area.right, y - 12), 2)
		who = t('badge_gym_leader') if trainer in GYM_LEADERS else t('badge_trainer')
		draw_text(surface, self.fonts['bold'], t('badge_name', badge = data['badge']) + f'  -  {who}', COLORS['gold'] if got else self.theme['text'], topleft = (area.left, y))
		if got:
			rewards = [item_name(data['reward']['held'])] + [f'{item_name(name)} x{amount}' for name, amount in data['reward']['items'].items()]
			detail = t('badge_earned_detail', rewards = ', '.join(rewards))
		else:
			detail = t('badge_locked_detail', level = self.game.trainer_level(trainer))
		draw_text(surface, self.fonts['regular'], detail, self.theme['text'], topleft = (area.left, y + 34))
		# Iteration 24: the two doors of the badge case slide open
		opening = min(1, self.time / 0.45)
		if opening < 1:
			gap = (1 - (1 - opening) ** 3) * area.width / 2
			surface.set_clip(area.inflate(16, 16))
			for side in (-1, 1):
				door = pygame.FRect(0, 0, area.width / 2 + 8, area.height + 16)
				if side < 0:
					door.topright = (area.centerx - gap, area.top - 8)
				else:
					door.topleft = (area.centerx + gap, area.top - 8)
				pygame.draw.rect(surface, (110, 30, 40), door, 0, 6)
				pygame.draw.rect(surface, UI['gold'], door, 3, 6)
				knob = door.midright - vector(18, 0) if side < 0 else door.midleft + vector(18, 0)
				pygame.draw.circle(surface, UI['gold'], knob, 7)
			surface.set_clip(None)


# Iteration 16 - monster index (dex) and quests

# Every species in a grid: never seen = dark shape and ???, seen = picture, caught = picture with a
# gold corner. The right side shows details and how complete the index is.
class DexScreen(Screen):
	hint = 'hint_dex'
	columns = 4

	FILTERS = ('all', 'caught', 'missing', 'normal', 'fire', 'water', 'plant', 'ice', 'poison', 'bug', 'flying', 'psychic', 'rock')   # Iteration 25
	visible_rows = 5

	def __init__(self, ui):
		super().__init__(ui)
		self.index = 0
		self.filter = 0
		self.top_row = 0
		self.species = list(MONSTER_DATA)
		# a black shape of each icon for monsters that have not been seen yet
		self.shadows = {}
		for name, picture in self.game.monster_frames['icons'].items():
			shadow = pygame.mask.from_surface(picture).to_surface(setcolor = (20, 20, 24), unsetcolor = (0, 0, 0, 0))
			self.shadows[name] = shadow

	# Iteration 25: the species shown with the current filter. A type filter only shows monsters you have
	# seen (so it does not give away unseen monsters' types).
	def shown(self):
		name = self.FILTERS[self.filter]
		game = self.game
		known = game.seen | game.caught
		if name == 'all':
			return self.species
		if name == 'caught':
			return [s for s in self.species if s in game.caught]
		if name == 'missing':
			return [s for s in self.species if s not in game.caught]
		return [s for s in self.species if s in known and name in (MONSTER_DATA[s]['stats']['element'], MONSTER_DATA[s]['stats'].get('element2'))]

	def handle_key(self, event):
		key = controls.menu_key(event.key)
		count = max(1, len(self.shown()))
		if event.key == pygame.K_ESCAPE:
			self.back()
		elif event.key in (pygame.K_f, pygame.K_TAB):
			self.filter = (self.filter + 1) % len(self.FILTERS)
			self.index, self.top_row = 0, 0
		elif key in (pygame.K_LEFT, pygame.K_RIGHT):
			self.index = (self.index + (1 if key == pygame.K_RIGHT else -1)) % count
		elif key in (pygame.K_UP, pygame.K_DOWN):
			self.index = (self.index + (self.columns if key == pygame.K_DOWN else -self.columns)) % count
		row = self.index // self.columns
		self.top_row = min(max(self.top_row, row - self.visible_rows + 1), row)

	def handle_click(self, pos):
		for rect, index in getattr(self, 'tile_rects', []):
			if rect.collidepoint(pos):
				self.index = index

	def draw(self, surface):
		game = self.game
		area = self.draw_panel(surface, t('dex_title', caught = len(game.caught), seen = len(game.seen | game.caught), total = len(self.species)))
		size = 82   # Iteration 25: smaller so 5 rows fit above the key hints
		self.tile_rects = []
		shown = self.shown()
		draw_text(surface, self.fonts['small'], t('dex_filter', filter = t(f'dex_filter_{self.FILTERS[self.filter]}') if self.FILTERS[self.filter] in ('all', 'caught', 'missing') else t(f'element_{self.FILTERS[self.filter]}'), amount = len(shown)), COLORS['gold'], bottomleft = area.topleft + vector(0, -6))
		for number, name in enumerate(shown):
			row = number // self.columns - self.top_row
			if not 0 <= row < self.visible_rows:
				continue
			rect = pygame.FRect(area.left + (number % self.columns) * (size + 10), area.top + 8 + row * (size + 8), size, size)
			self.tile_rects.append((rect, number))
			selected = number == self.index
			pygame.draw.rect(surface, self.theme['selected'] if selected else self.theme['row'], rect, 0, 8)
			if name in game.caught:
				pygame.draw.polygon(surface, COLORS['gold'], [rect.topright + vector(-24, 0), rect.topright, rect.topright + vector(0, 24)])
			icon = game.monster_frames['icons'][name] if name in game.seen or name in game.caught else self.shadows[name]
			surface.blit(icon, icon.get_frect(center = rect.center + vector(0, -8)))
			draw_text(surface, self.fonts['small'], f'{self.species.index(name) + 1:02}', self.theme['selected_text'] if selected else self.theme['muted'], bottomleft = rect.bottomleft + vector(6, -4))
		if not shown:
			draw_text(surface, self.fonts['regular'], t('dex_none'), self.theme['muted'], topleft = area.topleft + vector(0, 20))
			return

		# details of the selected species
		name = shown[min(self.index, len(shown) - 1)]
		left = area.left + self.columns * (size + 10) + 24
		width = area.right - left
		known = name in game.seen or name in game.caught
		draw_text(surface, self.fonts['bold'], name if known else '???', self.theme['text'], topleft = (left, area.top))
		status = 'dex_caught' if name in game.caught else 'dex_seen' if known else 'dex_unknown'
		draw_text(surface, self.fonts['regular'], t(status), COLORS['gold'] if name in game.caught else self.theme['muted'], topleft = (left, area.top + 36))
		y = area.top + 76
		if known:
			data = MONSTER_DATA[name]
			lines = [t('search_element', value = ' / '.join(t(f'element_{kind}') for kind in (data['stats']['element'], data['stats'].get('element2')) if kind))]   # Iteration 27: both types
			if name in game.caught:
				stats = data['stats']
				lines.append(t('search_stats', health = stats['max_health'], energy = stats['max_energy'], attack = stats['attack'], defense = stats['defense'], speed = stats['speed']))
				lines.append(t('search_abilities', value = ', '.join(attack_name(attack) for attack in data['abilities'].values())))
				lines.append(t('search_evolves', monster = data['evolve'][0], level = data['evolve'][1]) if data['evolve'] else t('search_no_evolution'))
			# Iteration 25: where to find it
			import records
			places = [t(key, zone = t(f'zone_{detail}') if detail in ('forest', 'sand', 'ice') else '', monster = detail or '') for key, detail in records.habitat(name)]
			lines.append(t('dex_habitat', places = ', '.join(places) if places else t('dex_habitat_unknown')))
			for line in lines:
				y = self.draw_paragraph(surface, line, (left, y), width, self.theme['text']) + 8

		# how complete the index is
		bar = pygame.FRect(left, area.bottom - 40, width, 14)
		draw_bar(surface, bar, len(game.caught), len(self.species), COLORS['gold'], self.theme['row'], 4)
		draw_text(surface, self.fonts['small'], t('dex_complete_reward'), self.theme['muted'], bottomleft = bar.topleft + vector(0, -6))


# Side quests and achievements with progress bars. Enter claims the reward of a completed quest.
class QuestScreen(ListScreen):
	hint = 'hint_quests'
	row_height = 40

	# Iteration 19: quests ready to claim go to the top, claimed ones to the bottom, and the rest
	# (still in progress) stay in the middle in their normal order.
	# Iteration 25: today's 3 daily quests and this week's quest come first.
	def ordered(self):
		import records
		def group(quest):
			if quest in self.game.claimed:
				return 2
			return 0 if self.game.quest_progress(quest) >= QUEST_DATA[quest]['target'] else 1
		return records.timed_quests(self.game) + sorted(QUEST_DATA, key = group)   # sorted() is stable, so the order inside a group is kept

	# (text, target, reward, progress, claimed) for any quest, normal or daily/weekly.
	def info(self, quest):
		import records
		if ':' in quest:
			period, counter, target, coins = records.parse(quest)
			text = t(f'{period}_label') + ' ' + t(f'timed_{counter}', target = target)
			return text, target, {'coins': coins}, records.timed_progress(self.game, quest), records.timed_claimed(self.game, quest), counter
		data = QUEST_DATA[quest]
		return t(f'quest_{quest}', target = data['target']), data['target'], data['reward'], self.game.quest_progress(quest), quest in self.game.claimed, data['kind']

	# Iteration 20: an icon for each kind of quest
	KIND_ICONS = {'catches': 'capture_orb', 'caught': 'book', 'seen': 'book', 'badges': 'badge', 'evolved': 'heal', 'level': 'heal',
	              'party': 'person', 'shiny': 'illuminator', 'coins': 'coin',
	              'wins': 'sword', 'fished': 'fishing_rod', 'dug': 'shovel', 'steps': 'person', 'crits': 'sword', 'night_catches': 'moon'}   # Iteration 25
	def row_picture(self, index, selected):
		order = self.ordered()
		if index >= len(order):
			return None
		name = self.KIND_ICONS.get(self.info(order[index])[5], 'clock' if ':' in order[index] else 'scroll')
		if name in ITEM_PICTURES:
			return small_item_icon(self.game, name)
		return row_icon(name, selected)

	def get_items(self):
		items = []
		for quest in self.ordered():
			text, target, _, progress, claimed, _ = self.info(quest)
			mark = '[x]' if claimed else '[!]' if progress >= target else '[ ]'
			items.append((f"{mark} {text}", lambda quest = quest: self.claim(quest)))
		return items

	def claim(self, quest):
		import records
		if ':' in quest:
			self.message = t(records.claim_timed(self.game, quest))
			self.game.check_quests()
		else:
			self.message = self.game.claim_quest(quest)

	def draw(self, surface):
		area = self.draw_panel(surface, t('quests_title', done = len(self.game.claimed), total = len(QUEST_DATA)))
		split = area.width * 0.58
		self.draw_list(surface, pygame.FRect(area.left, area.top, split, area.height - 36))
		quest = self.ordered()[self.index]
		text, target, reward, progress, claimed, _ = self.info(quest)
		left, width = area.left + split + 32, area.width - split - 32
		y = self.draw_paragraph(surface, text, (left, area.top), width, self.theme['text'], 'regular') + 12
		progress = min(progress, target)
		bar = pygame.FRect(left, y, width, 14)
		draw_bar(surface, bar, progress, target, COLORS['gold'], self.theme['row'], 4)
		draw_text(surface, self.fonts['small'], f"{progress} / {target}", self.theme['muted'], topleft = bar.bottomleft + vector(0, 6))
		y = bar.bottom + 40
		parts = ([t('quest_coins', amount = reward['coins'])] if reward.get('coins') else []) + [f'{item_name(name)} x{amount}' for name, amount in reward.get('items', {}).items()]
		y = self.draw_paragraph(surface, t('quest_reward', reward = ', '.join(parts)), (left, y), width, self.theme['text']) + 12
		status = 'quest_claimed_status' if claimed else 'quest_ready' if progress >= target else 'quest_in_progress'
		if ':' in quest:
			draw_text(surface, self.fonts['small'], t('quest_resets_daily' if quest.startswith('daily') else 'quest_resets_weekly'), self.theme['muted'], topleft = (left, y + 30))
		draw_text(surface, self.fonts['regular'], t(status), COLORS['gold'] if status == 'quest_ready' else self.theme['muted'], topleft = (left, y))
		draw_text(surface, self.fonts['regular'], self.message, self.theme['accent'], bottomleft = area.bottomleft)



# Iteration 25: achievements (Left/Right switches to the stats page). Achievements not unlocked yet
# show their progress; unlocked ones are gold with a trophy.
class RecordsScreen(Screen):
	hint = 'hint_records'
	columns = 4

	def __init__(self, ui):
		super().__init__(ui)
		self.page = 0      # 0 = achievements, 1 = stats
		self.index = 0
		self.time = 0

	def handle_key(self, event):
		import records
		key = controls.menu_key(event.key)
		count = len(records.ACHIEVEMENTS)
		if event.key == pygame.K_ESCAPE:
			self.back()
		elif event.key == pygame.K_TAB:
			self.page = 1 - self.page
		elif self.page == 0 and key in (pygame.K_LEFT, pygame.K_RIGHT):
			self.index = (self.index + (1 if key == pygame.K_RIGHT else -1)) % count
		elif self.page == 0 and key in (pygame.K_UP, pygame.K_DOWN):
			self.index = (self.index + (self.columns if key == pygame.K_DOWN else -self.columns)) % count

	def update(self, dt):
		self.time += dt

	def draw(self, surface):
		import records
		game = self.game
		done = records.unlocked(game)
		area = self.draw_panel(surface, t('records_title', done = len(done), total = len(records.ACHIEVEMENTS)) if self.page == 0 else t('stats_title'))
		# the two tabs
		for number, key in enumerate(('records_tab_achievements', 'records_tab_stats')):
			label = self.fonts['small'].render(t(key), False, self.theme['selected_text'] if number == self.page else self.theme['muted'])
			tab = label.get_frect(topright = (area.right - (1 - number) * 150, area.top - 44)).inflate(20, 10)
			pygame.draw.rect(surface, self.theme['selected'] if number == self.page else self.theme['row'], tab, 0, 6)
			surface.blit(label, label.get_frect(center = tab.center))
		if self.page == 0:
			self.draw_achievements(surface, area, done)
		else:
			self.draw_stats(surface, area)

	def draw_achievements(self, surface, area, done):
		import records
		width = (area.width - (self.columns - 1) * 10) / self.columns
		names = list(records.ACHIEVEMENTS)
		for number, name in enumerate(names):
			rect = pygame.FRect(area.left + (number % self.columns) * (width + 10), area.top + (number // self.columns) * 76, width, 68)
			got = name in done
			selected = number == self.index
			pygame.draw.rect(surface, (70, 56, 24) if got else self.theme['row'], rect, 0, 8)
			pygame.draw.rect(surface, UI['gold'] if selected else (self.theme['muted'] if not got else (160, 130, 40)), rect, 3 if selected else 1, 8)
			picture = icon('trophy', 3, UI['frame_dark'], UI['gold'] if got else (90, 88, 98))
			surface.blit(picture, picture.get_frect(midleft = rect.midleft + vector(10, 0)))
			draw_text(surface, self.fonts['small'], t(f'ach_{name}'), COLORS['white'] if got else self.theme['muted'], topleft = rect.topleft + vector(58, 12))
			kind, target, _ = records.ACHIEVEMENTS[name]
			amount = min(target, records.progress(self.game, kind))
			bar = pygame.FRect(rect.left + 58, rect.bottom - 22, rect.width - 72, 8)
			draw_bar(surface, bar, amount, target, UI['gold'], self.theme['panel'], 3)
		# details of the selected achievement along the bottom
		name = names[self.index]
		kind, target, reward = records.ACHIEVEMENTS[name]
		y = area.top + ((len(names) - 1) // self.columns + 1) * 76 + 8
		pygame.draw.line(surface, self.theme['muted'], (area.left, y), (area.right, y), 2)
		y = self.draw_paragraph(surface, t(f'ach_{name}_desc', target = target), (area.left, y + 12), area.width, self.theme['text'])
		parts = ([t('quest_coins', amount = reward['coins'])] if reward.get('coins') else []) + [f'{item_name(item)} x{amount}' for item, amount in reward.get('items', {}).items()]
		progress = min(target, records.progress(self.game, kind))
		draw_text(surface, self.fonts['regular'], t('quest_reward', reward = ', '.join(parts)) + f'    {progress} / {target}', COLORS['gold'], topleft = (area.left, y + 8))

	def draw_stats(self, surface, area):
		import records
		game = self.game
		rows = [(t('stat_play_time'), records.format_time(game.play_time))]
		finish = game.story.get('finish_time')
		rows.append((t('stat_finish_time'), records.format_time(finish) if finish is not None else '-'))
		rows += [(t(f'stat_{name}'), game.counters.get(name, 0)) for name in records.STATS]
		rows.append((t('stat_species'), f'{len(game.caught)} / {len(MONSTER_DATA)}'))
		half = (area.width - 24) / 2
		for number, (label, value) in enumerate(rows):
			column, row = divmod(number, (len(rows) + 1) // 2)
			rect = pygame.FRect(area.left + column * (half + 24), area.top + row * 44, half, 38)
			pygame.draw.rect(surface, self.theme['row'], rect, 0, 6)
			draw_text(surface, self.fonts['regular'], label, self.theme['text'], midleft = rect.midleft + vector(14, 0))
			draw_text(surface, self.fonts['bold'], value, COLORS['gold'], midright = rect.midright - vector(14, 0))
