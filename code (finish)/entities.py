# entities.py
# Contains the moving characters in the overworld. Entity is the base class with shared
# animation and facing-direction code. Player (controlled with the arrow keys) and Character
# (trainers and the nurse) both inherit from it, so shared behaviour is only written once.

from settings import *
from support import check_connections
from timery import Timer
from random import choice
from monster import Monster
import options
import controls

class Entity(pygame.sprite.Sprite):
	# Constructor.
	# Parameters: pos (x, y centre), frames (dict of direction -> list of images), groups (sprite
	# groups to join), facing_direction ('up', 'down', 'left' or 'right')
	def __init__(self, pos, frames, groups, facing_direction):
		super().__init__(groups)
		self.z = WORLD_LAYERS['main']   # drawing layer

		# graphics
		self.frame_index, self.frames = 0, frames     # current animation frame and all frames
		self.facing_direction = facing_direction

		# movement
		self.direction = vector()   # movement direction, (0, 0) when standing still
		self.speed = 250            # pixels per second
		self.blocked = False        # True when the entity is not allowed to move (dialogue, battle, etc.)

		# sprite setup
		self.image = self.frames[self.get_state()][self.frame_index]
		self.rect = self.image.get_frect(center = pos)
		self.hitbox = self.rect.inflate(-self.rect.width / 2, -60)   # smaller box used for collisions (around the feet)

		self.y_sort = self.rect.centery   # used by AllSprites to draw lower sprites in front

	# Moves to the next animation frame based on dt. Parameter: dt (real). Called from update.
	def animate(self, dt):
		self.frame_index += ANIMATION_SPEED * dt
		self.image = self.frames[self.get_state()][int(self.frame_index % len(self.frames[self.get_state()]))]

	# Returns the name of the animation to use, e.g. 'left' when walking left or 'left_idle'
	# when standing still facing left. Also updates facing_direction while moving.
	def get_state(self):
		moving = bool(self.direction)
		if moving:
			if self.direction.x != 0:
				self.facing_direction = 'right' if self.direction.x > 0 else 'left'
			if self.direction.y != 0:
				self.facing_direction = 'down' if self.direction.y > 0 else 'up'
		return f"{self.facing_direction}{'' if moving else '_idle'}"

	# Turns the entity to face a position. Parameter: target_pos (x, y).
	# Called from Game.input (character turns to face the player) and Character.raycast (player turns to face the trainer).
	def change_facing_direction(self, target_pos):
		relation = vector(target_pos) - vector(self.rect.center)
		if abs(relation.y) < 30:
			self.facing_direction = 'right' if relation.x > 0 else 'left'
		else:
			self.facing_direction = 'down' if relation.y > 0 else 'up'

	# Stops the entity from moving (used during dialogue, battles, transitions and evolutions).
	def block(self):
		self.blocked = True
		self.direction = vector(0,0)

	# Allows the entity to move again.
	def unblock(self):
		self.blocked = False

class Character(Entity):
	# Constructor for a trainer or the nurse.
	# Extra parameters: character_data (this character's entry in TRAINER_DATA), player (Player),
	# create_dialog (function in Game), collision_sprites (group), radius (how far they can see),
	# nurse (Boolean), notice_sound (sound played when they spot the player),
	# character_id (key in TRAINER_DATA, used for badges and the map - Iteration 13)
	def __init__(self, pos, frames, groups, facing_direction, character_data, player, create_dialog, collision_sprites, radius, nurse, notice_sound, character_id = None):
		super().__init__(pos, frames, groups, facing_direction)
		self.character_id = character_id
		self.character_data = character_data
		self.player = player
		self.create_dialog = create_dialog
		self.collision_rects = [sprite.rect for sprite in collision_sprites if sprite is not self]   # used for line of sight
		self.nurse = nurse
		self.npc = bool(character_data.get('npc'))   # Iteration 22: the professor (talks, never battles)
		# trainer's team built from TRAINER_DATA, or None for the nurse
		# Iteration 25: the difficulty setting moves trainers' levels up or down a little
		self.monsters = {i: Monster(name, max(1, min(100, lvl + options.state['level']))) for i, (name, lvl) in character_data['monsters'].items()} if 'monsters' in character_data else None

		# movement
		self.has_moved = False      # True once the trainer has walked to the player (only happens once)
		self.can_rotate = True      # False once the trainer has noticed or been talked to
		self.has_noticed = False    # True once the trainer has spotted the player
		self.radius = int(radius)   # sight distance in pixels
		self.view_directions = character_data['directions']   # directions the trainer randomly looks in

		self.timers = {
			'look around': Timer(1500, autostart = True, repeat = True, func = self.random_view_direction),
			'notice': Timer(500, func = self.start_move)   # short pause after noticing before walking over
		}
		self.notice_sound = notice_sound

	# Turns to a random direction from view_directions (called every 1.5 s by the look around timer).
	def random_view_direction(self):
		if self.can_rotate:
			self.facing_direction = choice(self.view_directions)

	# Returns the list of dialogue lines to show - 'default' before the trainer is beaten, 'defeated' after.
	def get_dialog(self):
		return self.character_data['dialog'][f"{'defeated' if self.character_data['defeated'] else 'default'}"]

	# Checks if the player is in front of the trainer, within the radius and in line of sight.
	# If so, blocks the player, plays the notice sound and starts the notice timer. Called from update.
	def raycast(self):
		# Iteration 19: not while the player is busy (talking to someone else, in a menu) - otherwise this trainer
		# would walk over, find the other conversation still open and never start its own
		if check_connections(self.radius, self, self.player) and self.has_los() and not self.has_moved and not self.has_noticed and not self.player.blocked and getattr(self.player, 'can_be_challenged', True):
			self.player.block()
			self.player.change_facing_direction(self.rect.center)
			self.timers['notice'].activate()
			self.can_rotate = False
			self.has_noticed = True
			self.player.noticed = True
			self.notice_sound.play()

	# Line of sight - returns True if no collision rectangle crosses the line between the trainer and the player.
	def has_los(self):
		if vector(self.rect.center).distance_to(self.player.rect.center) < self.radius:
			collisions = [bool(rect.clipline(self.rect.center, self.player.rect.center)) for rect in self.collision_rects]
			return not any(collisions)

	# Sets the trainer's direction towards the player (rounded to a straight line). Called by the notice timer.
	def start_move(self):
		relation = (vector(self.player.rect.center) - vector(self.rect.center)).normalize()
		self.direction = vector(round(relation.x), round(relation.y))

	# Walks the trainer towards the player until they are next to each other, then starts the dialogue.
	# Parameter: dt (real). Called from update.
	def move(self, dt):
		if not self.has_moved and self.direction:
			if not self.hitbox.inflate(10,10).colliderect(self.player.hitbox):
				self.rect.center += self.direction * self.speed * dt
				self.hitbox.center = self.rect.center
			else:
				self.direction = vector()
				self.has_moved = True
				self.create_dialog(self)
				self.player.noticed = False

	# Called every frame by AllSprites.update. Updates timers and animation, and if this is a
	# trainer who looks around, checks for the player and moves.
	def update(self, dt):
		for timer in self.timers.values():
			timer.update()

		self.animate(dt)
		if self.character_data['look_around']:
			self.raycast()
			self.move(dt)

class Player(Entity):
	# Constructor. Extra parameter: collision_sprites (group of sprites the player cannot walk through)
	def __init__(self, pos, frames, groups, facing_direction, collision_sprites):
		super().__init__(pos, frames, groups, facing_direction)
		self.collision_sprites = collision_sprites
		self.noticed = False   # True while a trainer has spotted the player (shows the '!' icon)

	# Reads the arrow keys and sets the movement direction. The vector is normalised so moving
	# diagonally is not faster than moving straight.
	def input(self):
		keys = controls.get_pressed()   # Iteration 16: arrow keys, WASD or the touch D-pad
		input_vector = vector()
		if keys[pygame.K_UP]:
			input_vector.y -= 1
		if keys[pygame.K_DOWN]:
			input_vector.y += 1
		if keys[pygame.K_LEFT]:
			input_vector.x -= 1
		if keys[pygame.K_RIGHT]:
			input_vector.x += 1
		self.direction = input_vector.normalize() if input_vector else input_vector
		# Iteration 18: hold Shift (or the touch Run button) to sprint
		self.sprinting = bool(keys[pygame.K_LSHIFT])

	# Moves the player using dt, one axis at a time, checking collisions after each axis.
	# Iteration 32: the move is split into small steps (at most 8 pixels each). Before, a slow frame (e.g. just
	# after a map loaded) could move the player further than a thin hedge is wide in one go, so the collision
	# check pushed them out on the WRONG side - into a closed-off part of the map where they were stuck.
	def move(self, dt):
		speed = self.speed * (SPRINT_SPEED if getattr(self, 'sprinting', False) else 1) * getattr(self, 'speed_bonus', 1)
		distance = speed * min(dt, 0.1)
		steps = max(1, int(distance // 8) + 1)
		for _ in range(steps):
			self.rect.centerx += self.direction.x * distance / steps
			self.hitbox.centerx = self.rect.centerx
			self.collisions('horizontal')

			self.rect.centery += self.direction.y * distance / steps
			self.hitbox.centery = self.rect.centery
			self.collisions('vertical')

	# Pushes the player back out of any solid sprite they overlap.
	# Parameter: axis ('horizontal' or 'vertical'). Called from move.
	def collisions(self, axis):
		for sprite in self.collision_sprites:
			if sprite.hitbox.colliderect(self.hitbox):
				if axis == 'horizontal':
					if self.direction.x > 0:
						self.hitbox.right = sprite.hitbox.left
					if self.direction.x < 0:
						self.hitbox.left = sprite.hitbox.right
					self.rect.centerx = self.hitbox.centerx
				else:
					if self.direction.y > 0:
						self.hitbox.bottom = sprite.hitbox.top
					if self.direction.y < 0:
						self.hitbox.top = sprite.hitbox.bottom
					self.rect.centery = self.hitbox.centery

	# Called every frame. Reads input and moves unless blocked, then animates.
	def update(self, dt):
		self.y_sort = self.rect.centery
		if not self.blocked:
			self.input()
			self.move(dt)
		self.animate(dt)
