# atmosphere.py
# Iteration 20: things that make the world feel alive - a banner with the area's name, and at night
# fireflies and warm light from buildings.
# Iteration 31: the only weather left is snow in the snow zone. The desert dust, drifting leaves,
# footprints, running dust, grass bits, footstep sounds and background (ambient) sounds were removed.
# Everything here is only drawn; none of it changes the game itself.

from random import uniform, random, choice
from math import sin, cos, pi

from settings import *
from localisation import t
from ui_style import hud_tag
import controls

WEATHER_COUNT = {'ice': 70}   # Iteration 31: only snow
AMBIENCE = {}                 # Iteration 31: no background sounds
INDOOR_MAPS = ('house', 'hospital', 'hospital2', 'plant', 'fire', 'water', 'lab', 'glitch')   # Iteration 25: + the Glitch Zone
BANNER_TIME = 2.6


class Particle:
	__slots__ = ('x', 'y', 'vx', 'vy', 'life', 'age', 'size', 'phase', 'kind')
	def __init__(self, x, y, vx, vy, life, size, kind):
		self.x, self.y, self.vx, self.vy, self.life, self.size, self.kind = x, y, vx, vy, life, size, kind
		self.age, self.phase = 0.0, uniform(0, 2 * pi)


class Atmosphere:
	def __init__(self, game):
		self.game = game
		self.weather = []          # screen-space particles (snow, dust, leaves)
		self.effects = []          # world-space particles (dust puffs, footprints, fireflies)
		self.biome = None          # the zone the player is in now
		self.weather_strength = 0  # fades 0 -> 1 when entering a zone with weather
		self.banner = None         # (text, seconds left)
		self.step_timer = 0
		self.print_side = 1
		self.ambience = None
		self.last_offset = vector()
		self.lights = []           # (centre, radius) of warm light at night, found when a map loads

	# ---------- called by Game ----------
	# A new map was loaded: find the buildings (for night light) and show the banner for the area.
	def map_loaded(self, map_name):
		self.effects.clear()
		self.lights = []
		for sprite in self.game.collision_sprites:
			if type(sprite).__name__ == 'CollidableSprite' and sprite.rect.width >= 300:
				self.lights.append((vector(sprite.rect.midbottom) - (0, 50), sprite.rect.width * 0.55))
		self.biome = None
		if map_name in INDOOR_MAPS:
			self.show_banner(t(f'zone_{map_name}'))

	def show_banner(self, text):
		self.banner = [text, BANNER_TIME]

	def zone_changed(self, biome):
		if biome != self.biome and biome:
			if self.biome is not None or self.game.current_map == 'world':
				self.show_banner(t(f'zone_{biome}'))
			self.biome = biome

	def update(self, dt, active):
		game = self.game
		offset = vector(game.all_sprites.offset)
		moved = offset - self.last_offset
		self.last_offset = offset
		outdoors = game.current_map not in INDOOR_MAPS
		biome = game.current_biome() if outdoors else None
		if outdoors and biome:
			self.zone_changed(biome)
		self.update_weather(dt, biome if outdoors else None, moved)
		self.update_effects(dt)
		if active:
			if game.is_dark() and outdoors and biome == 'forest' and random() < dt * 3:   # Iteration 25: also at night on the clock
				self.spawn_firefly()
		busy = self.game.battle or self.game.evolution
		self.update_ambience(biome if outdoors and not busy else None)
		if self.banner:
			self.banner[1] -= dt
			if self.banner[1] <= 0:
				self.banner = None

	# ---------- weather ----------
	def update_weather(self, dt, biome, moved):
		target = WEATHER_COUNT.get(biome, 0)
		self.weather_strength += (1 if target else -1) * dt * 0.8
		self.weather_strength = max(0, min(1, self.weather_strength))
		want = int(target * self.weather_strength)
		kind = {'ice': 'snow', 'sand': 'dust', 'forest': 'leaf'}.get(biome)
		# weather from the last zone drifts away a few pieces at a time; the new zone's fills in
		wrong = [p for p in self.weather if p.kind != kind]
		for p in wrong[:max(1, len(wrong) // 10)]:
			self.weather.remove(p)
		right = len(self.weather)
		while kind and right < want:
			self.weather.append(self.new_weather(biome, anywhere = right < want // 2))
			right += 1
		if right > want and self.weather:
			self.weather.pop()
		for p in self.weather:
			p.age += dt
			p.x += p.vx * dt
			p.y += p.vy * dt
			# move with the camera so the weather feels attached to the world
			p.x += moved.x
			p.y += moved.y
			if p.kind == 'snow':
				p.x += sin(p.age * 2 + p.phase) * 18 * dt
			elif p.kind == 'leaf':
				p.x += sin(p.age * 1.5 + p.phase) * 40 * dt
			if p.x < -40: p.x += WINDOW_WIDTH + 80
			if p.x > WINDOW_WIDTH + 40: p.x -= WINDOW_WIDTH + 80
			if p.y > WINDOW_HEIGHT + 20 or p.y < -40:
				p.y = -10 if p.vy >= 0 else WINDOW_HEIGHT + 10
				p.x = uniform(0, WINDOW_WIDTH)

	def new_weather(self, biome, anywhere = False):
		y = uniform(0, WINDOW_HEIGHT) if anywhere else uniform(-30, -5)
		x = uniform(0, WINDOW_WIDTH)
		if biome == 'ice':
			return Particle(x, y, uniform(-10, 10), uniform(40, 90), 0, choice((2, 2, 3, 4)), 'snow')
		if biome == 'sand':
			return Particle(uniform(-40, WINDOW_WIDTH), uniform(0, WINDOW_HEIGHT), uniform(160, 300), uniform(-8, 8), 0, uniform(10, 40), 'dust')
		return Particle(x, y, uniform(20, 50), uniform(30, 55), 0, 5, 'leaf')

	def spawn_firefly(self):
		centre = vector(self.game.player.rect.center)
		self.effects.append(Particle(centre.x + uniform(-600, 600), centre.y + uniform(-350, 350), uniform(-15, 15), uniform(-15, 15), uniform(4, 7), 3, 'firefly'))

	def update_effects(self, dt):
		for p in self.effects:
			p.age += dt
			p.x += p.vx * dt
			p.y += p.vy * dt
			if p.kind == 'firefly':
				p.vx += uniform(-30, 30) * dt
				p.vy += uniform(-30, 30) * dt
		self.effects = [p for p in self.effects if p.age < p.life][-160:]

	# ---------- sound ----------
	def update_ambience(self, biome):
		name = AMBIENCE.get(biome) if biome else None
		if name == self.ambience:
			return
		audio = self.game.audio
		if self.ambience in audio:
			audio[self.ambience].fadeout(800)
		if name in audio:
			audio[name].play(-1, fade_ms = 1200)
		self.ambience = name

	def stop_sounds(self):
		self.update_ambience(None)

	# ---------- drawing ----------
	# Ground effects (footprints, dust) are drawn after the world; weather and the banner after that.
	def draw_ground(self, surface, offset):
		for p in self.effects:
			fade = 1 - p.age / p.life
			pos = (p.x + offset.x, p.y + offset.y)
			if p.kind.startswith('print'):
				colour = (196, 160, 96) if p.kind == 'print_sand' else (170, 190, 215)
				mark = pygame.Surface((10, 6), pygame.SRCALPHA)
				pygame.draw.ellipse(mark, (*colour, int(150 * fade)), mark.get_rect())
				surface.blit(mark, (pos[0] - 5, pos[1] - 3))
			elif p.kind == 'puff':
				r = p.size + (1 - fade) * 8
				puff = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
				pygame.draw.circle(puff, (235, 225, 200, int(140 * fade)), (r + 1, r + 1), r)
				surface.blit(puff, (pos[0] - r, pos[1] - r))

	def draw_sky(self, surface, offset):
		for p in self.effects:
			if p.kind.startswith('blade'):
				pos = vector(p.x, p.y + 60 * p.age * p.age) + offset
				colour = (110, 175, 60) if p.kind == 'blade' else (200, 230, 240)
				pygame.draw.line(surface, colour, pos, pos + (2, -4), 2)
		for p in self.weather:
			if p.kind == 'snow':
				pygame.draw.circle(surface, (150, 170, 200), (p.x + 1, p.y + 1), p.size)   # a soft shadow so flakes show on white snow
				pygame.draw.circle(surface, (250, 252, 255), (p.x, p.y), p.size)
			elif p.kind == 'dust':
				streak = pygame.Surface((int(p.size) + 2, 3), pygame.SRCALPHA)
				streak.fill((252, 236, 196, 170))
				surface.blit(streak, (p.x, p.y))
			else:
				colour = (120, 170, 60) if p.phase < pi else (190, 160, 60)
				angle = sin(p.age * 3 + p.phase) * 0.8
				dx, dy = cos(angle) * 4, sin(angle) * 4
				pygame.draw.line(surface, colour, (p.x - dx, p.y - dy), (p.x + dx, p.y + dy), 3)

	# Night light: drawn after the night tint so lamps and fireflies glow.
	def draw_lights(self, surface, offset):
		if not self.game.is_dark():
			return
		glow = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
		view = pygame.FRect(-offset, (WINDOW_WIDTH, WINDOW_HEIGHT)).inflate(400, 400)
		flicker = 1 + 0.04 * sin(pygame.time.get_ticks() / 180)
		for centre, radius in self.lights:
			if view.collidepoint(centre):
				pos = centre + offset
				for scale, alpha in ((1.0, 22), (0.7, 28), (0.4, 36)):
					pygame.draw.circle(glow, (255, 200, 110, alpha), pos, radius * scale * flicker)
		for p in self.effects:
			if p.kind == 'firefly':
				fade = min(1, p.age, (p.life - p.age))
				blink = 0.5 + 0.5 * sin(p.age * 6 + p.phase)
				pos = (p.x + offset.x, p.y + offset.y)
				pygame.draw.circle(glow, (220, 255, 120, int(60 * fade * blink)), pos, 9)
				pygame.draw.circle(glow, (250, 255, 190, int(220 * fade * blink)), pos, 3)
		surface.blit(glow, (0, 0))

	def draw_banner(self, surface, font):
		if not self.banner:
			return
		text, left = self.banner
		slide = min(1, (BANNER_TIME - left) / 0.3, left / 0.4)
		hud_tag(surface, text, font, color = UI_GOLD, alpha = int(255 * max(0, slide)), midtop = (WINDOW_WIDTH / 2, -50 + 230 * max(0, slide)))

UI_GOLD = (255, 215, 0)
