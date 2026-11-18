# postgame.py
# Iteration 25c: things that open up after the ending.
#   - The Glitch Zone: a corrupted copy of the water gym, reached by fast travel. Strong wild monsters
#     jump out anywhere (no grass needed) and three boss monsters wait inside.
#   - Rematches: every badge trainer can be battled again once a day, at your level.
#   - Boss monsters: one monster with three times the health, shown bigger. Beaten once each.

from random import random, randint, sample

from settings import *
from game_data import MONSTER_DATA, TRAINER_DATA, BADGE_DATA
from entities import Character
from localisation import t

GLITCH_MAP = 'glitch'
GLITCH_LEVELS = (45, 60)
GLITCH_STEPS = (14, 30)     # tiles walked between wild battles in the Glitch Zone
BOSSES = {
	'boss_charmadillo': ('Charmadillo', 65, (576, 1264)),
	'boss_glacihare':   ('Friolera', 70, (959, 940)),
	'boss_cerebloom':   ('Draem', 75, (769, 300)),
}
BOSS_REWARD = {'coins': 1500, 'items': {'max_ether': 2, 'prime_orb': 1}}   # (Iteration 31: crystals were removed with the materials)
REMATCH_LEVEL_BONUS = 2

def unlocked(game):
	return bool(game.counters.get('ending'))

# ---------- the Glitch Zone ----------
# Makes the Glitch Zone's battle background: the forest background with its colours shifted and scanlines.
def glitch_background(game):
	if 'glitch' not in game.bg_frames:
		image = game.bg_frames['forest'].copy()
		tint = pygame.Surface(image.get_size())
		tint.fill((120, 60, 200))
		image.blit(tint, (0, 0), special_flags = pygame.BLEND_RGB_MULT)
		image.blit(tint, (0, 0), special_flags = pygame.BLEND_RGB_ADD)
		for y in range(0, image.get_height(), 32):
			pygame.draw.line(image, (20, 255, 160), (0, y), (image.get_width(), y), 1)
		game.bg_frames['glitch'] = image
	return 'glitch'

def glitch_monsters(game):
	names = list(MONSTER_DATA)
	monsters = {}
	from monster import Monster
	for index, name in enumerate(sample(names, 2)):
		monster = Monster(name, randint(*GLITCH_LEVELS))
		monster.shiny = random() < game.shiny_chance() * 2   # glitches are shinier
		monsters[index] = monster
	return monsters

# Called every frame in the Glitch Zone with the distance walked.
def glitch_walk(game, tiles):
	if game.current_map != GLITCH_MAP or game.battle or game.transition_target or not tiles:
		return
	game.story['glitch_steps'] = game.story.get('glitch_steps', randint(*GLITCH_STEPS)) - tiles
	if game.story['glitch_steps'] <= 0:
		game.story['glitch_steps'] = randint(*GLITCH_STEPS)
		game.start_wild_battle(glitch_monsters(game), glitch_background(game))

# A flickering, scan-lined screen while in the Glitch Zone (not during battles).
def draw_glitch(game, surface):
	if game.current_map != GLITCH_MAP or game.battle:
		return
	surface.fill((210, 150, 255), special_flags = pygame.BLEND_RGB_MULT)   # everything turns purple
	lines = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
	for y in range(0, WINDOW_HEIGHT, 4):
		pygame.draw.line(lines, (0, 0, 0, 40), (0, y), (WINDOW_WIDTH, y))
	surface.blit(lines, (0, 0))
	if random() < 0.08:   # now and then a strip of the screen jumps sideways
		y, height = randint(0, WINDOW_HEIGHT - 40), randint(6, 40)
		strip = surface.subsurface((0, y, WINDOW_WIDTH, height)).copy()
		surface.blit(strip, (randint(-30, 30), y))
		surface.fill((60, 255, 180), (0, y, WINDOW_WIDTH, 2), special_flags = pygame.BLEND_RGB_ADD)

# ---------- bosses ----------
def boss_frames(game, species):
	idle = game.monster_frames['monsters'][species]['idle']
	frames = [pygame.transform.scale_by(frame, 0.9) for frame in idle]
	return {state: frames for state in ('down', 'up', 'left', 'right', 'down_idle', 'up_idle', 'left_idle', 'right_idle')}

def place_bosses(game):
	if game.current_map != GLITCH_MAP:
		return []
	placed = []
	for boss_id, (species, level, pos) in BOSSES.items():
		if boss_id in game.story.get('bosses', []):
			continue
		TRAINER_DATA[boss_id] = {
			'monsters': {0: (species, level)}, 'dialog': {'default': [t('boss_roar', monster = species)], 'defeated': [t('boss_gone')]},
			'directions': ['down'], 'look_around': False, 'defeated': False, 'biome': 'glitch', 'boss': True,
		}
		placed.append(Character(pos = pos, frames = boss_frames(game, species), groups = (game.all_sprites, game.collision_sprites, game.character_sprites),
			facing_direction = 'down', character_data = TRAINER_DATA[boss_id], player = game.player, create_dialog = game.create_dialog,
			collision_sprites = game.collision_sprites, radius = 0, nurse = False, notice_sound = game.audio['notice'], character_id = boss_id))
	return placed

def make_boss(character):
	for monster in character.monsters.values():
		monster.boss = True
		monster.health = monster.get_stat('max_health')

def boss_beaten(game, boss_id):
	game.story.setdefault('bosses', []).append(boss_id)
	game.coins += BOSS_REWARD['coins']
	for item, amount in BOSS_REWARD['items'].items():
		game.inventory[item] = game.inventory.get(item, 0) + amount
	game.counters['bosses'] = game.counters.get('bosses', 0) + 1
	game.toast(t('boss_beaten', amount = BOSS_REWARD['coins']), 'trophy', 'badge')

# ---------- rematches ----------
def rematch_ready(game, character):
	from datetime import date
	return (unlocked(game) and character.character_id in BADGE_DATA and character.character_data['defeated']
	        and game.story.get('rematches', {}).get(character.character_id) != date.today().isoformat())

# The trainer's team again, but at the player's level (+2).
def rematch_team(game, character):
	from monster import Monster
	level = min(100, game.party_level() + REMATCH_LEVEL_BONUS)
	return {index: Monster(name, level) for index, (name, _) in TRAINER_DATA[character.character_id]['monsters'].items()}

def rematch_done(game, character_id):
	from datetime import date
	game.story.setdefault('rematches', {})[character_id] = date.today().isoformat()
	game.counters['rematches'] = game.counters.get('rematches', 0) + 1
