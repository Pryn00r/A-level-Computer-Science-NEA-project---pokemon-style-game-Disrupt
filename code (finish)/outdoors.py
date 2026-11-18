# outdoors.py
# Iteration 25: the day and night cycle (one game hour = one real minute). Nights are darker and some
# monsters only appear at night.
# Iteration 31: fishing, digging, hidden items and Repel were removed - only the clock, the night and the
# step counter (for the stats screen and the First Steps achievement) are left.

from datetime import date
from collections import deque

from settings import *
from atmosphere import INDOOR_MAPS
from localisation import t

MINUTES_PER_HOUR = 60        # real seconds for one game hour
NIGHT_START, NIGHT_END = 20, 6
NIGHT_TINT = (80, 92, 165)


# How dark it is (0 = day, 1 = the middle of the night) for an hour between 0 and 24.
# Dusk is 18:00-21:00 and dawn is 5:00-7:00, so the light changes slowly.
def darkness(hour):
	if 7 <= hour < 18:
		return 0.0
	if 18 <= hour < 21:
		return (hour - 18) / 3
	if 5 <= hour < 7:
		return 1 - (hour - 5) / 2
	return 1.0

def is_night(hour):
	return hour >= NIGHT_START or hour < NIGHT_END

def today():
	return date.today().isoformat()


class Outdoors:
	def __init__(self, game):
		self.game = game
		self._reachable = None       # world tiles the player can walk to (worked out once)

	# ---------- the clock ----------
	@property
	def hour(self):
		return self.game.story.get('clock', 9.0)

	def set_hour(self, hour):
		self.game.story['clock'] = hour % 24

	def dark(self):
		outdoors = self.game.current_map not in INDOOR_MAPS
		return darkness(self.hour) if outdoors else 0.0

	def night(self):
		return is_night(self.hour)

	def clock_text(self):
		hour = int(self.hour)
		minute = int((self.hour - hour) * 60) // 10 * 10
		return f'{hour:02d}:{minute:02d}'

	def update(self, dt, active):
		if active:
			self.set_hour(self.hour + dt / MINUTES_PER_HOUR)

	# Counts the tiles walked (Player.update calls this with the distance moved).
	def walked(self, pixels):
		self.step_buffer = getattr(self, 'step_buffer', 0) + pixels / TILE_SIZE
		if self.step_buffer >= 1:
			tiles = int(self.step_buffer)
			counters = self.game.counters
			before = counters.get('steps', 0)
			counters['steps'] = before + tiles
			self.step_buffer -= tiles
			# the Glitch Zone, and your lead monster enjoying the walk
			import postgame
			postgame.glitch_walk(self.game, tiles)
			if (before + tiles) // 100 > before // 100 and self.game.player_monsters:
				self.game.player_monsters[min(self.game.player_monsters)].change_happiness(1)

	# ---------- the night ----------
	def draw_night(self, surface):
		amount = self.dark()
		if amount <= 0:
			return
		colour = pygame.Color(255, 255, 255).lerp(NIGHT_TINT, amount * 0.85)
		surface.fill(colour, special_flags = pygame.BLEND_RGB_MULT)

	# ---------- the world map's walkable tiles (used by the tests to check every place can be reached) ----------
	def reachable(self):
		if self._reachable is None:
			game = self.game
			tmx_map = game.tmx_maps['world']
			layer = tmx_map.get_layer_by_name('Terrain')
			blocked = [pygame.Rect(obj.x, obj.y, obj.width, obj.height) for name in ('Water', 'Collisions') for obj in tmx_map.get_layer_by_name(name)]
			blocked += [pygame.Rect(obj.x, obj.y, obj.width, obj.height) for obj in tmx_map.get_layer_by_name('Objects') if obj.name != 'top']
			width, height = len(layer.data[0]), len(layer.data)
			start = next(((int(obj.x // TILE_SIZE), int(obj.y // TILE_SIZE)) for obj in tmx_map.get_layer_by_name('Entities') if obj.name == 'Player' and obj.properties['pos'] == 'house'), (66, 57))
			free = lambda x, y: pygame.Rect(x * TILE_SIZE + 12, y * TILE_SIZE + 12, 40, 40).collidelist(blocked) < 0
			seen, queue = {start}, deque([start])
			while queue:   # breadth-first search (flood fill) from the house door
				x, y = queue.popleft()
				for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
					tile = (x + dx, y + dy)
					if 0 <= tile[0] < width and 0 <= tile[1] < height and tile not in seen and free(*tile):
						seen.add(tile)
						queue.append(tile)
			self._reachable = {'all': seen}
		return self._reachable
