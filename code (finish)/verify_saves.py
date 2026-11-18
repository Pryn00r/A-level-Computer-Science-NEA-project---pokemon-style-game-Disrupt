# verify_saves.py
# Testing tool: checks the checksum of every file in the saves folder, then shows that changing one
# value in a copy of a save makes its checksum fail. Run with:  python verify_saves.py

import copy
import json
import os
from save_system import SAVE_ROOT, get_checksum

# go through every file in the saves folder and its sub folders
for folder, _, file_names in os.walk(SAVE_ROOT):
	for file_name in sorted(file_names):
		path = os.path.join(folder, file_name)
		with open(path, encoding = 'utf-8') as file:
			payload = json.load(file)
		result = 'checksum OK' if payload['checksum'] == get_checksum(payload['data']) else 'checksum FAILED'
		owner = payload['data'].get('username', '')
		print(f'{os.path.relpath(path, SAVE_ROOT):<70} {owner:<11} {result}')

# tamper test: raise the first monster's level in a copy of a save and check the checksum again
for folder, _, file_names in os.walk(SAVE_ROOT):
	if 'slot_1.json' in file_names:
		with open(os.path.join(folder, 'slot_1.json'), encoding = 'utf-8') as file:
			payload = json.load(file)
		edited = copy.deepcopy(payload['data'])
		edited['party'][0]['level'] = 100
		print(f"Edited {payload['data']['username']}'s level 32 -> 100. Checksum still matches: {get_checksum(edited) == payload['checksum']}")
		break
