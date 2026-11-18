# test_post_development.py
# Section 4: the post-development tests planned in section 2.7, run on the finished game.
# Each test plays the game the way a user would (holding keys, walking into things, talking to trainers)
# and checks what happens. A screenshot of every test is saved as evidence.
# Run with:  python test_post_development.py   (screenshots go in the folder named by EVIDENCE, if set)

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import shutil
import time
import pygame
import controls
from main import Game
from monster import Monster
from game_data import TRAINER_DATA
from battle import Battle, catch_chance
import battle_rules

EVIDENCE = os.environ.get('EVIDENCE')
results = []
def check(number, name, expected, actual, passed):
	results.append((number, name, expected, actual, 'Pass' if passed else 'Fail'))
	if os.environ.get('VERBOSE'):
		print('   ', number, 'Pass' if passed else 'FAIL', actual, flush = True)
def shot(number):
	if EVIDENCE:
		os.makedirs(EVIDENCE, exist_ok = True)
		pygame.image.save(game.display_surface, os.path.join(EVIDENCE, f'test_{number:02d}.png'))

shutil.rmtree('saves_post_test', ignore_errors = True)
game = Game()
game.autosave = lambda: None
from save_system import ProfileManager
game.profiles = ProfileManager('saves_post_test')   # a separate folder, so no real account is touched
profile, _ = game.profiles.create('Tester', 'Blue#Sky2026', 'question_pet', 'Rex')
game.select_profile(profile)
game.ui.screens = []
game.start_new_game(1, 'Sparchu')
game.ui.screens = []

def frames(count, dt = 1 / 60):
	for _ in range(count):
		game.frame(dt)

def hold(keys, seconds):
	# the keys are held the same way the on-screen D-pad holds them (one 'finger' per key)
	game.touch.fingers = {number: key for number, key in enumerate(keys)}
	frames(int(seconds * 60))
	game.touch.fingers = {}
	frames(1)

def press(key, count = 2):
	pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key = key, unicode = '', mod = 0, scancode = 0))
	controls.virtual_pressed.add(key)
	frames(count)

def place(x, y):
	game.player.rect.center = (x, y)
	game.player.hitbox.center = game.player.rect.center

challengeable = False
def fresh_world(spawn = 'house'):
	game.battle, game.dialog_tree, game.transition_target = None, None, None
	game.tint_mode, game.tint_progress = 'untint', 0
	game.ui.screens = []
	game.change_map('world', spawn)
	frames(30)
	game.player.unblock()
	game.cooldown = 0
	if not challengeable:   # the movement tests are not interrupted by trainers spotting the player
		for character in game.character_sprites:
			character.has_noticed = True

def open_ground():
	# a spot with nothing solid within 120 pixels
	start = pygame.Vector2(game.player.rect.center)
	for dx in range(-600, 601, 40):
		for dy in range(-600, 601, 40):
			area = pygame.FRect(0, 0, 240, 240).move_to(center = start + (dx, dy))
			if not any(s.hitbox.colliderect(area) for s in game.collision_sprites) and not any(s.rect.colliderect(area) for s in game.transition_sprites) \
			   and not any(s.rect.colliderect(area) for s in game.monster_sprites):
				return area.center
	return start

# ---------- Overworld movement and collision ----------
fresh_world()
place(*open_ground())
start = pygame.Vector2(game.player.rect.center)
hold({pygame.K_RIGHT}, 1.0)
moved = game.player.rect.centerx - start.x
check(1, 'Right arrow held', 'Player walks right with the walking animation', f'moved {moved:.0f} px right, facing {game.player.get_state()}', moved > 100 and 'right' in game.player.get_state())
shot(1)

# walk into the nearest tree / wall
fresh_world()
def clear_left(sprite):
	# the strip to the left of this tree must be open ground, so nothing else stops the player first
	strip = pygame.FRect(sprite.hitbox.left - 130, sprite.hitbox.centery - game.player.hitbox.height, 128, game.player.hitbox.height * 2)
	return not any(other.hitbox.colliderect(strip) for other in game.collision_sprites if other is not sprite)
target = min((s for s in game.collision_sprites if s.hitbox.width >= 24 and clear_left(s)), key = lambda s: pygame.Vector2(s.hitbox.center).distance_to(game.player.rect.center))
place(target.hitbox.left - 80, target.hitbox.centery - game.player.hitbox.centery + game.player.rect.centery)
hold({pygame.K_RIGHT}, 2.0)
overlap = game.player.hitbox.colliderect(target.hitbox)
check(2, 'Walk into a tree', 'Player stops at the edge of the hitbox', f'stopped {target.hitbox.left - game.player.hitbox.right:.0f} px from it, overlapping: {overlap}', not overlap and target.hitbox.left - game.player.hitbox.right <= 2)
shot(2)

fresh_world()
place(*open_ground())
start = pygame.Vector2(game.player.rect.center)
hold({pygame.K_UP, pygame.K_RIGHT}, 0.5)
diagonal = start.distance_to(game.player.rect.center)
place(*start)
hold({pygame.K_RIGHT}, 0.5)
straight = start.distance_to(game.player.rect.center)
check(3, 'Up and right together', 'Diagonal movement at the same speed as straight', f'diagonal {diagonal:.0f} px, straight {straight:.0f} px in 0.5 s', abs(diagonal - straight) < straight * 0.05)
shot(3)

place(*start)
hold({pygame.K_LEFT, pygame.K_RIGHT}, 0.5)
check(4, 'Left and right together', 'Directions cancel out - player stands still', f'moved {start.distance_to(game.player.rect.center):.0f} px', start.distance_to(game.player.rect.center) < 1)
before = (pygame.Vector2(game.player.rect.center), len(game.ui.screens), game.battle)
press(pygame.K_q, 10)
after = (pygame.Vector2(game.player.rect.center), len(game.ui.screens), game.battle)
check(5, 'Q key', 'Nothing happens', 'no movement, no menu, no battle' if before == after else f'changed: {after}', before == after)

# ---------- Map transitions ----------
fresh_world()
door = min(game.transition_sprites, key = lambda s: pygame.Vector2(s.rect.center).distance_to(game.player.rect.center))
place(door.rect.centerx, door.rect.bottom + 40)
hold({pygame.K_UP}, 1.2)
shot(6)
frames(120)
check(6, 'Walk through the house door', 'Fade to black, the house loads with the player at its start point', f'map now "{game.current_map}"', game.current_map == door.target[0])

fresh_world()
door = min(game.transition_sprites, key = lambda s: pygame.Vector2(s.rect.center).distance_to(game.player.rect.center))
place(door.rect.centerx, door.rect.bottom + game.player.hitbox.height / 2 + 1)
frames(5)
outside = game.tint_mode == 'untint' and game.transition_target is None
place(door.rect.centerx, door.rect.bottom + game.player.hitbox.height / 2 - 2)
frames(3)
inside = game.transition_target is not None
check(7, 'Edge of the transition zone', 'Only starts when the hitbox overlaps the zone', f'1 px outside: no transition ({outside}); 2 px inside: transition ({inside})', outside and inside)

position = pygame.Vector2(game.player.rect.center)
hold({pygame.K_DOWN}, 0.3)
check(8, 'Arrow keys during the fade', 'Player cannot move until the new map loads', f'moved {position.distance_to(game.player.rect.center):.0f} px while blocked = {game.player.blocked}', position.distance_to(game.player.rect.center) < 1)
frames(150)

# ---------- Trainers, dialogue and the nurse ----------
challengeable = True
def trainer(character_id):
	return next(c for c in game.character_sprites if getattr(c, 'character_id', None) == character_id)
fresh_world()
o1 = trainer('o1')
TRAINER_DATA['o1']['defeated'] = False
o1.has_noticed = o1.has_moved = False
facing = {'down': (0, 1), 'up': (0, -1), 'left': (-1, 0), 'right': (1, 0)}
o1.can_rotate = False
o1.facing_direction = 'down'
place(o1.rect.centerx, o1.rect.centery + 120)
frames(150)
shot(9)
noticed = o1.has_noticed
started = game.dialog_tree is not None
check(9, 'Walk in front of trainer o1', 'Notice icon and sound, the trainer walks over and the dialogue starts', f'noticed: {noticed}, dialogue open: {started}', noticed and started)
game.dialog_tree = None

fresh_world()
o1 = trainer('o1')
o1.has_noticed = o1.has_moved = False
wall = pygame.FRect(o1.rect.centerx - 30, o1.rect.centery + 40, 60, 20)   # a wall straight between them
o1.collision_rects.append(wall)
o1.can_rotate, o1.facing_direction = False, 'down'
place(o1.rect.centerx, o1.rect.centery + 120)
frames(90)
check(10, 'Wall between trainer and player', 'Trainer does not notice the player', f'noticed: {o1.has_noticed}, line of sight: {bool(o1.has_los())}', not o1.has_noticed)
o1.collision_rects.remove(wall)

fresh_world()
o1 = trainer('o1')
TRAINER_DATA['o1']['defeated'] = True
o1.has_noticed = o1.has_moved = False
place(o1.rect.centerx, o1.rect.centery + 90)
game.player.change_facing_direction(o1.rect.center)
press(pygame.K_SPACE, 10)
lines = o1.get_dialog()
battle_started = game.battle is not None or game.transition_target is not None and not isinstance(game.transition_target, tuple)
check(11, 'Defeated trainer', 'Shows the "defeated" dialogue, no battle', f'dialogue: "{lines[0] if isinstance(lines[0], str) else lines[0][1]}"; battle: {battle_started}', lines == TRAINER_DATA['o1']['dialog']['defeated'] and not battle_started)
shot(11)

tree = game.dialog_tree
if tree:
	time.sleep(0.6)   # the dialogue timer runs on the real clock: wait until the first line may be skipped
	before = tree.dialog_index
	for _ in range(6):   # six presses within about a tenth of a second
		press(pygame.K_SPACE, 1)
	after = tree.dialog_index
	check(12, 'Space pressed rapidly', 'Lines advance at most once every half second', f'6 quick presses moved the dialogue from line {before} to line {after}', after - before <= 1)
else:
	check(12, 'Space pressed rapidly', 'Lines advance at most once every half second', 'no dialogue open', False)
game.dialog_tree = None
TRAINER_DATA['o1']['defeated'] = False

for monster in game.player_monsters.values():
	monster.health, monster.energy = 1, 0
game.heal_party()
full = all(m.health == m.get_stat('max_health') and m.energy == m.get_stat('max_energy') for m in game.player_monsters.values())
check(13, 'Nurse with every monster damaged', 'Every monster back to full health and energy', 'all full' if full else 'not all full', full)

# ---------- Wild encounters ----------
fresh_world()
patch = min((s for s in game.monster_sprites if s.biome == 'forest'), key = lambda s: pygame.Vector2(s.rect.center).distance_to(game.player.rect.center))
place(*patch.rect.center)
game.encounter_timer.duration = 300
started_battle = False
end = time.time() + 4
direction = pygame.K_RIGHT
while time.time() < end and not started_battle:   # walk back and forth in the grass in real time
	game.touch.fingers = {0: direction}
	frames(6)
	time.sleep(0.05)
	if not patch.rect.colliderect(game.player.hitbox):
		direction = pygame.K_LEFT if direction == pygame.K_RIGHT else pygame.K_RIGHT
		place(*patch.rect.center)
	started_battle = isinstance(game.transition_target, Battle) or game.battle is not None
game.touch.fingers = {}
shot(14)
check(14, 'Walking in forest grass', 'A battle starts after a short delay', 'battle started' if started_battle else 'no battle', started_battle)

fresh_world()
place(*patch.rect.center)
game.encounter_timer.deactivate() if hasattr(game.encounter_timer, 'deactivate') else None
game.player.direction = pygame.Vector2()
frames(240)
standing = not (isinstance(game.transition_target, Battle) or game.battle)
check(15, 'Standing still in grass', 'No encounter starts', 'no battle after 4 s' if standing else 'a battle started', standing)

fresh_world()
place(*patch.rect.center)
game.encounter_timer.duration = 800
hold({pygame.K_RIGHT}, 0.1)
place(*open_ground())
frames(120)
left = not (isinstance(game.transition_target, Battle) or game.battle)
check(16, 'Leave the grass before the timer ends', 'No battle when the timer finishes', 'no battle' if left else 'a battle started', left)

# ---------- Battle system ----------
def new_battle(mine, theirs, character = None):
	battle = Battle(mine, theirs, game.monster_frames, game.bg_frames['forest'], game.fonts, lambda c, lost = False: ended.append(lost), character, {}, {'capture_orb': 5}, False, game.use_item)
	battle.crit_chance = 0
	game.battle = battle
	return battle
def my_turn(battle):
	for _ in range(900):
		frames(1)
		if battle.current_monster and battle.selection_mode == 'general' and battle.player_sprites.has(battle.current_monster):
			return True
	return False
ended = []
fresh_world()
battle = new_battle({0: Monster('Charmadillo', 30), 1: Monster('Finsta', 20)}, {0: Monster('Pluma', 30)})
my_turn(battle)
target = battle.opponent_sprites.sprites()[0]
before = target.monster.health
battle.indexes['general'] = 0
press(pygame.K_SPACE)
battle.indexes['attacks'] = battle.current_monster.monster.get_abilities(all = False).index('flame burst') if 'flame burst' in battle.current_monster.monster.get_abilities(all = False) else 0
press(pygame.K_SPACE)
if battle.selection_mode == 'target':
	press(pygame.K_SPACE)
frames(150)
shot(17)
check(17, 'Fight -> fire move -> target', 'Animation and sound play, the target loses health', f'Pluma health {before:.0f} -> {target.monster.health:.0f}', target.monster.health < before)

fresh_world()
battle = new_battle({0: Monster('Charmadillo', 30), 1: Monster('Finsta', 20)}, {0: Monster('Larvea', 5)})
my_turn(battle)
battle.indexes['general'] = list(__import__('settings').BATTLE_CHOICES['full']).index('switch')
press(pygame.K_SPACE)
press(pygame.K_SPACE, 30)
names = [s.monster.name for s in battle.player_sprites]
check(18, 'Switch -> another monster', 'The chosen monster replaces the active one', f'on the field: {names}', names == ['Finsta'])
shot(18)

# catching: the rule changed in Iteration 14 from "below 90% health always works" to a chance
finsta = Monster('Finsta', 15)
finsta.health = finsta.get_stat('max_health') * 0.9 - 0.5
chance_low = catch_chance(finsta, 'capture_orb')
finsta.health = finsta.get_stat('max_health')
chance_full = catch_chance(finsta, 'capture_orb')
check(19, 'Catch Finsta just below 90% health', 'Can be caught (Iteration 14 made catching a chance that grows as health falls)', f'chance {chance_low:.0%} (vs {chance_full:.0%} at full health)', chance_low > chance_full > 0)
ended = []
fresh_world()
battle = new_battle({0: Monster('Charmadillo', 30)}, {0: Monster('Finsta', 15)})
import random as random_module
my_turn(battle)
real_random = random_module.random
import battle as battle_module
battle_module.random = lambda: 0.99   # an unlucky throw
battle.selected_orb = 'capture_orb'
battle.throw_orb(battle.opponent_sprites.sprites()[0])
frames(120)
battle_module.random = real_random
caught = len(battle.caught)
shot(20)
check(20, 'Catch at full health (unlucky throw)', 'The orb breaks free - the monster is not caught', f'caught: {caught}, still in battle: {bool(battle.opponent_sprites)}', caught == 0 and bool(battle.opponent_sprites))

ended = []
fresh_world()
mine = Monster('Charmadillo', 30)
battle = new_battle({0: mine}, {0: Monster('Larvea', 5)})
my_turn(battle)
xp_before = mine.xp
battle.opponent_sprites.sprites()[0].monster.health = 0
battle.check_death()
frames(120)
check(21, "Opponent's last monster faints", 'Experience is given and the battle ends', f'xp {xp_before:.0f} -> {mine.xp:.0f}, battle ended: {bool(ended)}', mine.xp > xp_before and bool(ended))

fresh_world()
battle = new_battle({0: Monster('Charmadillo', 30)}, {0: Monster('Larvea', 5)})
my_turn(battle)
press(pygame.K_ESCAPE, 5)
check(22, 'Escape on the general menu', 'Nothing happens (no menu to go back to)', f'menu still "{battle.selection_mode}", battle still on: {game.battle is battle}', battle.selection_mode == 'general' and game.battle is battle)
shot(22)
game.battle = None

# ---------- Monster index ----------
fresh_world()
game.player_monsters.clear()
for i, name in enumerate(('Sparchu', 'Finsta', 'Plumette', 'Atrox')):
	game.player_monsters[i] = Monster(name, 10)
game.index_open = False
press(pygame.K_RETURN, 5)
shot(23)
opened = game.index_open and game.player.blocked
check(23, 'Enter key in the world', 'The monster index opens and the player stops', f'index open: {game.index_open}, player blocked: {game.player.blocked}', opened)
index = game.monster_index
index.index = 0
press(pygame.K_SPACE, 3)
index.index = 3
press(pygame.K_SPACE, 3)
order = [game.player_monsters[i].name for i in sorted(game.player_monsters)]
check(24, 'Space on slot 0, then slot 3', 'The two monsters swap places', f'order now {order}', order[0] == 'Atrox' and order[3] == 'Sparchu')
index.index = 0
press(pygame.K_UP, 3)
check(25, 'Up arrow on the first monster', 'Selection wraps round to the last monster', f'selected slot {index.index} of {len(game.player_monsters)}', index.index == len(game.player_monsters) - 1)
press(pygame.K_RETURN, 3)
game.index_open = False
game.player.unblock()

fresh_world()
battle = new_battle({0: Monster('Charmadillo', 30)}, {0: Monster('Larvea', 5)})
my_turn(battle)
press(pygame.K_RETURN, 3)
check(26, 'Enter during a battle', 'The index does not open', f'index open: {game.index_open}', not game.index_open)
game.battle = None

# ---------- Evolution and defeat ----------
fresh_world()
plumette = Monster('Plumette', 14)
game.player_monsters.clear()
game.player_monsters[0] = plumette
plumette.update_xp(plumette.level_up - plumette.xp + 1)
game.check_evolution() if hasattr(game, 'check_evolution') else None
frames(600)
shot(27)
names = [m.name for m in game.player_monsters.values()]
check(27, 'Plumette reaches level 15', 'The evolution plays and Ivieron is in the party', f'party: {names}', 'Ivieron' in names)

fresh_world()
game.player_monsters.clear()
game.player_monsters[0] = Monster('Sparchu', 5)
game.evolution = None
battle = new_battle(game.player_monsters, {0: Monster('Charmadillo', 40)})
battle.end_battle = game.end_battle
frames(5)
battle.player_sprites.sprites()[0].monster.health = 0
battle.check_death()
frames(400)
shot(28)
healed = all(m.health == m.get_stat('max_health') for m in game.player_monsters.values())
check(28, 'All monsters faint', 'The game does not close: the player goes back to the hospital with the party healed', f'game running, map "{game.current_map}", party healed: {healed}', healed and game.battle is None)

# ---------- results ----------
passed = sum(1 for r in results if r[4] == 'Pass')
for number, name, expected, actual, outcome in results:
	print(f'{outcome.upper()} | {number} | {name} | expected {expected} | actual {actual}')
print(f'{passed}/{len(results)} tests passed')
shutil.rmtree('saves_post_test', ignore_errors = True)
