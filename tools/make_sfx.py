# Generates the chiptune sound effects and music for Disrupt (square/triangle waves + noise drums).
import wave, struct, math, random, sys
RATE = 22050
OUT = sys.argv[1]
random.seed(7)
NOTE = {n: i for i, n in enumerate(['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'])}
def freq(name):
    if name in (None, '-'): return 0
    n, o = name[:-1], int(name[-1])
    return 440 * 2 ** ((NOTE[n] + 12 * (o - 4) - 9) / 12)
def osc(kind, f, t, duty=0.5):
    if f == 0: return 0
    ph = (f * t) % 1
    if kind == 'square': return 1 if ph < duty else -1
    if kind == 'tri': return 4 * abs(ph - 0.5) - 1
    if kind == 'sine': return math.sin(2 * math.pi * ph)
def tone(buf, start, length, f, kind='square', vol=0.3, duty=0.5, attack=0.005, release=0.05, slide=0):
    n0 = int(start * RATE); n = int(length * RATE)
    for i in range(n):
        t = i / RATE
        env = min(1, t / attack) * min(1, (length - t) / release) if release else min(1, t / attack)
        ff = f * (1 + slide * t / length)
        idx = n0 + i
        if idx >= len(buf): break
        buf[idx] += osc(kind, ff, t, duty) * vol * max(0, env)
def noise(buf, start, length, vol=0.2, decay=30):
    n0 = int(start * RATE)
    for i in range(int(length * RATE)):
        idx = n0 + i
        if idx >= len(buf): break
        buf[idx] += (random.random() * 2 - 1) * vol * math.exp(-decay * i / RATE)
def save(name, buf):
    peak = max(1e-9, max(abs(x) for x in buf))
    scale = min(1, 0.9 / peak)
    with wave.open(f'{OUT}/{name}.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(b''.join(struct.pack('<h', int(max(-1, min(1, x * scale)) * 32000)) for x in buf))
def sfx(name, length, notes):
    buf = [0.0] * int(length * RATE)
    for args in notes: tone(buf, *args)
    save(name, buf)

# --- short effects ---
sfx('menu_move', 0.06, [(0, 0.05, freq('A5'), 'square', 0.25, 0.25, 0.002, 0.02)])
sfx('menu_select', 0.14, [(0, 0.06, freq('E5'), 'square', 0.25, 0.5), (0.06, 0.08, freq('A5'), 'square', 0.25, 0.5)])
sfx('menu_back', 0.12, [(0, 0.05, freq('A5'), 'square', 0.22, 0.5), (0.05, 0.07, freq('E5'), 'square', 0.22, 0.5)])
sfx('coin', 0.35, [(0, 0.07, freq('B5'), 'square', 0.25, 0.5), (0.07, 0.28, freq('E6'), 'square', 0.25, 0.5, 0.002, 0.2)])
sfx('catch', 0.9, [(i * 0.09, 0.12, freq(n), 'square', 0.22, 0.5) for i, n in enumerate(['C5','E5','G5','C6','E6','G6'])] + [(0.55, 0.35, freq('C6'), 'tri', 0.3, 0.5, 0.01, 0.3)])
sfx('catch_fail', 0.6, [(0, 0.5, freq('E5'), 'square', 0.22, 0.5, 0.005, 0.2, -0.5)])
sfx('level_up', 0.8, [(i * 0.08, 0.1, freq(n), 'square', 0.22, 0.25) for i, n in enumerate(['C5','D5','E5','G5','C6'])] + [(0.42, 0.36, freq('E6'), 'square', 0.22, 0.25, 0.005, 0.3)])
sfx('save', 0.4, [(0, 0.12, freq('G5'), 'tri', 0.35), (0.12, 0.25, freq('D6'), 'tri', 0.35, 0.5, 0.005, 0.2)])
sfx('heal', 0.7, [(i * 0.1, 0.25, freq(n), 'sine', 0.3, 0.5, 0.01, 0.2) for i, n in enumerate(['C5','E5','G5','C6'])])
sfx('super_hit', 0.25, [(0, 0.2, freq('C3'), 'square', 0.3, 0.5, 0.002, 0.1, -0.4)])

# victory fanfare
buf = [0.0] * int(2.6 * RATE)
mel = [('C5',.15),('C5',.15),('C5',.15),('C5',.45),('G#4',.45),('A#4',.45),('C5',.3),('A#4',.15),('C5',.9)]
t = 0
for n, d in mel:
    tone(buf, t, d * 0.95, freq(n), 'square', 0.25, 0.5); tone(buf, t, d * 0.95, freq(n) / 2, 'tri', 0.25)
    t += d
save('victory', buf)

# --- music loops ---
def song(name, bpm, lead, bass, drums, bars_repeat=2, duty=0.5, lead_vol=0.18):
    beat = 60 / bpm
    length = sum(d for _, d in lead) * beat * bars_repeat
    buf = [0.0] * int(length * RATE)
    for r in range(bars_repeat):
        off = r * sum(d for _, d in lead) * beat
        t = off
        for n, d in lead:
            if n != '-': tone(buf, t, d * beat * 0.9, freq(n), 'square', lead_vol, duty, 0.005, 0.03)
            t += d * beat
        t = off
        for n, d in bass:
            if n != '-': tone(buf, t, d * beat * 0.95, freq(n), 'tri', 0.28, 0.5, 0.005, 0.02)
            t += d * beat
        t = off
        for kind, d in drums:
            if kind == 'k': tone(buf, t, 0.12, 110, 'sine', 0.35, 0.5, 0.001, 0.1, -0.6)
            if kind == 's': noise(buf, t, 0.12, 0.18, 25)
            if kind == 'h': noise(buf, t, 0.03, 0.06, 120)
            t += d * beat
    save(name, buf)

# gym theme: upbeat, major key, 4 bars x 4 beats
gym_lead = [('E5',.5),('G5',.5),('A5',1),('G5',.5),('E5',.5),('D5',1), ('C5',.5),('D5',.5),('E5',.5),('G5',.5),('A5',2),
            ('A5',.5),('C6',.5),('B5',.5),('A5',.5),('G5',1),('E5',1), ('D5',.5),('E5',.5),('G5',.5),('E5',.5),('C5',2)]
gym_bass = [('A2',1),('A3',1),('A2',1),('A3',1), ('F2',1),('F3',1),('F2',1),('F3',1), ('C3',1),('C4',1),('C3',1),('C4',1), ('G2',1),('G3',1),('G2',1),('G3',1)]
gym_drums = [('k',.5),('h',.5),('s',.5),('h',.5)] * 8
# (Iteration 19: the gym and boss music are now made by make_music.py)
# song('gym', 138, gym_lead, gym_bass, gym_drums, 3, 0.25)

# boss theme: minor, faster, driving
boss_lead = [('E5',.25),('E5',.25),('G5',.5),('E5',.25),('D#5',.25),('E5',.5), ('B4',.5),('C5',.5),('B4',.5),('A4',.5),
             ('E5',.25),('E5',.25),('G5',.5),('A5',.5),('B5',.5), ('C6',.5),('B5',.5),('A5',.5),('G5',.5),
             ('F#5',.5),('G5',.5),('A5',.5),('B5',.5), ('E5',1),('-',.5),('B4',.5),
             ('C5',.5),('D5',.5),('E5',.5),('F#5',.5), ('E5',2)]
boss_bass = [('E2',.5),('E3',.5)] * 4 + [('C2',.5),('C3',.5)] * 4 + [('A2',.5),('A3',.5)] * 4 + [('B2',.5),('B3',.5)] * 4
boss_drums = [('k',.25),('h',.25),('s',.25),('h',.25)] * 16
# song('boss', 168, boss_lead, boss_bass, boss_drums, 3, 0.5, 0.16)

# ending theme: slow, gentle
end_lead = [('C5',1),('E5',1),('G5',2), ('F5',1),('E5',1),('D5',2), ('C5',1),('E5',1),('A5',2), ('G5',4)]
end_bass = [('C3',4),('F2',4),('A2',4),('G2',4)]
song('ending', 80, end_lead, end_bass, [('-',16)], 2, 0.5, 0.15)
print('done')
