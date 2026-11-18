# audio_manager.py
# Iteration 20: stops sound effects piling on top of each other.
# Every sound effect is wrapped in a ManagedSound that plays on a channel for its kind:
#   ui       - menu clicks (a new click replaces the last one)
#   jingle   - victory, level up, heal, badge... (only one at a time, the next one waits its turn)
#   notice   - the trainer '!' sound
#   battle   - attack and hit sounds (4 channels taken in turn, so a hit never cuts off itself)
#   ambient  - birds, wind, waves under the music (looped)
#   step     - footsteps
# The same sound started again within DEBOUNCE seconds is ignored (stops double clicks), and the
# music is turned down while a jingle plays (ducking), then faded back.
# Music tracks (MUSIC_TRACKS) are not wrapped: they keep using pygame's free channels.

from settings import *

DEBOUNCE = 0.08          # seconds
DUCK_LEVEL = 0.35        # music volume multiplier while a jingle plays

UI_SOUNDS = ('menu_move', 'menu_select', 'menu_back')
JINGLES = ('victory', 'level_up', 'heal', 'coin', 'catch', 'catch_fail', 'save', 'badge', 'quest', 'evolution', 'unlock', 'rival')
CATEGORY_CHANNELS = {'ui': [0], 'jingle': [1], 'notice': [2], 'ambient': [3], 'step': [4], 'battle': [5, 6, 7, 8]}
RESERVED = 9

def category_of(name):
	if name in UI_SOUNDS:
		return 'ui'
	if name in JINGLES:
		return 'jingle'
	if name == 'notice':
		return 'notice'
	if name.startswith('amb_'):
		return 'ambient'
	if name.startswith('step_'):
		return 'step'
	return 'battle'


class ManagedSound:
	def __init__(self, manager, name, sound):
		self.manager, self.name, self.sound = manager, name, sound
		self.category = category_of(name)

	# Same call style as pygame.mixer.Sound.play, so the rest of the game does not change.
	def play(self, loops = 0, maxtime = 0, fade_ms = 0):
		return self.manager.play(self, loops, fade_ms)

	def stop(self):
		self.manager.stop(self)

	def fadeout(self, ms):
		self.manager.stop(self, ms)

	def set_volume(self, volume):
		self.sound.set_volume(volume)

	def get_volume(self):
		return self.sound.get_volume()

	def get_length(self):
		return self.sound.get_length()


class AudioManager:
	def __init__(self):
		self.ready = bool(pygame.mixer.get_init())
		self.channels = {}
		if self.ready:
			pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), 24))
			pygame.mixer.set_reserved(RESERVED)
			self.channels = {kind: [pygame.mixer.Channel(i) for i in ids] for kind, ids in CATEGORY_CHANNELS.items()}
		self.next_battle = 0
		self.last_started = {}    # sound name -> time it last started (for the debounce)
		self.ducked = False

	# Wraps every sound effect in the audio dictionary (music tracks are left alone).
	def wrap(self, audio):
		return {name: (sound if name in MUSIC_TRACKS else ManagedSound(self, name, sound)) for name, sound in audio.items()}

	def channel_for(self, managed):
		options = self.channels.get(managed.category)
		if not options:
			return None
		if managed.category == 'battle':
			channel = options[self.next_battle % len(options)]
			self.next_battle += 1
			return channel
		return options[0]

	def play(self, managed, loops = 0, fade_ms = 0):
		now = pygame.time.get_ticks() / 1000
		if now - self.last_started.get(managed.name, -1) < DEBOUNCE:
			return None
		self.last_started[managed.name] = now
		channel = self.channel_for(managed)
		if channel is None:
			return managed.sound.play(loops, fade_ms = fade_ms)
		if managed.category == 'jingle' and channel.get_busy():
			# only one jingle at a time - the new one waits until the current one ends
			channel.queue(managed.sound)
			return channel
		channel.play(managed.sound, loops, fade_ms = fade_ms)
		return channel

	def stop(self, managed, fade_ms = 0):
		for channel in self.channels.get(managed.category, []):
			if channel.get_sound() is managed.sound:
				channel.fadeout(fade_ms) if fade_ms else channel.stop()
		if not self.channels:
			managed.sound.stop()

	# Called every frame: turns the music down while a jingle plays. Parameters: the audio dict,
	# the name of the music playing now and its normal volume (0-1).
	def update(self, audio, music, volume):
		if not self.channels or music not in audio:
			return
		busy = self.channels['jingle'][0].get_busy()
		if busy != self.ducked:
			self.ducked = busy
			audio[music].set_volume(volume * (DUCK_LEVEL if busy else 1))
