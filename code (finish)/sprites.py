# sprites.py
# All sprite classes: overworld tiles and objects, and the battle sprites (monsters, outlines,
# names, levels, stats bars, attack animations and timed icons).

from settings import * 
from random import uniform
from math import sin
from os.path import exists
from support import draw_bar, stat_color
from timery import Timer
from localisation import t
import item_art

# overworld sprites
# Basic overworld sprite. Parameters: pos (top-left), surf (image), groups, z (drawing layer).
class Sprite(pygame.sprite.Sprite):
	def __init__(self, pos, surf, groups, z = WORLD_LAYERS['main']):
		super().__init__(groups)
		self.image = surf 
		self.rect = self.image.get_frect(topleft = pos)
		self.z = z
		self.y_sort = self.rect.centery
		self.hitbox = self.rect.copy()

# Invisible wall from the Collisions layer of the map. Its hitbox is the full rectangle.
class BorderSprite(Sprite):
	def __init__(self, pos, surf, groups):
		super().__init__(pos, surf, groups)
		self.hitbox = self.rect.copy()

# Invisible zone that loads another map. target = (map name, player start position).
class TransitionSprite(Sprite):
	def __init__(self, pos, size, target, groups):
		surf = pygame.Surface(size)
		super().__init__(pos, surf, groups)
		self.target = target

# Solid object such as a tree or house. The hitbox is shorter than the image so the player
# can walk behind the top of the object.
class CollidableSprite(Sprite):
	def __init__(self, pos, surf, groups):
		super().__init__(pos, surf, groups)
		self.hitbox = self.rect.inflate(0, -self.rect.height * 0.6)

# Grass patch where wild monsters appear. biome picks the battle background, monsters is a
# comma-separated string of species, level is the base level of wild monsters.
class MonsterPatchSprite(Sprite):
	def __init__(self, pos, surf, groups, biome, monsters, level):
		self.biome = biome
		super().__init__(pos, surf, groups, WORLD_LAYERS['main' if biome != 'sand' else 'bg'])
		self.y_sort -= 40
		self.biome = biome
		self.monsters = monsters.split(',')
		self.level = level

# Overworld sprite that loops through animation frames (water, coast).
# Iteration 19: every water and coast tile takes its frame from one shared clock (world_time), so
# all the waves move together. Before, tiles off the screen were paused (to save time), so when
# they came on screen they were out of step with their neighbours and the waves looked broken.
class AnimatedSprite(Sprite):
	world_time = 0   # seconds, moved on once per frame by AllSprites.update

	def __init__(self, pos, frames, groups, z = WORLD_LAYERS['main']):
		self.frame_index, self.frames = 0, frames
		super().__init__(pos, frames[self.frame_index], groups, z)

	def animate(self, dt):
		self.frame_index = AnimatedSprite.world_time * ANIMATION_SPEED
		self.image = self.frames[int(self.frame_index % len(self.frames))]

	def update(self, dt):
		self.animate(dt)

# battle sprites 
# A monster on the battle field. Handles its animation, the white highlight when its turn starts,
# starting an attack, and being removed (with an optional replacement) after fainting or being caught.
class MonsterSprite(pygame.sprite.Sprite):
	def __init__(self, pos, frames, groups, monster, index, pos_index, entity, apply_attack, create_monster):
		# data
		self.index = index 
		self.pos_index = pos_index
		self.entity = entity
		self.monster = monster
		self.frame_index, self.frames, self.state = 0, frames, 'idle'
		self.animation_speed = ANIMATION_SPEED + uniform(-1, 1)
		self.z = BATTLE_LAYERS['monster']
		self.highlight = False
		self.target_sprite = None
		self.current_attack = None
		self.apply_attack = apply_attack
		self.create_monster = create_monster

		# sprite setup
		super().__init__(groups)
		self.image = self.frames[self.state][self.frame_index]
		self.rect = self.image.get_frect(center = pos)

		# timers 
		self.timers = {
			'remove highlight': Timer(300, func = lambda: self.set_highlight(False)),
			'kill': Timer(600, func = self.destroy)
		}

	def animate(self, dt):
		self.frame_index += self.animation_speed * dt   # each monster animates at a slightly different speed so they are not in step
		if self.state == 'attack' and self.frame_index >= len(self.frames['attack']):
			self.apply_attack(self.target_sprite, self.current_attack, self.monster.get_base_damage(self.current_attack), attacker = self)
			self.state = 'idle'

		self.adjusted_frame_index = int(self.frame_index % len(self.frames[self.state]))
		self.image = self.frames[self.state][self.adjusted_frame_index]

		# Iteration 24: fainting - the monster shrinks and fades while the kill timer runs
		if self.timers['kill'].active:
			progress = min(1, (pygame.time.get_ticks() - self.timers['kill'].start_time) / self.timers['kill'].duration)
			size = max(1, int(self.image.get_width() * (1 - 0.7 * progress))), max(1, int(self.image.get_height() * (1 - 0.7 * progress)))
			small = pygame.transform.smoothscale(self.image.convert_alpha(), size)   # Iteration 33: keep the see-through background (it showed green)
			faded = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
			faded.blit(small, small.get_frect(midbottom = (self.image.get_width() / 2, self.image.get_height() * 0.8)))
			faded.set_alpha(int(255 * (1 - progress)))
			self.image = faded
		# Iteration 24: a golden glow after levelling up
		if getattr(self, 'glow_time', 0) > 0:
			self.glow_time -= dt
			gold = pygame.mask.from_surface(self.image).to_surface(setcolor = (255, 215, 0, 255), unsetcolor = (0, 0, 0, 0))
			gold.set_alpha(int(160 * abs(sin(self.glow_time * 8))))
			self.image = self.image.copy()
			self.image.blit(gold, (0, 0))

		# Iteration 21: a monster charging a move (or waiting to strike last) flashes
		charging = getattr(self.monster, 'charging', None) and (pygame.time.get_ticks() // 160) % 2
		if self.highlight or charging:
			white_surf = pygame.mask.from_surface(self.image).to_surface()
			white_surf.set_colorkey('black')
			self.image = white_surf

	# Turns the white flash on or off. When turned on, a timer turns it off again after 300 ms.
	def set_highlight(self, value):
		self.highlight = value
		if value: 
			self.timers['remove highlight'].activate()

	# Starts the attack animation and pays the energy cost. apply_attack is called when the animation ends.
	# Iteration 21: pay = False when a charged move is released (its energy was paid when charging started)
	def activate_attack(self, target_sprite, attack, pay = True):
		self.state = 'attack'
		self.frame_index = 0
		self.target_sprite = target_sprite
		self.current_attack = attack
		if pay:
			self.monster.reduce_energy(attack)

	# Removes the monster after 600 ms so the player can see it faint. new_monster is the data for
	# the replacement monster (or None).
	def delayed_kill(self, new_monster):
		if not self.timers['kill'].active:
			self.next_monster_data = new_monster
			self.timers['kill'].activate()

	# Called by the kill timer: creates the replacement monster (if any) and removes this sprite.
	def destroy(self):
		if self.next_monster_data:
			self.create_monster(*self.next_monster_data)
		self.kill()

	def update(self, dt):
		for timer in self.timers.values():
			timer.update()
		self.animate(dt)
		self.monster.update(dt)

# White outline drawn behind a monster to show it is active or targeted. Copies the monster's frame.
class MonsterOutlineSprite(pygame.sprite.Sprite):
	def __init__(self, monster_sprite, groups, frames):
		super().__init__(groups)
		self.z = BATTLE_LAYERS['outline']
		self.monster_sprite = monster_sprite
		self.frames = frames

		self.image = self.frames[self.monster_sprite.state][self.monster_sprite.frame_index]
		self.rect = self.image.get_frect(center = self.monster_sprite.rect.center)

	def update(self, _):
		self.image = self.frames[self.monster_sprite.state][self.monster_sprite.adjusted_frame_index]
		if not self.monster_sprite.groups():
			self.kill()

# White label with the monster's name, shown above it in battle.
class MonsterNameSprite(pygame.sprite.Sprite):
	def __init__(self, pos, monster_sprite, groups, font):
		super().__init__(groups)
		self.monster_sprite = monster_sprite
		self.z = BATTLE_LAYERS['name']

		# Iteration 16: shiny monsters have a * after their name and a gold label
		shiny = monster_sprite.monster.shiny
		text_surf = font.render(monster_sprite.monster.display_name + (' *' if shiny else ''), False, COLORS['black'])
		padding = 10
		# Iteration 24: the monster's type as a small coloured chip after its name
		element = monster_sprite.monster.element
		chip = item_art.type_icon(element, 20)   # Iteration 32: the round type icons
		second = getattr(monster_sprite.monster, 'element2', None)   # Iteration 27: a second type gets a second chip
		second_chip = item_art.type_icon(second, 20) if second else None

		self.image = pygame.Surface((text_surf.get_width() + 2 * padding + 22 + (22 if second_chip else 0), text_surf.get_height() + 2 * padding)) 
		self.image.fill(COLORS['gold'] if shiny else COLORS['white'])
		self.image.blit(text_surf, (padding, padding))
		for number, (kind, picture) in enumerate(((element, chip), (second, second_chip))):
			if picture is None:
				continue
			badge = pygame.Rect(text_surf.get_width() + padding + 4 + number * 22, (self.image.get_height() - 20) / 2, 20, 20)
			self.image.blit(picture, picture.get_rect(center = badge.center))
		self.rect = self.image.get_frect(midtop = pos)

	def update(self, _):
		if not self.monster_sprite.groups():
			self.kill()

# Label showing the monster's level with a thin xp bar underneath.
class MonsterLevelSprite(pygame.sprite.Sprite):
	def __init__(self, entity, pos, monster_sprite, groups, font):
		super().__init__(groups)
		self.monster_sprite = monster_sprite
		self.font = font
		self.z = BATTLE_LAYERS['name']

		self.image = pygame.Surface((60,26))
		self.rect = self.image.get_frect(topleft = pos) if entity == 'player' else self.image.get_frect(topright = pos)
		self.xp_rect = pygame.FRect(0,self.rect.height - 2,self.rect.width,2)

	def update(self, _):
		self.image.fill(COLORS['white'])

		text_surf = self.font.render(t('battle_level', level = self.monster_sprite.monster.level), False, COLORS['black'])
		text_rect = text_surf.get_frect(center = (self.rect.width / 2, self.rect.height / 2))
		self.image.blit(text_surf, text_rect)

		draw_bar(self.image, self.xp_rect, self.monster_sprite.monster.xp, self.monster_sprite.monster.level_up, COLORS['black'], COLORS['white'], 0)

		if not self.monster_sprite.groups():
			self.kill()

# Box under each monster showing health (red), energy (blue) and initiative (grey) bars.
class MonsterStatsSprite(pygame.sprite.Sprite):
	def __init__(self, pos, monster_sprite, size, groups, font):
		super().__init__(groups)
		self.monster_sprite = monster_sprite
		self.image = pygame.Surface(size) 
		self.rect = self.image.get_frect(midbottom = pos)
		self.font = font
		self.z = BATTLE_LAYERS['overlay']
		self.shown_health = monster_sprite.monster.health   # Iteration 18: the health the bar shows right now

	def update(self, _):
		monster = self.monster_sprite.monster
		# Iteration 35: the box is only tall enough for the stat pills when a stat has been changed
		height = 82 if any(getattr(monster, 'stages', {}).values()) else 62
		if self.image.get_height() != height:
			self.image = pygame.Surface((self.rect.width, height))
			self.rect = self.image.get_frect(topleft = self.rect.topleft)
		self.image.fill(COLORS['white'])
		width = self.rect.width

		for index, (value, max_value) in enumerate(monster.get_info()):
			if index == 0:
				# Iteration 18: the health bar drains smoothly and goes green -> yellow -> red as it drops
				self.shown_health += (value - self.shown_health) * 0.15
				value = self.shown_health
				color = stat_color(value / max_value)
			else:
				color = COLORS['blue']
			if index < 2: # health and energy
				text_surf = self.font.render(f'{int(value)}/{max_value}', False, COLORS['black'])
				text_rect = text_surf.get_frect(topleft = (width * 0.05, index * 24))
				bar_rect = pygame.FRect(text_rect.bottomleft + vector(0, -2), (width * 0.9, 4))
				self.image.blit(text_surf, text_rect)
				draw_bar(self.image, bar_rect, value, max_value, color, COLORS['black'], 2)
			else: # Iteration 32: the turn bar - fills up until it is this monster's turn
				self.draw_turn_bar(pygame.Rect(width * 0.05, 50, width * 0.9, 8), value / max_value if max_value else 0)

		# Iteration 32: raised or lowered stats. Iteration 34: shown as green (raised) or red (lowered) pills
		# with the stat's icon and the number of stages, so they can be read at a glance.
		x = 4
		for stat in ('attack', 'defense', 'speed'):
			stage = getattr(monster, 'stages', {}).get(stat, 0)
			if not stage:
				continue
			label = self.font.render(f'{"+" if stage > 0 else "-"}{abs(stage)}', False, COLORS['white'])
			pill = pygame.Rect(x, 59, 22 + label.get_width() + 6, 19)
			pygame.draw.rect(self.image, '#2f9e44' if stage > 0 else '#d63a3a', pill, 0, 6)
			icon = item_art.item(STAGE_ICONS[stat], 16)
			self.image.blit(icon, icon.get_frect(midleft = (pill.left + 3, pill.centery)))
			self.image.blit(label, label.get_frect(midleft = (pill.left + 21, pill.centery)))
			x = pill.right + 4

		# Iteration 21: the monster's status (burn, freeze, poison, sleep, confused) as a small icon
		status = getattr(monster, 'status', None)
		if status:
			icon = item_art.status_icon(status, 18)
			self.image.blit(icon, icon.get_frect(topright = (width - 2, 2)))

		if not self.monster_sprite.groups():
			self.kill()

	def draw_turn_bar(self, area, fraction):
		empty, full = turn_bar_pictures(area.size)
		if empty is None:   # no picture files - a plain bar
			draw_bar(self.image, area, fraction, 1, COLORS['gray'], COLORS['white'], 0)
			return
		self.image.blit(empty, area)
		filled = int(area.width * max(0, min(1, fraction)))
		if filled:
			self.image.blit(full, area, pygame.Rect(0, 0, filled, area.height))

STAGE_ICONS = {'attack': 'ui_sword', 'defense': 'ui_trophy', 'speed': 'snow_boots'}
_turn_bars = {}
def turn_bar_pictures(size):
	if size not in _turn_bars:
		pictures = []
		for name in ('turnbar_empty', 'turnbar_full'):
			path = asset('graphics', 'ui_pack', f'{name}.png')
			pictures.append(pygame.transform.scale(pygame.image.load(path).convert_alpha(), size) if exists(path) else None)
		_turn_bars[size] = pictures
	return _turn_bars[size]

# Plays an attack animation once over the target, then removes itself.
_scaled_attacks = {}
class AttackSprite(AnimatedSprite):
	# Iteration 34: scale makes the animation bigger or smaller (stronger moves are drawn bigger)
	def __init__(self, pos, frames, groups, scale = 1.0):
		if scale != 1.0:
			key = (id(frames), round(scale, 2))
			if key not in _scaled_attacks:
				_scaled_attacks[key] = [pygame.transform.scale_by(frame, scale) for frame in frames]
			frames = _scaled_attacks[key]
		super().__init__(pos, frames, groups, BATTLE_LAYERS['overlay'])
		self.rect.center = pos

	def animate(self, dt):
		self.frame_index += ANIMATION_SPEED * dt
		if self.frame_index < len(self.frames):
			self.image = self.frames[int(self.frame_index)]
		else:
			self.kill()

	def update(self, dt):
		self.animate(dt)

# Iteration 18: the damage dealt, floating up from the monster that was hit and fading out.
class DamageNumberSprite(pygame.sprite.Sprite):
	def __init__(self, pos, text, font, color, groups):
		super().__init__(groups)
		self.z = BATTLE_LAYERS['overlay']
		outline = font.render(text, False, COLORS['black'])
		self.text = font.render(text, False, color)
		self.image = pygame.Surface((self.text.get_width() + 4, self.text.get_height() + 4), pygame.SRCALPHA)
		for offset in ((0, 2), (4, 2), (2, 0), (2, 4)):   # black edge so it shows on any background
			self.image.blit(outline, offset)
		self.image.blit(self.text, (2, 2))
		self.rect = self.image.get_frect(midbottom = pos)
		self.life = 1.0   # seconds

	def update(self, dt):
		self.life -= dt
		self.rect.y -= 40 * dt
		self.image.set_alpha(int(255 * max(0, min(1, self.life * 2))))
		if self.life <= 0:
			self.kill()

# Shows an image (e.g. the red cross when a catch fails) for a set number of ms, then removes itself.
class TimedSprite(Sprite):
	def __init__(self, pos, surf, groups, duration):
		super().__init__(pos, surf, groups, z = BATTLE_LAYERS['overlay'])
		self.rect.center = pos
		self.death_timer = Timer(duration, autostart = True, func = self.kill)

	def update(self, _):
		self.death_timer.update()