# make_sounds.py
# Iteration 20+: generates the extra sound effects (footsteps, ambience, jingles and one hit sound per
# type) with numpy, reusing the instruments in make_music.py. Every sound is original.
# Run with:  python tools/make_sounds.py   (writes .ogg files into the audio folder)

import os
import subprocess
import wave
from os.path import join

import numpy as np

from make_music import SR, AUDIO, times, env, band, lowpass, highpass, noise, saw, square, hz, midi, kalimba, glock, marimba, bell, pluck, rng

def save(name, sound, stereo = False, normalise = 0.8):
	sound = np.asarray(sound, dtype = float)
	peak = np.max(np.abs(sound)) or 1
	sound = sound / peak * normalise
	if not stereo:
		sound = np.stack([sound, sound], axis = 1)
	path = join(AUDIO, f'{name}.wav')
	with wave.open(path, 'wb') as file:
		file.setnchannels(2)
		file.setsampwidth(2)
		file.setframerate(SR)
		file.writeframes((sound * 32767).astype('<i2').tobytes())
	subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', path, '-c:a', 'libvorbis', '-q:a', '4', join(AUDIO, f'{name}.ogg')], check = True)
	os.remove(path)

def seq(notes, voice, step = 0.12, tail = 0.6):
	length = step * len(notes) + tail
	out = np.zeros(int(length * SR))
	for i, note in enumerate(notes):
		if note is None:
			continue
		s = voice(note)
		start = int(i * step * SR)
		out[start:start + len(s)] += s[:len(out) - start]
	return out

def loop_crossfade(sound, fade = 0.5):
	# makes a sound loop smoothly by fading its end into its start
	n = int(fade * SR)
	head, tail = sound[:n].copy(), sound[-n:]
	ramp = np.linspace(0, 1, n)
	out = sound[n:].copy()
	out[-n:] = tail * (1 - ramp) + head * ramp
	return out

# ---------- footsteps (short, quiet) ----------
def step(kind):
	t = times(0.12)
	if kind == 'grass':
		return band(noise(0.12), 2000, 7000) * np.exp(-t * 40) * 0.6
	if kind == 'sand':
		return band(noise(0.12), 800, 3500) * np.exp(-t * 28) * 0.7
	if kind == 'snow':
		crunch = band(noise(0.12), 1500, 5000) * (rng.uniform(0, 1, len(t)) > 0.6) * np.exp(-t * 22)
		return crunch * 0.8
	return band(noise(0.12), 200, 1200) * np.exp(-t * 50) + np.sin(2 * np.pi * 140 * t) * np.exp(-t * 60) * 0.5   # wood

# ---------- ambience (8 second loops) ----------
def ambience(kind):
	length = 8.5
	t = times(length)
	if kind == 'grass':   # soft breeze with birds chirping now and then
		air = lowpass(noise(length), 600) * 0.15
		for start in (0.6, 2.2, 3.1, 5.0, 6.4, 7.3):
			n = int(start * SR)
			ct = times(0.18)
			chirp = np.sin(2 * np.pi * np.cumsum(2600 + 1200 * np.sin(ct * 60)) / SR) * np.exp(-ct * 18) * 0.25
			for rep in range(2):
				m = n + int(rep * 0.12 * SR)
				air[m:m + len(chirp)] += chirp[:len(air) - m]
		return loop_crossfade(air)
	if kind == 'sand':    # dry gusting wind
		gust = 0.5 + 0.5 * np.sin(2 * np.pi * t / 4.25) ** 2
		return loop_crossfade(band(noise(length), 300, 1800) * gust * 0.35)
	if kind == 'ice':     # cold wind with tinkling ice
		wind = band(noise(length), 500, 2500) * (0.4 + 0.3 * np.sin(2 * np.pi * t / 8.5)) * 0.3
		for start, note in ((1.0, 'E6'), (3.4, 'B6'), (5.2, 'G6'), (7.0, 'D7')):
			n = int(start * SR)
			s = glock(note, 1.2) * 0.4
			wind[n:n + len(s)] += s[:len(wind) - n]
		return loop_crossfade(wind)
	# sea: slow waves
	swell = (0.5 - 0.5 * np.cos(2 * np.pi * t / 4.25)) ** 2
	return loop_crossfade(lowpass(noise(length), 900) * swell * 0.5)

# ---------- one hit sound per type ----------
def hit(kind):
	t = times(0.45)
	if kind == 'normal':
		return np.sin(2 * np.pi * np.cumsum(120 + 200 * np.exp(-t * 30)) / SR) * np.exp(-t * 14) + band(noise(0.45), 300, 2000) * np.exp(-t * 40) * 0.5
	if kind == 'fire':
		return band(noise(0.45), 400, 3000) * (np.exp(-t * 6) * (0.6 + 0.4 * (rng.uniform(0, 1, len(t)) > 0.85)))
	if kind == 'water':
		return band(noise(0.45), 300, 1500) * np.exp(-t * 9) + np.sin(2 * np.pi * np.cumsum(700 - 500 * t) / SR) * np.exp(-t * 12) * 0.4
	if kind == 'plant':
		return band(noise(0.45), 2500, 8000) * np.exp(-t * 18) + np.sin(2 * np.pi * np.cumsum(1500 - 2000 * t) / SR) * np.exp(-t * 20) * 0.3
	if kind == 'ice':
		return sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in ((2100, 9), (3170, 12), (4400, 15))) * 0.4 + highpass(noise(0.45), 5000) * np.exp(-t * 30) * 0.4
	if kind == 'poison':
		out = np.zeros(len(t))
		for i, f in enumerate((300, 420, 260, 380)):
			bt = times(0.12)
			b = np.sin(2 * np.pi * np.cumsum(f + 600 * bt) / SR) * np.exp(-bt * 30)
			s = int(i * 0.08 * SR)
			out[s:s + len(b)] += b[:len(out) - s]
		return out
	if kind == 'bug':
		buzz = square(110, t, 0.3) * (0.5 + 0.5 * square(30, t))
		return lowpass(buzz, 1800) * np.exp(-t * 6) * 0.6
	if kind == 'flying':
		return band(noise(0.45), 600, 4000) * np.sin(np.pi * t / 0.45) ** 2 * 0.9
	# psychic: a wobbling chime
	f = 600 * (1 + 0.3 * np.sin(2 * np.pi * 9 * t))
	return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5) * 0.6 + np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR) * np.exp(-t * 6) * 0.3

# Iteration 24: a short cry for every monster. The shape comes from the name (so it is always the
# same for that monster), bigger monsters (later evolutions) sound lower, and the element adds colour.
def cry(name, element, stage):
	seed = sum(ord(c) * (i + 1) for i, c in enumerate(name))
	pick = np.random.default_rng(seed)
	length = 0.35 + 0.06 * stage
	t = times(length)
	base = 700 / (1.2 ** stage) * pick.uniform(0.85, 1.2)   # Iteration 32: higher, so big monsters do not rumble
	# a rising-then-falling call with one or two "syllables"
	syllables = pick.integers(1, 3)
	shape = np.sin(np.pi * np.clip(t * syllables / length, 0, syllables) % 1) ** 0.6
	glide = 1 + pick.uniform(0.3, 0.8) * np.sin(np.pi * t / length) - 0.3 * t / length
	vibrato = 1 + pick.uniform(0.01, 0.05) * np.sin(2 * np.pi * pick.uniform(5, 12) * t)
	f = base * glide * vibrato
	phase = 2 * np.pi * np.cumsum(f) / SR
	voice = np.sin(phase) + 0.5 * np.sin(2 * phase) + 0.25 * np.sin(3 * phase + 0.4)
	if element in ('fire', 'poison', 'bug'):
		voice = voice + 0.3 * np.sin(phase * 3.01)         # Iteration 32: a brighter edge (the old buzz sounded rude)
	if element in ('ice', 'psychic'):
		voice = voice + 0.4 * np.sin(phase * 2.01)         # shimmering
	if element in ('water', 'flying'):
		voice = lowpass(voice, 2200)                       # soft
	if element == 'code':
		voice = np.sign(np.sin(phase)) * (0.5 + 0.5 * square(14, t))   # a glitchy square wave
	return lowpass(voice, 3500) * shape * np.exp(-t * 2.5)

def stage_of(name, data):
	stage = 0
	for other, info in data.items():
		if info['evolve'] and info['evolve'][0] == name:
			return stage_of(other, data) + 1
	return stage

# Iteration 32: the sound when a battle starts - a rising swoosh into a bright arpeggio
def battle_start():
	length = 1.1
	t = times(length)
	sweep = band(noise(length), 800, 7000) * np.clip(t / 0.35, 0, 1) ** 2 * np.exp(-np.clip(t - 0.35, 0, None) * 9) * 0.5
	notes = seq(['E5', 'G#5', 'B5', 'E6', 'B6'], lambda n: glock(n, 0.6), 0.05, 0.6)
	out = np.zeros(len(t))
	start = int(0.3 * SR)
	out[start:start + len(notes)] += notes[:len(out) - start] * 1.6
	return out + sweep

if __name__ == '__main__':
	import sys
	if 'battle_start' in sys.argv:
		save('battle_start', battle_start(), normalise = 0.6)
		print('battle start written')
		sys.exit()
	if 'cries' in sys.argv:
		sys.path.insert(0, join(os.path.dirname(__file__), '..', 'code'))
		from game_data import MONSTER_DATA
		for name, info in MONSTER_DATA.items():
			save(f'cry_{name}', cry(name, info['stats']['element'], stage_of(name, MONSTER_DATA)), normalise = 0.55)
		print('cries written')
		sys.exit()
	for kind in ('grass', 'sand', 'snow', 'wood'):
		save(f'step_{kind}', step(kind), normalise = 0.5)
	for kind in ('grass', 'sand', 'ice', 'sea'):
		save(f'amb_{kind}', ambience(kind), normalise = 0.6)
	for kind in ('normal', 'fire', 'water', 'plant', 'ice', 'poison', 'bug', 'flying', 'psychic'):
		save(f'hit_{kind}', hit(kind))
	save('miss', band(noise(0.35), 500, 3000) * np.sin(np.pi * times(0.35) / 0.35) ** 2, normalise = 0.6)
	save('crit', np.concatenate([np.zeros(10), hit('normal')]) + np.pad(glock('E7', 0.6), (0, 0))[:len(hit('normal')) + 10] * 0.5)
	save('badge', seq(['C5', 'E5', 'G5', 'C6', None, 'G5', 'C6'], lambda n: marimba(n, 0.6), 0.11, 0.9))
	save('quest', seq(['G5', 'B5', 'D6', 'G6'], lambda n: kalimba(n, 0.7), 0.09, 0.8))
	save('unlock', seq(['E5', 'G#5', 'B5', 'E6', 'G#6'], lambda n: glock(n, 0.8), 0.07, 0.9))
	save('rival', seq(['A4', 'A4', None, 'C5', 'A4', None, 'E5', 'D#5'], lambda n: pluck(n, 0.25, 3500), 0.1, 0.4))
	save('status', seq(['E5', 'C5', 'A4'], lambda n: pluck(n, 0.2, 2500), 0.06, 0.3), normalise = 0.6)
	save('stat_up', seq(['C5', 'E5', 'G5', 'C6'], lambda n: glock(n, 0.4), 0.05, 0.4), normalise = 0.6)
	save('stat_down', seq(['C6', 'G5', 'E5', 'C5'], lambda n: glock(n, 0.4), 0.05, 0.4), normalise = 0.6)
	save('door', lowpass(noise(0.3), 500) * np.exp(-times(0.3) * 12) + np.sin(2 * np.pi * 90 * times(0.3)) * np.exp(-times(0.3) * 25), normalise = 0.6)
	save('bump', np.sin(2 * np.pi * 70 * times(0.12)) * np.exp(-times(0.12) * 40), normalise = 0.5)
	save('pickup', seq(['E6', 'B6'], lambda n: glock(n, 0.5), 0.07, 0.4), normalise = 0.6)
	save('splash_fish', band(noise(0.5), 400, 3000) * np.exp(-times(0.5) * 8), normalise = 0.7)
	save('dig', band(noise(0.25), 200, 1500) * np.exp(-times(0.25) * 15), normalise = 0.7)
	print('sounds written')
