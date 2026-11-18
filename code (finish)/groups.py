# groups.py
# Custom sprite groups. AllSprites draws the overworld as a camera centred on the player,
# BattleSprites draws the battle and decides which outlines to show.

from settings import * 
from support import import_image
from entities import Entity
from sprites import AnimatedSprite, MonsterPatchSprite
from math import sin

# Camera group for the overworld.
class AllSprites(pygame.sprite.Group):
	def __init__(self):
		super().__init__()
		self.display_surface = pygame.display.get_surface()
		self.offset = vector()
		self.shadow_surf = import_image('graphics', 'other', 'shadow')
		self.notice_surf = import_image('graphics', 'ui', 'notice')
		self.ground_hook = None   # Iteration 20: a function that draws footprints under the characters

	# Draws every sprite offset so the player is in the centre. Background layers are drawn first, then the
	# main layer sorted by y_sort (lower sprites in front), then the top layer. Entities get a shadow and the
	# player gets a '!' icon when noticed. Parameter: player (Player). Called every frame from Game.run.
	def draw(self, player):
		self.offset.x = -(player.rect.centerx - WINDOW_WIDTH / 2)
		self.offset.y = -(player.rect.centery - WINDOW_HEIGHT / 2)

		# Iteration 18: only sprites on (or just off) the screen are drawn. The world map has about
		# 7,900 sprites but only a few hundred are ever visible, so this makes drawing much faster.
		view = pygame.FRect(-self.offset, (WINDOW_WIDTH, WINDOW_HEIGHT)).inflate(TILE_SIZE * 4, TILE_SIZE * 4)
		visible = [sprite for sprite in self if view.colliderect(sprite.rect)]
		bg_sprites = [sprite for sprite in visible if sprite.z < WORLD_LAYERS['main']]
		main_sprites = sorted([sprite for sprite in visible if sprite.z == WORLD_LAYERS['main']], key = lambda sprite: sprite.y_sort)
		fg_sprites = [sprite for sprite in visible if sprite.z > WORLD_LAYERS['main']]

		ticks = pygame.time.get_ticks()
		for layer in (bg_sprites, main_sprites, fg_sprites):
			if layer is main_sprites and self.ground_hook:
				self.ground_hook(self.display_surface, self.offset)   # Iteration 20: footprints and dust
			for sprite in layer:
				# Iteration 20: tall grass sways while the player walks through it
				if type(sprite) is MonsterPatchSprite and player.direction and sprite.rect.colliderect(player.hitbox):
					self.display_surface.blit(sprite.image, sprite.rect.topleft + self.offset + vector(sin(ticks / 45) * 2, 0))
					continue
				if isinstance(sprite, Entity):
					self.display_surface.blit(self.shadow_surf, sprite.rect.topleft + self.offset + vector(40,110))
				self.display_surface.blit(sprite.image, sprite.rect.topleft + self.offset)
				if sprite == player and player.noticed:
					rect = self.notice_surf.get_frect(midbottom = sprite.rect.midtop)
					self.display_surface.blit(self.notice_surf, rect.topleft + self.offset)

	# Iteration 18: characters always update (trainers keep looking around), but scenery like water
	# only animates when it is near the screen.
	def update(self, dt):
		AnimatedSprite.world_time += dt   # Iteration 19: one clock for all water/coast animation
		view = pygame.FRect(-self.offset, (WINDOW_WIDTH, WINDOW_HEIGHT)).inflate(TILE_SIZE * 8, TILE_SIZE * 8)
		for sprite in self.sprites():
			if isinstance(sprite, Entity) or view.colliderect(sprite.rect):
				sprite.update(dt)

# Sprite group for the battle screen.
class BattleSprites(pygame.sprite.Group):
	def __init__(self):
		super().__init__()
		self.display_surface = pygame.display.get_surface()

	# Draws all battle sprites in z order. Outlines are only drawn for the active monster, or for the
	# monster currently being targeted when the player is choosing a target. Called from Battle.update.
	def draw(self, current_monster_sprite, side, mode, target_index, player_sprites, opponent_sprites):
		# get available positions 
		sprite_group = opponent_sprites if side == 'opponent' else player_sprites
		sprites = {sprite.pos_index: sprite for sprite in sprite_group}
		monster_sprite = sprites[list(sprites.keys())[target_index]] if sprites else None

		for sprite in sorted(self, key = lambda sprite: sprite.z):
			# Iteration 24: a monster inside a wobbling orb is hidden, and a hit knocks it back a little
			owner = getattr(sprite, 'monster_sprite', sprite)
			if getattr(owner, 'hidden', False):
				continue
			knock = getattr(owner, 'knock', 0)
			if knock > 0 and sprite is owner:
				side = 1 if owner.entity == 'opponent' else -1
				self.display_surface.blit(sprite.image, sprite.rect.move(side * 14 * knock, 0))
				continue
			if sprite.z == BATTLE_LAYERS['outline']:
				if sprite.monster_sprite == current_monster_sprite and not (mode == 'target' and side == 'player') or\
				   sprite.monster_sprite == monster_sprite and sprite.monster_sprite.entity == side and mode and mode == 'target':
					self.display_surface.blit(sprite.image, sprite.rect)
			else:
				self.display_surface.blit(sprite.image, sprite.rect)