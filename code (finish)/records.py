# records.py
# Iteration 25b: achievements, daily and weekly quests, play statistics and where each monster lives.
#   - Achievements unlock once, show a gold pop-up and some give a reward (the Shiny Charm for 20 species).
#   - Daily quests (3, new every day) and a weekly quest (new every Monday) count from the moment the
#     day or week starts, using the same counters as the stats screen.
#   - habitat(name) says where a monster can be found, for the monster index.

from datetime import date
from random import Random

from settings import GYM_LEADERS
from game_data import MONSTER_DATA, WILD_ENCOUNTERS, NIGHT_ENCOUNTERS, NIGHT_ONLY, STARTER_MONSTERS

# id -> (what is measured, target, reward). The measures are worked out in progress() below.
ACHIEVEMENTS = {
	'first_steps':     ('steps', 1000, {'coins': 100}),
	'night_owl':       ('night_catches', 1, {'items': {'great_orb': 2}}),
	# (Iteration 31: the fishing, digging and hidden-item achievements were removed with those activities)
	'shiny_hunter':    ('shiny', 1, {'coins': 300}),
	'collector':       ('caught', 12, {'items': {'shiny_charm': 1}}),
	'critical':        ('crits', 10, {'items': {'power_band': 1}}),
	'gym_sweep':       ('gyms', len(GYM_LEADERS), {'items': {'prime_orb': 2}}),
	'big_spender':     ('spent', 5000, {'items': {'lucky_coin': 1}}),
	'veteran':         ('wins', 25, {'items': {'party_heal': 2}}),
	'level_50':        ('level', 50, {'coins': 1000}),
	'speedrunner':     ('speedrun', 1, {'coins': 1500}),
	'boss_slayer':     ('bosses', 3, {'coins': 2000}),   # Iteration 27: replaces the Codeus achievement
	'dedicated':       ('dailies', 5, {'items': {'max_ether': 3}}),
}
SPEEDRUN_TARGET = 2 * 60 * 60   # seconds: finish the story in under 2 hours

# Daily quest pool: (counter, target, coins). Three are picked each day from the date.
DAILY_POOL = (('wins', 3, 150), ('catches', 2, 150), ('evolved', 1, 200), ('steps', 300, 100), ('crits', 2, 120), ('night_catches', 1, 200))
WEEKLY_POOL = (('wins', 20, 800), ('catches', 10, 800), ('evolved', 2, 700), ('steps', 2000, 600), ('crits', 15, 600))
DAILY_COUNT = 3

# The numbers on the stats screen (counter name, text key). Counters live in game.counters.
STATS = ('steps', 'wins', 'catches', 'shiny', 'evolved', 'crits', 'spent', 'dailies')   # Iteration 28: rival wins removed; Iteration 31: fishing, digging and hidden items removed


def today():
	return date.today()

def week_key(day = None):
	year, week, _ = (day or today()).isocalendar()
	return f'{year}-W{week:02d}'

# What an achievement measures, for this game.
def progress(game, kind):
	if kind == 'caught':
		return len(game.caught)
	if kind == 'level':
		return game.party_level()
	if kind == 'gyms':
		from game_data import TRAINER_DATA
		return sum(1 for leader in GYM_LEADERS if TRAINER_DATA[leader]['defeated'])
	if kind == 'speedrun':
		finish = game.story.get('finish_time')
		return 1 if finish is not None and finish <= SPEEDRUN_TARGET else 0
	return game.counters.get(kind, 0)

def unlocked(game):
	return game.story.setdefault('achievements', [])

# Unlocks every achievement that has reached its target. Returns the ids unlocked just now.
def check(game):
	new = []
	for name, (kind, target, reward) in ACHIEVEMENTS.items():
		if name not in unlocked(game) and progress(game, kind) >= target:
			unlocked(game).append(name)
			give(game, reward)
			new.append(name)
	return new

def give(game, reward):
	game.coins += reward.get('coins', 0)
	for item, amount in reward.get('items', {}).items():
		game.inventory[item] = game.inventory.get(item, 0) + amount

# ---------- daily and weekly quests ----------
# ('daily', counter, target, coins) chosen for today, and one for this week. The pick only depends on the
# date, so it does not change if the game is restarted.
def daily_quests(day = None):
	day = day or today()
	picker = Random(day.toordinal())
	return [f'daily:{counter}:{target}:{coins}' for counter, target, coins in picker.sample(DAILY_POOL, DAILY_COUNT)]

def weekly_quest(day = None):
	day = day or today()
	year, week, _ = day.isocalendar()
	counter, target, coins = WEEKLY_POOL[(year * 53 + week) % len(WEEKLY_POOL)]
	return f'weekly:{counter}:{target}:{coins}'

def timed_quests(game):
	return daily_quests() + [weekly_quest()]

def parse(quest):
	period, counter, target, coins = quest.split(':')
	return period, counter, int(target), int(coins)

# Remembers the counters at the start of the day / week, so a daily quest only counts what happens today.
def period_state(game, period):
	key = today().isoformat() if period == 'daily' else week_key()
	state = game.story.get(period)
	if not isinstance(state, dict) or state.get('key') != key:
		state = {'key': key, 'start': dict(game.counters), 'claimed': []}
		game.story[period] = state
	return state

def timed_progress(game, quest):
	period, counter, target, _ = parse(quest)
	state = period_state(game, period)
	return max(0, game.counters.get(counter, 0) - state['start'].get(counter, 0))

def timed_claimed(game, quest):
	period = parse(quest)[0]
	return quest in period_state(game, period)['claimed']

def claim_timed(game, quest):
	period, counter, target, coins = parse(quest)
	state = period_state(game, period)
	if quest in state['claimed']:
		return 'quest_already'
	if timed_progress(game, quest) < target:
		return 'quest_not_done'
	state['claimed'].append(quest)
	game.coins += coins
	if period == 'daily':
		game.counters['dailies'] = game.counters.get('dailies', 0) + 1
	return 'quest_claimed'

# ---------- the monster index: where a monster lives ----------
# Returns a list of (key, details) for the localisation, e.g. [('habitat_zone', 'forest'), ('habitat_night', 'sand')].
def habitat(name):
	places = []
	for zone, data in WILD_ENCOUNTERS.items():
		if name in data['monsters']:
			places.append(('habitat_night' if name in NIGHT_ONLY else 'habitat_zone', zone))
	for zone, names in NIGHT_ENCOUNTERS.items():
		if name in names and ('habitat_night', zone) not in places and ('habitat_zone', zone) not in places:
			places.append(('habitat_night', zone))
	if name in STARTER_MONSTERS:
		places.append(('habitat_starter', None))
	for other, data in MONSTER_DATA.items():
		if data['evolve'] and data['evolve'][0] == name:
			places.append(('habitat_evolve', other))
	return places

# Play time as h:mm:ss.t for the speedrun timer.
def format_time(seconds):
	seconds = max(0, seconds)
	return f'{int(seconds // 3600)}:{int(seconds % 3600 // 60):02d}:{int(seconds % 60):02d}.{int(seconds * 10) % 10}'
