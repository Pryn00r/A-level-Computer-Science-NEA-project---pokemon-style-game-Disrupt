# test_sound_and_atmosphere.py
# Automated tests for Iteration 20: the audio manager (no more overlapping sounds), the new icons,
# key-cap hints, zone weather and banners (Iteration 31: only snow is left, no footsteps or background sounds).
# Run with:  python test_sound_and_atmosphere.py   (no window is opened)

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from settings import MUSIC_TRACKS
from audio_manager import AudioManager, ManagedSound, category_of
from main import Game
import item_art
import menus

results = []
def check(name, expected, actual):
	results.append((name, expected, actual, expected == actual))

# ---------- audio manager ----------
check('menu clicks share one channel', 'ui', category_of('menu_move'))
check('victory is a jingle', 'jingle', category_of('victory'))
check('footsteps have their own channel', 'step', category_of('step_sand'))
check('ambience has its own channel', 'ambient', category_of('amb_ice'))
check('attack sounds use the battle channels', 'battle', category_of('hit_fire'))

game = Game()
check('music tracks are not wrapped (they keep playing on free channels)', True, all(not isinstance(game.audio[name], ManagedSound) for name in MUSIC_TRACKS if name in game.audio))
check('sound effects are wrapped by the audio manager', True, isinstance(game.audio['menu_select'], ManagedSound))
manager = game.audio_manager
if manager.channels:
	first = game.audio['menu_select'].play()
	second = game.audio['menu_select'].play()
	check('the same sound twice in a row is ignored (no double click)', (True, None), (first is not None, second))
	check('two different menu sounds use the same channel (the new one replaces the old)', manager.channel_for(game.audio['menu_move']), manager.channel_for(game.audio['menu_back']))
	channels = {id(manager.channel_for(game.audio['hit_fire'])) for _ in range(4)}
	check('battle sounds take turns on 4 channels, so a hit never cuts itself off', 4, len(channels))
else:
	check('audio device present (skipped without one)', True, True)

# ---------- new sounds exist ----------
for name in ('step_grass', 'step_sand', 'step_snow', 'step_wood', 'amb_grass', 'amb_sand', 'amb_ice', 'hit_psychic', 'badge', 'quest', 'door', 'miss'):
	check(f'sound "{name}" was generated', True, name in game.audio)

# ---------- icons ----------
for name in ('capture_orb', 'great_orb', 'prime_orb', 'power_band', 'vital_charm', 'focus_ring', 'wise_feather', 'illuminator'):
	check(f'{name} has a 32 x 32 picture', (32, 32), item_art.item(name).get_size())
check('flags for every language', True, all(item_art.flag(code).get_width() == 30 for code in ('en', 'it', 'es')))
check('medals for the top three', 3, len({item_art.medal(place).get_at((16, 20))[:3] for place in (1, 2, 3)}))
font = pygame.font.Font(None, 14)
check('a type chip is wider for a longer name', True, item_art.type_chip('psychic', font, 'Psychic').get_width() > item_art.type_chip('bug', font, 'Bug').get_width())
strip = pygame.Surface((800, 40), pygame.SRCALPHA)
rect = menus.draw_key_hints(strip, font, 'Up/Down: Select    Esc: Back', (255, 255, 255), center = (400, 20))
check('key hints are drawn as one strip of caps and words', True, 80 < rect.width < 400)

# ---------- atmosphere ----------
game.change_map('world', 'water')
check('outside the water gym is the snow zone', 'ice', game.current_biome())
game.playing = True
for _ in range(60):
	game.atmosphere.update(1 / 30, active = True)
check('snow falls in the snow zone', True, len(game.atmosphere.weather) > 20 and game.atmosphere.weather[0].kind == 'snow')
check('the banner names the area', menus.t('zone_ice'), game.atmosphere.banner[0] if game.atmosphere.banner else None)
check('no background sound (Iteration 31)', None, game.atmosphere.ambience)
game.change_map('world', 'fire')
for _ in range(60):
	game.atmosphere.update(1 / 30, active = True)
check('no weather in the desert any more - only snow is left (Iteration 31)', [], [p.kind for p in game.atmosphere.weather if p.kind != 'snow'])
check('and no desert background sound', None, game.atmosphere.ambience)
check('no footprints or dust', [], [p.kind for p in game.atmosphere.effects if p.kind != 'firefly'])
game.change_map('hospital', 'world')
for _ in range(60):
	game.atmosphere.update(1 / 30, active = True)
check('no weather indoors', 0, len(game.atmosphere.weather))
check('no outdoor ambience indoors', None, game.atmosphere.ambience)

for name, expected, actual, passed in results:
	print(f"{'PASS' if passed else 'FAIL'} | {name} | expected {expected} | actual {actual}")
print(f'{sum(r[3] for r in results)}/{len(results)} tests passed')
