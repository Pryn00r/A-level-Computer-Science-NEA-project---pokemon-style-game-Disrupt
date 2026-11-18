# support.py
# Reusable helper functions: importers that load images, sprite sheets, maps and sounds,
# plus draw_bar (every bar in the game) and check_connections (is one entity facing another).
# Used by: main.py, sprites.py, groups.py, entities.py, battle.py, monster_index.py

from settings import *
from os.path import join   # asset() comes from settings
from os import walk
from pytmx.util_pygame import load_pygame

# import functions
# Loads one image. Parameters: *path (folders + file name), alpha (keep transparency), format (file extension).
# Returns: pygame Surface.
def import_image(*path, alpha = True, format = 'png'):
	full_path = asset(*path) + f'.{format}'
	surf = pygame.image.load(full_path).convert_alpha() if alpha else pygame.image.load(full_path).convert()
	return surf

# Loads every image in a folder in number order (0.png, 1.png...). Returns: list of Surfaces (animation frames).
def import_folder(*path):
	frames = []
	for folder_path, sub_folders, image_names in walk(asset(*path)):
		for image_name in sorted(image_names, key = lambda name: int(name.split('.')[0])):
			full_path = join(folder_path, image_name)
			surf = pygame.image.load(full_path).convert_alpha()
			frames.append(surf)
	return frames

# Loads every image in a folder. Returns: dict of file name (no extension) -> Surface.
def import_folder_dict(*path):
	frames = {}
	for folder_path, sub_folders, image_names in walk(asset(*path)):
		for image_name in image_names:
			full_path = join(folder_path, image_name)
			surf = pygame.image.load(full_path).convert_alpha()
			frames[image_name.split('.')[0]] = surf
	return frames

# Cuts a sprite sheet into a grid of equal cells. Parameters: cols, rows (integers), *path.
# Returns: dict of (col, row) -> Surface. Green is used as a transparent colour key.
def import_tilemap(cols, rows, *path):
	frames = {}
	surf = import_image(*path)
	cell_width, cell_height = surf.get_width() / cols, surf.get_height() / rows
	for col in range(cols):
		for row in range(rows):
			cutout_rect = pygame.Rect(col * cell_width, row * cell_height,cell_width,cell_height)
			cutout_surf = pygame.Surface((cell_width, cell_height))
			cutout_surf.fill('green')
			cutout_surf.set_colorkey('green')
			cutout_surf.blit(surf, (0,0), cutout_rect)
			frames[(col, row)] = cutout_surf
	return frames

# Cuts a 4x4 character sheet into walking animations. Each row is one direction; column 0 is
# also used as the idle frame. Returns: dict e.g. {'down': [...], 'down_idle': [...]}.
def character_importer(cols, rows, *path):
	frame_dict = import_tilemap(cols, rows, *path)
	new_dict = {}
	for row, direction in enumerate(('down', 'left', 'right', 'up')):
		new_dict[direction] = [frame_dict[(col, row)] for col in range(cols)]
		new_dict[f'{direction}_idle'] = [frame_dict[(0, row)]]
	return new_dict

# Runs character_importer on every character sheet in a folder. Returns: dict of name -> animations.
def all_character_import(*path):
	new_dict = {}
	for _, __, image_names in walk(asset(*path)):
		for image in image_names:
			image_name = image.split('.')[0]
			new_dict[image_name] = character_importer(4,4,*path, image_name)
	return new_dict

# Cuts the coast tileset into animated frames for each terrain type and each side.
# Returns: dict terrain -> side -> list of frames.
def coast_importer(cols, rows, *path):
	frame_dict = import_tilemap(cols, rows, *path)
	new_dict = {}
	terrains = ['grass', 'grass_i', 'sand_i', 'sand', 'rock', 'rock_i', 'ice', 'ice_i']
	sides = {
		'topleft': (0,0), 'top': (1,0), 'topright': (2,0), 
		'left': (0,1), 'right': (2,1), 'bottomleft': (0,2), 
		'bottom': (1,2), 'bottomright': (2,2)}
	for index, terrain in enumerate(terrains):
		new_dict[terrain] = {}
		for key, pos in sides.items():
			new_dict[terrain][key] = [frame_dict[(pos[0] + index * 3, pos[1] + row)] for row in range(0,rows, 3)]
	return new_dict

# Loads every Tiled map in a folder. Returns: dict of map name -> loaded TiledMap.
def tmx_importer(*path):
	tmx_dict = {}
	for folder_path, sub_folders, file_names in walk(asset(*path)):
		for file in file_names:
			if not file.endswith('.tmx'):
				continue
			tmx_dict[file.split('.')[0]] = load_pygame(join(folder_path, file))
	return tmx_dict

# Cuts each monster sheet into an 'idle' row and an 'attack' row. Returns: dict name -> state -> frames.
def monster_importer(cols, rows, *path):
	monster_dict = {}
	for folder_path, sub_folders, image_names in walk(asset(*path)):
		for image in image_names:
			image_name = image.split('.')[0]
			monster_dict[image_name] = {}
			frame_dict = import_tilemap(cols, rows, *path, image_name)
			for row, key in enumerate(('idle', 'attack')):
				monster_dict[image_name][key] = [frame_dict[(col,row)] for col in range(cols)]
	return monster_dict

# Makes a white outline for every monster frame by drawing a white silhouette shifted in 8 directions.
# Parameters: frame_dict (from monster_importer), width (outline thickness in px). Returns: same shape dict.
def outline_creator(frame_dict, width):
	outline_frame_dict = {}
	for monster, monster_frames in frame_dict.items():
		outline_frame_dict[monster] = {}
		for state, frames in monster_frames.items():
			outline_frame_dict[monster][state] = []
			for frame in frames:
				new_surf = pygame.Surface(vector(frame.get_size()) + vector(width * 2), pygame.SRCALPHA)
				new_surf.fill((0,0,0,0))
				white_frame = pygame.mask.from_surface(frame).to_surface()
				white_frame.set_colorkey('black')

				new_surf.blit(white_frame, (0,0))
				new_surf.blit(white_frame, (width,0))
				new_surf.blit(white_frame, (width * 2,0))
				new_surf.blit(white_frame, (width * 2,width))
				new_surf.blit(white_frame, (width * 2,width * 2))
				new_surf.blit(white_frame, (width,width * 2))
				new_surf.blit(white_frame, (0,width * 2))
				new_surf.blit(white_frame, (0,width))
				outline_frame_dict[monster][state].append(new_surf)
	return outline_frame_dict

# Cuts each attack animation sheet (4 frames in a row). Returns: dict attack animation name -> frames.
def attack_importer(*path):
	attack_dict = {}
	for folder_path, _, image_names in walk(asset(*path)):
		for image in image_names:
			image_name = image.split('.')[0]
			# Iteration 21: the number of frames is worked out from the image (the old sheets have 4, the new ones 6)
			sheet = pygame.image.load(join(folder_path, image))
			columns = max(1, sheet.get_width() // sheet.get_height())
			attack_dict[image_name] = same_size(list(import_tilemap(columns, 1, folder_path, image_name).values()))
	return attack_dict

# Iteration 34: the packs drew their effects at different sizes inside the frame, so a small picture
# looked tiny on screen. The empty space round every frame is cut off and the effect is scaled so its
# longest side is ATTACK_SIZE pixels. (The battle then makes stronger moves bigger - see AttackSprite.)
ATTACK_SIZE = 180
def same_size(frames):
	frames = [frame.convert_alpha() for frame in frames]
	boxes = [frame.get_bounding_rect() for frame in frames if frame.get_bounding_rect().width]
	if not boxes:
		return frames
	union = boxes[0].unionall(boxes[1:])
	scale = ATTACK_SIZE / max(union.width, union.height)
	size = (max(1, round(union.width * scale)), max(1, round(union.height * scale)))
	return [pygame.transform.scale(frame.subsurface(union), size) for frame in frames]

# Loads every sound file in a folder. Returns: dict of file name -> pygame Sound.
def audio_importer(*path):
	files = {}
	for folder_path, _, file_names in walk(asset(*path)):
		for file_name in file_names:
			full_path = join(folder_path, file_name)
			files[file_name.split('.')[0]] = pygame.mixer.Sound(full_path)
	return files

# game functions
# Iteration 18: colour for a stat bar - red when the stat is low, yellow in the middle, green when high.
# Parameter: ratio (0 to 1). Returns an (r, g, b) colour.
def stat_color(ratio):
	ratio = max(0, min(1, ratio))
	if ratio < 0.5:
		return (230, int(70 + 370 * ratio), 60)            # red -> yellow
	return (int(230 - 300 * (ratio - 0.5)), 205, 70)       # yellow -> green

# Draws a progress bar (health, energy, initiative, xp, stats).
# Parameters: surface to draw on, rect (full bar size), value, max_value, color, bg_color, radius (corner rounding).
# The progress width is clamped between 0 and the full width (range check) so the bar never overflows.
def draw_bar(surface, rect, value, max_value, color, bg_color, radius = 1):
	ratio = rect.width / max_value
	bg_rect = rect.copy()
	progress = max(0, min(rect.width,value * ratio))
	progress_rect = pygame.FRect(rect.topleft, (progress,rect.height))
	pygame.draw.rect(surface, bg_color, bg_rect, 0, radius)
	pygame.draw.rect(surface, color, progress_rect, 0, radius)

# Returns True if target is within radius of entity AND in the direction entity is facing
# (within tolerance px of a straight line). Used for talking to characters and trainer line of sight.
def check_connections(radius, entity, target, tolerance = 30):
	relation = vector(target.rect.center) - vector(entity.rect.center)
	if relation.length() < radius:
		if entity.facing_direction == 'left' and relation.x < 0 and abs(relation.y) < tolerance or\
		   entity.facing_direction == 'right' and relation.x > 0 and abs(relation.y) < tolerance or\
		   entity.facing_direction == 'up' and relation.y < 0 and abs(relation.x) < tolerance or\
		   entity.facing_direction == 'down' and relation.y > 0 and abs(relation.x) < tolerance:
			return True