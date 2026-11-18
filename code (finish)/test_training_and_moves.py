# test_training_and_moves.py
# Automated tests for Iteration 33: training mode, every attack animation used by a move, the fainting
# fix (no green box) and no repeated icons in the menu.
# Run with:  python test_training_and_moves.py   (no window is opened)

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from settings import asset
from game_data import ATTACK_DATA, MONSTER_DATA
import localisation

results = []
def check(name, expected, actual):
	results.append((name, expected, actual, expected == actual))

# ---------- every animation is used ----------
files = {name[:-4] for name in os.listdir(asset('graphics', 'attacks')) if name.endswith('.png')}
used = {data['animation'] for data in ATTACK_DATA.values()}
check('every attack animation is used by a move', set(), files - used)
check('every move has its animation', set(), used - files)
check('there are over 90 moves (Iteration 35 removed ten)', True, len(ATTACK_DATA) > 90)
learnt = {move for data in MONSTER_DATA.values() for move in data['abilities'].values()}
check('every move can be learnt by at least one monster', set(), set(ATTACK_DATA) - learnt)
shared = [move for move in ATTACK_DATA if sum(move in data['abilities'].values() for data in MONSTER_DATA.values()) > 1]
check('lots of moves are shared by more than one monster', True, len(shared) > 40)
missing = []
for lang in ('en', 'it', 'es'):
	localisation.set_language(lang)
	missing += [(lang, move) for move in ATTACK_DATA if localisation.attack_name(move) == f'attack_{move}']
localisation.set_language('en')
check('every move has a name in all 3 languages', [], missing)

# ---------- Iteration 34: no two moves look the same, and bigger moves look bigger ----------
from collections import Counter
import battle_rules as rules
shared_pictures = [name for name, count in Counter(data['animation'] for data in ATTACK_DATA.values()).items() if count > 1]
check('no two moves share an animation', [], shared_pictures)
check('Inferno charges up for a turn first', True, ATTACK_DATA['inferno'].get('charge', False))
check('Annihilate no longer waits to strike last', 0, ATTACK_DATA['annihilate'].get('priority', 0))
check('a strong move is drawn bigger than a weak one', True, rules.animation_scale('inferno') > rules.animation_scale('scratch'))
check('move power is shown as a whole number', (60, None), (rules.move_power('scratch'), rules.move_power('growl')))

# ---------- training mode ----------
from main import Game
import training
game = Game()
game.autosave = lambda: None
monster = training.training_monster('Pouch')
check('a training monster is level 50', 50, monster.level)
check('it can use every move it knows, not just 4', monster.known_moves(), monster.get_abilities())
screen = training.TrainingScreen(game.ui, 'Charmadillo')
battle = screen.battle
check('the training battle has one Pouch to hit', ['Pouch'], [s.monster.name for s in battle.opponent_sprites])
dummy = battle.opponent_sprites.sprites()[0]
dummy.monster.health = 0
battle.check_death()
check('a knocked-out Pouch is counted', 1, screen.knockouts)
check('and a fresh Pouch at full health is sent out next', ('Pouch', True), (dummy.next_monster_data[0].name, dummy.next_monster_data[0].health > 0) if dummy.next_monster_data else None)
trainee = battle.player_sprites.sprites()[0]
trainee.monster.health = 0
battle.check_death()
check('your monster cannot faint in training', trainee.monster.get_stat('max_health'), trainee.monster.health)
trainee.monster.energy = 0
screen.update(1 / 60)
check('your monster never runs out of energy', trainee.monster.get_stat('max_energy'), trainee.monster.energy)
battle.current_monster = dummy
screen.dummy_turn()
check('the Pouch does not attack on its turn', ('idle', None), (dummy.state, battle.current_monster))
dummy_now = battle.opponent_sprites.sprites()[-1].monster
dummy_now.health, dummy_now.status, dummy_now.stages = 10, 'burn', {'defense': -2}
screen.handle_key(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_r))
check('R resets the Pouch (no status or stat changes)', (None, {}), (dummy_now.status, dummy_now.stages))
battle.selection_mode = 'attacks'
screen.handle_key(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_ESCAPE))
check('Esc in the move list only closes the list', False, screen.done)
battle.selection_mode = 'general'
screen.handle_key(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_ESCAPE))
check('Esc leaves training', True, screen.done)
screen.done = False
before = dict(game.player_monsters)
battle.run_away()
check('Run leaves training too', True, screen.done)
check('training does not change your party', before, game.player_monsters)

# ---------- fainting: no green box ----------
from sprites import MonsterSprite
frames = game.monster_frames['monsters']['Larvea']
sprite = battle.opponent_sprites.sprites()[0] if battle.opponent_sprites else None
if sprite:
	sprite.timers['kill'].activate()
	sprite.animate(0.01)
	corner = sprite.image.get_at((0, 0))
	check('a fainting monster has no green background', True, corner.a == 0 or corner[:3] != (0, 255, 0))

# ---------- Iteration 35: the move list after playtesting ----------
from game_data import REMOVED_MOVES, current_move
check('the removed moves are gone', [], [m for m in ('spark', 'fire', 'flame wheel', 'ember dash', 'firework', 'root bind', 'seed shot', 'water gun', 'splash', 'soak') if m in ATTACK_DATA])
check('Grassy Heal is now the attack Bramble Cage', ('opponent', 'grass_grow'), (ATTACK_DATA['bramble cage']['target'], ATTACK_DATA['bramble cage']['animation']))
check('Leaf Storm is the healing move', ('player', 'heal'), (ATTACK_DATA['leaf storm']['target'], ATTACK_DATA['leaf storm'].get('kind')))
check('Sleep Spores is a bug move, drawn bigger', ('bug', True), (ATTACK_DATA['sleep spores']['element'], rules.animation_scale('sleep spores') > 1))
check('Aqua Jet is now the ice move Frost Jet', 'ice', ATTACK_DATA['frost jet']['element'])
check('Ink Spray is now the poison move Toxic Splash', 'poison', ATTACK_DATA['toxic splash']['element'])
check('Bubble uses the bubble animation', 'soak', ATTACK_DATA['bubble']['animation'])
check('Venom Burst and Toxic swapped animations, Venom Burst drawn bigger', ('toxic', 'venom', True),
      (ATTACK_DATA['venom burst']['animation'], ATTACK_DATA['toxic']['animation'], rules.animation_scale('venom burst') > rules.animation_scale('toxic')))
check('Solar Beam has its own new animation', 'solar_beam', ATTACK_DATA['solar beam']['animation'])
check('Draem does not learn Bubble', False, 'bubble' in MONSTER_DATA['Draem']['abilities'].values())
check('Doom Pulse is a normal move', 'normal', ATTACK_DATA['doom pulse']['element'])
check('Dark Pulse is a dark finishing move', ('dark', True), (ATTACK_DATA['dark pulse']['element'], ATTACK_DATA['dark pulse']['amount'] >= 3))
check('there are dark, ghost and fairy moves', {'dark', 'ghost', 'fairy'}, {d['element'] for d in ATTACK_DATA.values()} & {'dark', 'ghost', 'fairy'})
check('the new types have icons and names', [], [e for e in ('dark', 'ghost', 'fairy') if not os.path.exists(asset('graphics', 'type_icons', f'{e}.png')) or localisation.t(f'element_{e}') == f'element_{e}'])
check('dark beats psychic', (1.5, 'super'), rules.effectiveness('dark', 'psychic'))
check('fire, plant and water each still have a quick move', set(), {'fire', 'plant', 'water'} - {d['element'] for d in ATTACK_DATA.values() if d.get('priority', 0) > 0})
import save_system
from monster import Monster
old = save_system.serialise_monster(Monster('Sparchu', 20))
old['moves'] = ['spark', 'fire', 'scratch']
check('an old save with removed moves still loads, with the new moves', ['spark shower', 'flame burst', 'scratch'], save_system.deserialise_monster(old).moves)

# ---------- Iteration 35: the full badge art and the battle layout ----------
import ui_style
check('the badge art has wings, frames and gems', True, all(os.path.exists(asset('graphics', 'badges', f'{part}_{colour}.png')) for part in ('wing', 'frame', 'gem') for colour in ('red', 'green', 'blue', 'grey')))
check('a gym badge is wider than a normal one (it has wings)', True, ui_style.badge_image('Leaf', True, True).get_width() > ui_style.badge_image('Rookie', True, False).get_width())
from battle import Battle
team = {0: Monster('Pluma', 40), 1: Monster('Charmadillo', 40), 2: Monster('Finiette', 40)}
fight = Battle(team, {0: Monster('Friolera', 40), 1: Monster('Atrox', 40), 2: Monster('Jacana', 40)}, game.monster_frames, game.bg_frames['forest'], game.fonts, lambda *a, **k: None, None, {}, {}, False, None)
from sprites import MonsterNameSprite, MonsterStatsSprite
overlaps = []
for sprite in list(fight.player_sprites) + list(fight.opponent_sprites):
	body = fight.visible_rect(sprite)
	for label in fight.battle_sprites:
		if getattr(label, 'monster_sprite', None) is sprite and isinstance(label, MonsterNameSprite) and label.rect.colliderect(body):
			overlaps.append(sprite.monster.name)
check('name tags never cover their monster', [], overlaps)
boxes = [s.rect for s in fight.battle_sprites if isinstance(s, (MonsterNameSprite, MonsterStatsSprite))]
check('no two name tags or stats boxes overlap', 0, sum(a.colliderect(b) for i, a in enumerate(boxes) for b in boxes[i + 1:]))

# ---------- Iteration 36: same-speed monsters, matching team sizes and the Monster Box ----------
pouch_screen = training.TrainingScreen(game.ui, 'Pouch')   # both sides are Pouch, so they always have the same speed
duel = pouch_screen.battle
mine = duel.player_sprites.sprites()[0]
for _ in range(600):
	duel.update(1 / 60)
	if duel.current_monster is mine:
		break
for _ in range(30):
	duel.update(1 / 60)
check('with the same speed, your turn is not taken away by the other monster', (mine, 'general'), (duel.current_monster, duel.selection_mode))
def field_size(theirs):
	fight = Battle({i: Monster('Pluma', 30) for i in range(6)}, {i: Monster('Atrox', 30) for i in range(theirs)}, game.monster_frames, game.bg_frames['forest'],
	               game.fonts, lambda *a, **k: None, None, {}, {}, False, None)
	return len(fight.player_sprites), len(fight.opponent_sprites)
check('one opponent is 1 v 1, two is 2 v 2, four is 3 v 3', [(1, 1), (2, 2), (3, 3)], [field_size(1), field_size(2), field_size(4)])
from game_screens import PartyScreen
party_screen = PartyScreen(game.ui)
game.ui.screens = [party_screen]
party_screen.handle_key(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_b))
check('B on the party screen opens the Monster Box', 'StorageScreen', type(game.ui.screens[-1]).__name__)
game.ui.screens = []

# ---------- the menu icons are all different ----------
from game_screens import MainMenu
check('every row in the menu has its own icon', len(MainMenu.ROW_ICONS), len(set(MainMenu.ROW_ICONS)))
check('the menu has an icon for every row', len(MainMenu(game.ui).get_items()), len(MainMenu.ROW_ICONS))

# ---------- results ----------
passed = sum(1 for r in results if r[3])
for name, expected, actual, ok in results:
	print(f"{'PASS' if ok else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{passed}/{len(results)} tests passed')
