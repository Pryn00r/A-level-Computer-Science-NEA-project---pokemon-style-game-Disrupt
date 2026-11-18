# preferences.py
# Stores the player's settings (brightness, night mode, language, sound, music) in preferences.json
# and applies them to the screen and audio.

from os.path import join

from localisation import LANGUAGES, set_language
from save_system import SAVE_ROOT, read_protected, write_protected
from settings import *

# values used the first time the game is run, or if the file is missing
DEFAULT_PREFERENCES = {
	'brightness': 100,
	'night_mode': False,
	'language': 'en',
	'sound_volume': 80,   # Iteration 18: volume sliders (0-100) instead of on/off
	'music_volume': 70,
	'muted': False,       # Iteration 18: the speaker button on the menu mutes everything
	'intro': 'full',      # Iteration 18: 'full', 'short' (no loading screen) or 'off'
	'minimap': True,   # Iteration 13 - corner minimap on or off
	'control_hints': True,   # Iteration 14 - key reminders along the bottom of the screen
	# Iteration 24/25 (see options.py)
	'colour_blind': False,
	'large_text': False,
	'difficulty': 'normal',
	'autosave': 180,
	'encounter_rate': 'normal',
	'keys': None,
	'speedrun_timer': False,   # Iteration 25: shows the play time with tenths of a second
}

class Preferences:
	# Loads the saved settings over the defaults, then validates them (range check on brightness,
	# lookup check on language) so a hand-edited file cannot break the game.
	def __init__(self, root = SAVE_ROOT):
		self.path = join(root, 'preferences.json')
		self.values = dict(DEFAULT_PREFERENCES)
		self.values.update(read_protected(self.path) or {})

		# a hand edited file should not be able to break the game
		self.values['brightness'] = max(BRIGHTNESS_MIN, min(int(self.values['brightness']), BRIGHTNESS_MAX))
		if self.values['language'] not in LANGUAGES:
			self.values['language'] = 'en'
		# Iteration 18: older files had sound/music on/off - an 'off' becomes volume 0
		for old, new in (('sound', 'sound_volume'), ('music', 'music_volume')):
			if self.values.pop(old, True) is False:
				self.values[new] = 0
		for key in ('sound_volume', 'music_volume'):
			self.values[key] = max(0, min(100, int(self.values[key])))   # range check
		if self.values['intro'] not in INTRO_MODES:
			self.values['intro'] = 'full'
		set_language(self.values['language'])
		# Iteration 24/25: lookup checks on the new settings
		import options
		if self.values['difficulty'] not in options.DIFFICULTIES:
			self.values['difficulty'] = 'normal'
		if self.values['autosave'] not in options.AUTOSAVE_CHOICES:
			self.values['autosave'] = 180
		if self.values['encounter_rate'] not in options.ENCOUNTER_RATES:
			self.values['encounter_rate'] = 'normal'
		self.values['colour_blind'] = bool(self.values['colour_blind'])
		self.values['large_text'] = bool(self.values['large_text'])
		self.values['keys'] = options.valid_keys(self.values['keys'])
		options.apply_keys(self.values['keys'])
		options.apply_colour_blind(self.values['colour_blind'])
		options.apply_difficulty(self.values['difficulty'])

	# Allows preferences['night_mode'] style access.
	def __getitem__(self, key):
		return self.values[key]

	# Changes one setting and saves the file straight away.
	def set(self, key, value):
		self.values[key] = value
		if key == 'language':
			set_language(value)
		write_protected(self.path, self.values)

	# Switches an on/off setting (night mode, sound, music).
	def toggle(self, key):
		self.set(key, not self.values[key])

	# Moves brightness up or down by BRIGHTNESS_STEP, clamped between BRIGHTNESS_MIN and BRIGHTNESS_MAX.
	def change_brightness(self, direction):
		value = self.values['brightness'] + direction * BRIGHTNESS_STEP
		self.set('brightness', max(BRIGHTNESS_MIN, min(value, BRIGHTNESS_MAX)))

	# Iteration 18: changes a volume by 10 (kept between 0 and 100).
	def change_volume(self, key, direction):
		self.set(key, max(0, min(100, self.values[key] + direction * 10)))

	# Iteration 18: moves to the next/previous intro mode (full -> short -> off).
	def cycle_intro(self, direction):
		index = INTRO_MODES.index(self.values['intro'])
		self.set('intro', INTRO_MODES[(index + direction) % len(INTRO_MODES)])

	# Iteration 25: steps through a fixed list of choices (difficulty, autosave, encounter rate).
	def cycle(self, key, choices, direction):
		index = choices.index(self.values[key]) if self.values[key] in choices else 0
		self.set(key, choices[(index + direction) % len(choices)])
		import options
		options.apply_difficulty(self.values['difficulty'])

	# Moves to the next/previous language, wrapping round with MOD.
	def cycle_language(self, direction):
		codes = list(LANGUAGES)
		index = codes.index(self.values['language'])
		self.set('language', codes[(index + direction) % len(codes)])

	# Sets the volume of every sound to 1 or 0 depending on the music and sound settings.
	def apply_audio(self, audio):
		# tracks keep playing silently so that music resumes as soon as it is turned on
		for name, sound in audio.items():
			volume = self.values['music_volume'] if name in MUSIC_TRACKS else self.values['sound_volume']
			sound.set_volume(0 if self.values['muted'] else volume / 100)

	# Multiplies the screen by a cool blue tint when night mode is on.
	def apply_night_mode(self, surface):
		if self.values['night_mode']:
			surface.fill(NIGHT_MODE_TINT, special_flags = pygame.BLEND_RGB_MULT)

	# Darkens the screen below 100% (multiply) or lightens it above 100% (add).
	def apply_brightness(self, surface):
		brightness = self.values['brightness']
		if brightness < 100:
			level = int(255 * brightness / 100)
			surface.fill((level, level, level), special_flags = pygame.BLEND_RGB_MULT)
		elif brightness > 100:
			# Iteration 18: a gentler lighten (was 0.5) so colours do not wash out
			level = int(255 * (brightness - 100) / 100 * 0.25)
			surface.fill((level, level, level), special_flags = pygame.BLEND_RGB_ADD)
