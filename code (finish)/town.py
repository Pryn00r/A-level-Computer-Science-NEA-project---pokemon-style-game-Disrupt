# town.py
# Iteration 25c: fast travel to places you have visited.
# Iteration 31: the daycare and eggs, crafting, the move tutor, trading, the bounty board, the twins'
# battle, the people around town and the phone calls were removed. Only fast travel is left.

from settings import *

# spawn point on the world map.
# Iteration 32: the towns have names (Forest Town is home and its hospital, Snow Town is the hospital in
# the snow, Desert Ruins is the stone arch in the south) and every gym can be teleported to straight away,
# because walking there takes so long.
TRAVEL_SPOTS = ('house', 'hospital2', 'ruins', 'plant', 'fire', 'water')

def visited(game):
	return list(TRAVEL_SPOTS)

def remember_visit(game, map_name, spawn):
	if map_name == 'world' and spawn in TRAVEL_SPOTS:
		places = game.story.setdefault('visited', [])
		if spawn not in places:
			places.append(spawn)
