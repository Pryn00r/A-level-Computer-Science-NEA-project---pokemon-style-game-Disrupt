# story_screens.py
# Iteration 22: screens for the house.
#   WardrobeScreen  - the dresser: change the colour of the trainer's clothes (Iteration 27)
#   StorageScreen   - the PC: move monsters between your party (up to 6) and the storage box

from settings import *
from localisation import t

from ui_base import *
import looks
import controls


def draw_walker(surface, game, look, center, scale = 2, time = 0.0, state = 'down'):
	frames = looks.frames_for(game, look)[state]
	frame = frames[int(time * 6) % len(frames)]
	big = pygame.transform.scale_by(frame, scale)
	surface.blit(big, big.get_frect(center = center))


# Iteration 27: the dresser in the bedroom - choose the colour of the trainer's clothes.
class WardrobeScreen(ListScreen):
	hint = 'hint_wardrobe'

	def __init__(self, ui):
		super().__init__(ui)
		self.message = ''
		self.time = 0
		names = list(looks.COLOURS)
		current = looks.colour_name(self.game.look)
		self.index = names.index(current) if current in names else 0

	def get_items(self):
		worn = looks.colour_name(self.game.look)
		return [(t(f'colour_{name}') + ('  *' if name == worn else ''), lambda name = name: self.choose(name)) for name in looks.COLOURS]

	def choose(self, name):
		self.game.change_look(looks.COLOURS[name])
		self.message = t('wardrobe_wearing', look = t(f'colour_{name}'))

	def update(self, dt):
		self.time += dt

	def draw(self, surface):
		area = self.draw_panel(surface, t('wardrobe_title'))
		split = area.width * 0.5
		self.draw_list(surface, pygame.FRect(area.left, area.top, split, area.height - 36))
		name = list(looks.COLOURS)[min(self.index, len(looks.COLOURS) - 1)]
		centre = (area.left + split + (area.width - split) / 2, area.centery - 20)
		pygame.draw.circle(surface, self.theme['row'], centre, 120)
		draw_walker(surface, self.game, looks.COLOURS[name], centre, 2.2, self.time)
		draw_text(surface, self.fonts['regular'], self.message, self.theme['accent'], bottomleft = area.bottomleft)


class StorageScreen(Screen):
	hint = 'hint_storage'

	def __init__(self, ui):
		super().__init__(ui)
		self.column = 0   # 0 = party, 1 = storage box
		self.index = [0, 0]
		self.message = ''

	def lists(self):
		party = [self.game.player_monsters[i] for i in sorted(self.game.player_monsters)]
		return party, self.game.storage

	def handle_key(self, event):
		key = controls.menu_key(event.key)
		party, box = self.lists()
		current = (party, box)[self.column]
		if event.key == pygame.K_ESCAPE:
			self.back()
		elif key in (pygame.K_LEFT, pygame.K_RIGHT):
			self.column = 1 - self.column
		elif key in (pygame.K_UP, pygame.K_DOWN) and current:
			self.index[self.column] = (self.index[self.column] + (1 if key == pygame.K_DOWN else -1)) % len(current)
		elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and current:
			self.message = self.game.move_storage(self.column, min(self.index[self.column], len(current) - 1))
			self.index = [min(self.index[0], max(0, len(self.lists()[0]) - 1)), min(self.index[1], max(0, len(self.lists()[1]) - 1))]

	def draw(self, surface):
		area = self.draw_panel(surface, t('storage_title'))
		party, box = self.lists()
		half = (area.width - 24) / 2
		for column, (title, monsters) in enumerate(((t('storage_party', amount = len(party), total = MAX_PARTY_SIZE), party), (t('storage_box', amount = len(box)), box))):
			left = area.left + column * (half + 24)
			draw_text(surface, self.fonts['bold'], title, COLORS['gold'] if column == self.column else self.theme['text'], topleft = (left, area.top))
			visible = 8
			start = max(0, self.index[column] - visible + 1) if column == self.column else 0
			for row, monster in enumerate(monsters[start:start + visible]):
				rect = pygame.FRect(left, area.top + 40 + row * 50, half, 44)
				selected = column == self.column and start + row == self.index[column]
				icon_surf = self.game.monster_frames['icons'].get(monster.name)
				self.draw_row(surface, rect, f'{monster.display_name}  Lv {monster.level}', selected, pygame.transform.scale(icon_surf, (34, 34)) if icon_surf else None)
			if not monsters:
				draw_text(surface, self.fonts['regular'], t('storage_empty'), self.theme['muted'], topleft = (left, area.top + 50))
		draw_text(surface, self.fonts['regular'], self.message, self.theme['accent'], bottomleft = area.bottomleft)
