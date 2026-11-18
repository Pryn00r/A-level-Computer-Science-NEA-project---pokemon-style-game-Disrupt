# make_music.py
# Iteration 19: makes the zone and battle music for Disrupt from code (no samples), so every track is
# original. The world tracks use a bounce-style beat (syncopated kick, claps on 2 and 4, shout
# "hey" stabs) mixed with West African style percussion (djembe, agogo bell, shaker) and a melody
# on marimba / kalimba / plucked strings. The battle tracks are faster, in minor keys, with a
# driving bass, string ostinato, brass stabs and drum fills to build tension.
# Every track is a seamless loop. Needs numpy, scipy and ffmpeg.
# Run with:  python tools/make_music.py   (writes the .ogg files into the audio folder)

import os
import subprocess
import wave
from os.path import abspath, dirname, join

import numpy as np
from scipy.signal import butter, sosfilt

SR = 32000
AUDIO = join(dirname(dirname(abspath(__file__))), 'audio')
NOTES = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}


def midi(name):
	note, octave = name[:-1], int(name[-1])
	return NOTES[note] + 12 * (octave + 1)

def hz(note):
	if isinstance(note, str):
		note = midi(note)
	return 440 * 2 ** ((note - 69) / 12)

def times(length):
	return np.arange(int(length * SR)) / SR

def env(length, attack = 0.005, decay = 0.3, sustain = 0.0, release = 0.05):
	t = times(length)
	e = np.minimum(1, t / max(attack, 1e-4))
	e *= sustain + (1 - sustain) * np.exp(-t / max(decay, 1e-4))
	tail = np.clip((length - t) / max(release, 1e-4), 0, 1)
	return e * tail

def band(signal, low, high, order = 2):
	return sosfilt(butter(order, [low, high], 'bandpass', fs = SR, output = 'sos'), signal)

def lowpass(signal, cutoff, order = 2):
	return sosfilt(butter(order, min(cutoff, SR / 2 - 100), 'lowpass', fs = SR, output = 'sos'), signal)

def highpass(signal, cutoff, order = 2):
	return sosfilt(butter(order, cutoff, 'highpass', fs = SR, output = 'sos'), signal)

rng = np.random.default_rng(19)
def noise(length):
	return rng.uniform(-1, 1, int(length * SR))

def saw(freq, t):
	return 2 * ((freq * t) % 1) - 1

def square(freq, t, duty = 0.5):
	return np.where((freq * t) % 1 < duty, 1.0, -1.0)


# ---------- instruments (each returns a mono numpy array) ----------
def kick(punch = 1.0):
	t = times(0.45)
	freq = 45 + 110 * np.exp(-t * 28)
	body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 7)
	click = noise(0.45) * np.exp(-t * 300) * 0.3
	return np.tanh((body + click) * 1.6 * punch)

def clap():
	length = 0.3
	sound = np.zeros(int(length * SR))
	for offset in (0, 0.011, 0.022):
		n = int(offset * SR)
		count = len(sound) - n
		burst = rng.uniform(-1, 1, count) * np.exp(-np.arange(count) / SR * (90 if offset < 0.02 else 18))
		sound[n:] += burst
	return band(sound, 900, 3500) * 1.4

def snare():
	t = times(0.25)
	tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25)
	return (band(noise(0.25), 1500, 8000) * np.exp(-t * 20) + tone * 0.6) * 0.9

def hat(open_hat = False):
	length = 0.25 if open_hat else 0.05
	return highpass(noise(length), 7000) * np.exp(-times(length) * (12 if open_hat else 70)) * 0.5

def shaker():
	t = times(0.09)
	return band(noise(0.09), 5000, 11000) * np.sin(np.pi * t / 0.09) ** 2 * 0.35

def djembe(kind):
	t = times(0.4)
	if kind == 'B':   # bass: deep and round
		freq = 70 + 40 * np.exp(-t * 30)
		return np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 9) * 0.9
	if kind == 't':   # tone: open and ringing
		return (np.sin(2 * np.pi * 260 * t) + 0.4 * np.sin(2 * np.pi * 410 * t)) * np.exp(-t * 16) * 0.45 + band(noise(0.4), 300, 1500) * np.exp(-t * 60) * 0.3
	# slap: sharp and bright
	return band(noise(0.4), 1200, 6000) * np.exp(-t * 45) * 0.8 + np.sin(2 * np.pi * 420 * t) * np.exp(-t * 40) * 0.3

def talking_drum(start_note, bend):
	t = times(0.35)
	freq = hz(start_note) * (1 + bend * (1 - np.exp(-t * 12)))
	return np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 9) * 0.6

def bell(high = True):
	t = times(0.3)
	f = 820 if high else 610
	return (np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * f * 2.76 * t) + 0.3 * np.sin(2 * np.pi * f * 5.4 * t)) * np.exp(-t * 14) * 0.25

def tom(note):
	t = times(0.5)
	freq = hz(note) * (1 + 0.5 * np.exp(-t * 20))
	return np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 7) * 0.8 + band(noise(0.5), 200, 2000) * np.exp(-t * 40) * 0.2

def crash():
	t = times(1.6)
	return highpass(noise(1.6), 4000) * np.exp(-t * 2.5) * 0.35

def bass808(note, length, drive = 1.5):
	t = times(length + 0.05)
	f = hz(note)
	tone = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 2 * t)
	return np.tanh(tone * drive) * env(length + 0.05, 0.004, 0.6, 0.5, 0.04) * 0.8

def synth_bass(note, length, cutoff = 900):
	t = times(length)
	f = hz(note)
	tone = saw(f, t) + saw(f * 1.006, t)
	return lowpass(tone, cutoff) * env(length, 0.003, 0.12, 0.6, 0.02) * 0.45

def marimba(note, length = 0.5):
	t = times(length)
	f = hz(note)
	return (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 30)) * np.exp(-t * 7) * 0.5

def kalimba(note, length = 0.8):
	t = times(length)
	f = hz(note)
	return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 5.1 * t) * np.exp(-t * 20)) * np.exp(-t * 4) * 0.45

def glock(note, length = 1.0):
	t = times(length)
	f = hz(note)
	return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t * 6)) * np.exp(-t * 3.5) * 0.3

def pluck(note, length = 0.4, bright = 3000):
	t = times(length)
	f = hz(note)
	tone = saw(f, t) * np.exp(-t * 9)
	return lowpass(tone, bright) * 0.4

def brass(notes, length, cutoff = 2400):
	t = times(length)
	sound = sum(saw(hz(n), t) + saw(hz(n) * 1.004, t) for n in notes) / len(notes)
	sweep = lowpass(sound, cutoff)
	return sweep * env(length, 0.01, 0.15, 0.55, 0.05) * 0.4

def strings(note, length):
	t = times(length)
	f = hz(note)
	tone = saw(f, t) + saw(f * 1.005, t) + saw(f * 0.995, t)
	return lowpass(tone, 3200) * env(length, 0.005, 0.08, 0.5, 0.03) * 0.18

def pad(notes, length, cutoff = 1500):
	t = times(length)
	sound = sum(saw(hz(n), t) + saw(hz(n) * 1.007, t) for n in notes) / len(notes)
	return lowpass(sound, cutoff) * env(length, 0.4, 2.0, 0.8, 0.4) * 0.22

def choir(notes, length):
	t = times(length)
	source = sum(saw(hz(n) * (1 + 0.004 * np.sin(2 * np.pi * 5 * t)), t) for n in notes) / len(notes)
	vowel = band(source, 600, 1000) * 1.2 + band(source, 1100, 1400) * 0.6 + band(source, 2400, 2800) * 0.25
	return vowel * env(length, 0.3, 2.0, 0.8, 0.4) * 0.5

def lead(note, length, vibrato = True):
	t = times(length)
	f = hz(note) * (1 + (0.006 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t * 3, 0, 1) if vibrato else 0))
	phase = np.cumsum(f) / SR
	tone = np.where(phase % 1 < 0.3, 1.0, -1.0) * 0.6 + (2 * (phase % 1) - 1) * 0.4
	return lowpass(tone, 2600) * env(length, 0.01, 0.3, 0.7, 0.05) * 0.22

def hey(pitch = 1.0):
	# a shouted "hey!" made from a buzzy tone through vowel filters, sliding down
	t = times(0.28)
	freq = 230 * pitch * (1 - 0.25 * t / 0.28)
	source = saw(1, np.cumsum(freq) / SR) + 0.3 * noise(0.28)
	vowel = band(source, 450, 750) + 0.8 * band(source, 1700, 2200) + 0.3 * band(source, 2600, 3100)
	return vowel * env(0.28, 0.01, 0.12, 0.3, 0.06) * 1.3

def riser(length):
	t = times(length)
	sweep = np.zeros_like(t)
	source = noise(length)
	for i, part in enumerate(np.array_split(np.arange(len(t)), 16)):
		cutoff = 400 + 7000 * (i / 15) ** 2
		sweep[part] = lowpass(source, cutoff)[part]
	return sweep * (t / length) ** 2 * 0.4


# ---------- arranging ----------
class Track:
	def __init__(self, bpm, bars):
		self.bpm, self.bars = bpm, bars
		self.step = 60 / bpm / 4                  # one 16th note
		self.length = self.step * 16 * bars
		self.buffer = np.zeros((int(self.length * SR), 2))

	# Adds a sound at a time in steps (16ths). Sounds that run past the end wrap round to the start,
	# so the loop is seamless.
	def add(self, sound, step, gain = 1.0, pan = 0.0, swing = 0.0):
		if step % 2 == 1:
			step += swing
		start = int(step * self.step * SR) % len(self.buffer)
		left, right = gain * np.sqrt(0.5 * (1 - pan)), gain * np.sqrt(0.5 * (1 + pan))
		end = start + len(sound)
		if end <= len(self.buffer):
			self.buffer[start:end, 0] += sound * left
			self.buffer[start:end, 1] += sound * right
		else:
			first = len(self.buffer) - start
			self.buffer[start:, 0] += sound[:first] * left
			self.buffer[start:, 1] += sound[:first] * right
			rest = sound[first:][:len(self.buffer)]
			self.buffer[:len(rest), 0] += rest * left
			self.buffer[:len(rest), 1] += rest * right

	# Plays a 16-step pattern ('x' = hit, 'o' = softer hit) in every bar listed.
	def pattern(self, sound_for, pattern, bars, gain = 1.0, pan = 0.0, swing = 0.0):
		for bar in bars:
			for i, cell in enumerate(pattern):
				if cell != '.':
					sound = sound_for(cell) if callable(sound_for) else sound_for
					self.add(sound, bar * 16 + i, gain * (0.6 if cell == 'o' else 1.0), pan, swing)

	def save(self, name):
		mix = self.buffer
		# gentle glue compression (soft clip) and level matching so every track is about as loud
		rms = np.sqrt(np.mean(mix ** 2)) + 1e-9
		mix = np.tanh(mix * (0.12 / rms)) * 0.9
		mix /= max(1e-9, np.max(np.abs(mix))) / 0.89
		wav_path = join(AUDIO, f'{name}.wav')
		with wave.open(wav_path, 'wb') as file:
			file.setnchannels(2)
			file.setsampwidth(2)
			file.setframerate(SR)
			file.writeframes((mix * 32767).astype('<i2').tobytes())
		subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav_path, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', str(SR), '-c:a', 'libvorbis', '-q:a', '4', join(AUDIO, f'{name}.ogg')], check = True)
		os.remove(wav_path)
		print(f'{name}.ogg  {self.length:.1f} s')


def chord_tones(root, quality):
	r = midi(root)
	steps = {'maj': (0, 4, 7), 'min': (0, 3, 7), 'sus': (0, 5, 7), 'dim': (0, 3, 6), 'maj7': (0, 4, 7, 11), 'min7': (0, 3, 7, 10), 'dom': (0, 4, 7, 10)}[quality]
	return [r + s for s in steps]


# ---------- world tracks: bounce beat + West African percussion ----------
BOUNCE_KICK = ['x..x...x..x.x...', 'x..x...x..x..x.x']
BOUNCE_CLAP = ['....x.......x...', '....x.......x.xx']
SON_CLAVE = 'x..x..x...x.x...'
AGOGO = 'x.xx.x.xx.x.xx.x'
DJEMBE = ['B..t.ss.B.t.t.ss', 'B.st.st.B.ttsss.']

def world_track(name, bpm, key_root, progression, riff, riff_voice, extra, bass_rhythm = 'x..x...x..x.x...', swing = 0.18):
	bars = 32
	track = Track(bpm, bars)
	everything = range(bars)
	sections = {'A': range(0, 8), 'B': range(8, 16), 'A2': range(16, 24), 'C': range(24, 32)}
	beat_bars = [b for b in everything if b not in range(24, 28)]   # bars 24-27: drums drop out, percussion only
	# drums
	for bar in beat_bars:
		track.pattern(lambda c: kick(), BOUNCE_KICK[1 if bar % 4 == 3 else 0], [bar], 1.0)
		track.pattern(lambda c: clap(), BOUNCE_CLAP[1 if bar % 8 == 7 else 0], [bar], 0.75, 0.05)
		track.pattern(lambda c: hat(), 'x.xox.xox.xox.xo', [bar], 0.22, 0.3, swing)
	track.pattern(lambda c: shaker(), 'xoxoxoxoxoxoxoxo', everything, 0.3, -0.35, swing)
	track.pattern(lambda c: djembe(c), DJEMBE[0], [b for b in everything if b % 2 == 0], 0.6, -0.25, swing)
	track.pattern(lambda c: djembe(c), DJEMBE[1], [b for b in everything if b % 2 == 1], 0.6, -0.25, swing)
	track.pattern(bell(True), AGOGO, list(sections['B']) + list(sections['A2']) + list(sections['C']), 0.7, 0.45, swing)
	track.pattern(bell(False), SON_CLAVE, everything, 0.5, 0.5)
	for bar in (7, 15, 23, 31):   # fills into the next section
		track.pattern(lambda c: djembe('s'), '........ssss.sss', [bar], 0.9, -0.1)
	track.add(crash(), 0, 0.4)
	track.add(crash(), 16 * 16, 0.7)
	# bass and harmony
	for bar in everything:
		root, quality = progression[bar % len(progression)]
		tones = chord_tones(root + '2', quality)
		if bar not in range(24, 26):
			for i, cell in enumerate(bass_rhythm):
				if cell == 'x':
					note = tones[0] + (12 if i in (10, 14) else 0)
					track.add(bass808(note, track.step * 2.5), bar * 16 + i, 0.9)
		if bar in sections['B'] or bar in sections['C']:
			for i in (2, 6, 10, 14):   # off-beat stabs
				track.add(brass([n + 12 for n in tones], track.step * 1.2), bar * 16 + i, 0.35, 0.2)
		if bar % 2 == 0:
			track.add(pad([n + 12 for n in tones], track.step * 32), bar * 16, 0.5)
	# the riff (melody), with a "hey!" call at the end of every 4 bars
	for bar in everything:
		if bar in range(24, 26):
			continue
		phrase = riff[(bar // 2) % len(riff)] if bar % 2 == 0 else riff[(bar // 2) % len(riff)][::-1]
		for i, note in enumerate(phrase):
			if note:
				track.add(riff_voice(midi(key_root) + note), bar * 16 + i * 2, 1.1, -0.2 if i % 2 else 0.2, swing)
		if bar % 4 == 3:
			track.add(hey(1.0), bar * 16 + 12, 0.55, -0.1)
			track.add(hey(1.12), bar * 16 + 14, 0.55, 0.1)
	extra(track)
	track.save(name)

def no_extra(track):
	pass


# ---------- battle tracks ----------
def battle_track(name, bpm, root, progression, motif, intensity = 1.0, boss = False):
	bars = 24
	track = Track(bpm, bars)
	everything = range(bars)
	r = midi(root + '1')
	for bar in everything:
		build = bar in range(0, 4)
		# drums: four on the floor with a syncopated kick, snare on 2 and 4, rolls before each section
		track.pattern(lambda c: kick(1.1), 'x...x..xx...x...' if not build else 'x.......x.......', [bar], 1.0)
		if not build:
			track.pattern(lambda c: snare(), '....x.......x...' if bar % 4 != 3 else '....x.......xxxx', [bar], 0.8, 0.05)
			track.pattern(lambda c: hat(c == 'o'), 'x.x.x.x.x.x.x.xo', [bar], 0.4, 0.3)
		track.pattern(lambda c: djembe(c), 'B.ts.tB.s.tsB.ts', [bar], 0.6, -0.3)
		track.pattern(bell(True), 'x..x..x...x..x..', [bar], 0.5, 0.4)
		if bar % 8 == 7:
			for i, note in enumerate((r + 31, r + 28, r + 24, r + 19)):
				track.add(tom(note), bar * 16 + 8 + i * 2, 0.8, -0.4 + i * 0.25)
		if bar % 8 == 0:
			track.add(crash(), bar * 16, 0.8)
		# harmony
		chord_root, quality = progression[bar % len(progression)]
		tones = chord_tones(chord_root + '2', quality)
		for i in range(0, 16, 2 if build else 1):   # driving bass
			octave = 12 if i % 4 == 2 else 0
			track.add(synth_bass(tones[0] + octave, track.step * 0.9, 700 + 500 * intensity), bar * 16 + i, 0.7)
		for i in range(16):   # string ostinato (the tension)
			note = tones[[0, 1, 2, 1][i % 4]] + 12
			track.add(strings(note + 12, track.step * 0.9), bar * 16 + i, 0.6, 0.25 if i % 2 else -0.25)
		if not build:
			for i in (0, 3, 6, 10):
				track.add(brass([n + 12 for n in tones], track.step * (1.5 if i != 10 else 4)), bar * 16 + i, 0.5 * intensity, 0.15)
		if boss and bar % 2 == 0:
			track.add(choir([n + 12 for n in tones], track.step * 32), bar * 16, 0.7)
		if bar == 3:
			track.add(riser(track.step * 16), bar * 16, 0.8)
	# the motif (lead melody) from bar 4
	for bar in range(4, bars):
		phrase = motif[(bar - 4) % len(motif)]
		for start, note, length in phrase:
			track.add(lead(midi(root + '4') + note, track.step * length), bar * 16 + start, 0.9, 0.05)
	track.save(name)


if __name__ == '__main__':
	os.makedirs(AUDIO, exist_ok = True)
	# GRASS: bright, G major pentatonic marimba riff
	world_track('zone_grass', 102, 'G4',
		[('G', 'maj'), ('E', 'min'), ('C', 'maj'), ('D', 'maj')],
		[[0, 4, 7, 9, 7, 4, 2, 0], [2, 4, 7, 12, 9, 7, 4, 2], [0, 0, 4, 7, 9, 12, 9, 7], [4, 2, 0, 2, 4, 7, 4, 0]],
		lambda n: marimba(n), no_extra)

	# SAND: desert scale (D phrygian dominant), plucked strings and a talking drum
	def sand_extra(track):
		for bar in range(track.bars):
			if bar % 2 == 1:
				for i, (note, bend) in enumerate((('D3', 0.4), ('A2', 0.6), ('D3', -0.2))):
					track.add(talking_drum(note, bend), bar * 16 + 9 + i * 2, 0.6, 0.35)
	world_track('zone_sand', 98, 'D4',
		[('D', 'maj'), ('Eb', 'maj'), ('D', 'maj'), ('C', 'min')],
		[[0, 1, 4, 5, 7, 5, 4, 1], [0, 4, 7, 8, 7, 4, 1, 0], [7, 8, 7, 5, 4, 5, 4, 1], [0, 1, 0, -2, 0, 4, 1, 0]],
		lambda n: pluck(n, 0.45, 2600), sand_extra, bass_rhythm = 'x..x..x...x.x...')

	# ICE: cool E minor kalimba, with glockenspiel sparkles
	def ice_extra(track):
		for bar in range(8, track.bars):
			for i, note in enumerate((76, 79, 83, 88)):
				track.add(glock(note), bar * 16 + 1 + i * 4, 0.35, 0.5 if i % 2 else -0.5)
	world_track('zone_ice', 100, 'E4',
		[('E', 'min'), ('C', 'maj'), ('A', 'min'), ('B', 'min')],
		[[0, 3, 7, 10, 7, 3, 2, 0], [7, 10, 12, 15, 12, 10, 7, 3], [0, 0, 3, 5, 7, 5, 3, 2], [3, 2, 0, -2, 0, 3, 7, 0]],
		lambda n: kalimba(n), ice_extra, swing = 0.12)

	# INDOORS (houses and hospitals): calmer, same family
	world_track('zone_town', 92, 'C4',
		[('C', 'maj7'), ('A', 'min7'), ('F', 'maj7'), ('G', 'dom')],
		[[0, 4, 7, 11, 7, 4, 2, 0], [4, 7, 9, 12, 9, 7, 4, 2], [0, 2, 4, 7, 4, 2, 0, -1], [2, 4, 5, 7, 9, 7, 5, 4]],
		lambda n: kalimba(n, 0.9), no_extra, swing = 0.1)

	# BATTLES
	A = [[(0, 0, 3), (3, 3, 3), (6, 7, 2), (8, 5, 4), (12, 3, 4)], [(0, 7, 3), (3, 8, 3), (6, 7, 2), (8, 3, 6), (14, 2, 2)],
	     [(0, 0, 3), (3, 3, 3), (6, 7, 2), (8, 10, 4), (12, 8, 4)], [(0, 7, 6), (6, 5, 2), (8, 3, 4), (12, 2, 4)]]
	battle_track('battle_wild', 150, 'A', [('A', 'min'), ('F', 'maj'), ('G', 'maj'), ('E', 'maj')], A, 0.9)
	T = [[(0, 0, 2), (2, 0, 2), (4, 3, 2), (6, 5, 2), (8, 7, 6), (14, 5, 2)], [(0, 3, 4), (4, 2, 2), (6, 0, 2), (8, -2, 8)],
	     [(0, 0, 2), (2, 0, 2), (4, 3, 2), (6, 5, 2), (8, 10, 4), (12, 8, 4)], [(0, 7, 4), (4, 5, 4), (8, 7, 8)]]
	battle_track('battle_trainer', 156, 'D', [('D', 'min'), ('Bb', 'maj'), ('C', 'maj'), ('A', 'maj')], T, 1.1)
	G = [[(0, 0, 4), (4, 0, 2), (6, 3, 2), (8, 7, 4), (12, 6, 4)], [(0, 7, 4), (4, 3, 4), (8, 5, 8)],
	     [(0, 0, 4), (4, 0, 2), (6, 3, 2), (8, 8, 4), (12, 7, 4)], [(0, 3, 4), (4, 2, 4), (8, -1, 8)]]
	battle_track('gym', 148, 'C', [('C', 'min'), ('Ab', 'maj'), ('F', 'min'), ('G', 'maj')], G, 1.2)
	B = [[(0, 0, 2), (2, 1, 2), (4, 0, 2), (6, 3, 2), (8, 7, 2), (10, 6, 2), (12, 7, 4)], [(0, 12, 6), (6, 10, 2), (8, 8, 4), (12, 7, 4)],
	     [(0, 0, 2), (2, 1, 2), (4, 0, 2), (6, 3, 2), (8, 8, 2), (10, 7, 2), (12, 8, 4)], [(0, 7, 4), (4, 6, 4), (8, 7, 8)]]
	battle_track('boss', 164, 'F#', [('F#', 'min'), ('D', 'maj'), ('B', 'min'), ('C#', 'maj')], B, 1.4, boss = True)
