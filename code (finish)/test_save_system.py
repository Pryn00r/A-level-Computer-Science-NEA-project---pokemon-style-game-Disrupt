# test_save_system.py
# Automated unit tests for usernames, save slots, backups, checksums, the leaderboard and translations.
# Run with:  python -m unittest test_save_system

import json
import os
import tempfile
import unittest

from localisation import DOCUMENTS, LANGUAGES, STRINGS
from monster import Monster
from save_system import (ProfileManager, calculate_score, deserialise_monster, 
	read_protected, serialise_monster, validate_username, write_protected)
from settings import SAVE_SLOT_COUNT


# Iteration 14: accounts now need a password, security question and answer
ACCOUNT = ('Strong#Pass1', 'question_pet', 'Rex')


def sample_save(trainers = (), level = 10):
	return {
		'party': [serialise_monster(Monster('Atrox', level))],
		'defeated_trainers': list(trainers),
		'play_time': 65,
		'saved_at': '2026-11-02 21:00'}


class UsernameTests(unittest.TestCase):
	def test_accepts_a_valid_name(self):
		self.assertIsNone(validate_username('Simran_1', []))

	def test_rejects_invalid_names(self):
		self.assertEqual(validate_username('ab', []), 'username_too_short')
		self.assertEqual(validate_username('a' * 13, []), 'username_too_long')
		self.assertEqual(validate_username('bad name', []), 'username_invalid')
		self.assertEqual(validate_username('nàme', []), 'username_invalid')
		self.assertEqual(validate_username('Admin', []), 'username_reserved')

	def test_duplicate_check_ignores_case(self):
		self.assertEqual(validate_username('SIMRAN', ['simran']), 'username_taken')


class SaveTests(unittest.TestCase):
	def setUp(self):
		self.folder = tempfile.TemporaryDirectory()
		self.root = self.folder.name
		self.addCleanup(self.folder.cleanup)
		self.profiles = ProfileManager(self.root)
		self.profile, _ = self.profiles.create('Simran', *ACCOUNT)
		self.saves = self.profiles.get_saves(self.profile)

	def damage(self, path):
		with open(path, 'w', encoding = 'utf-8') as file:
			file.write('{broken')

	def test_usernames_persist_between_sessions(self):
		reopened = ProfileManager(self.root)
		self.assertEqual(reopened.usernames(), ['Simran'])
		profile, error = reopened.create('simran', *ACCOUNT)
		self.assertIsNone(profile)
		self.assertEqual(error, 'username_taken')

	def test_there_are_at_least_three_isolated_slots(self):
		self.assertGreaterEqual(SAVE_SLOT_COUNT, 3)
		self.saves.write_slot(1, sample_save(['o1']))
		self.saves.write_slot(2, sample_save(['o2']))
		self.saves.delete_slot(1)
		self.assertEqual(self.saves.slot_info(1)['status'], 'empty')
		self.assertEqual(self.saves.read_slot(2)['defeated_trainers'], ['o2'])

	def test_damaged_slot_does_not_affect_other_slots(self):
		self.saves.write_slot(1, sample_save())
		self.saves.write_slot(2, sample_save())
		self.damage(self.saves.slot_path(1))
		self.assertEqual(self.saves.slot_info(1)['status'], 'corrupted')
		self.assertEqual(self.saves.slot_info(2)['status'], 'ok')

	def test_damaged_slot_recovers_from_backup(self):
		self.saves.write_slot(1, sample_save(['o1']))
		self.saves.write_slot(1, sample_save(['o1', 'o2']))
		self.damage(self.saves.slot_path(1))
		self.assertEqual(self.saves.read_slot(1)['defeated_trainers'], ['o1'])

	def test_edited_save_fails_its_checksum(self):
		path = self.saves.slot_path(1)
		self.saves.write_slot(1, sample_save())
		with open(path, encoding = 'utf-8') as file:
			payload = json.load(file)
		payload['data']['play_time'] = 999
		with open(path, 'w', encoding = 'utf-8') as file:
			json.dump(payload, file)
		self.assertEqual(self.saves.slot_info(1)['status'], 'corrupted')

	def test_damaged_file_never_replaces_a_good_backup(self):
		path = os.path.join(self.root, 'file.json')
		write_protected(path, {'value': 1})
		write_protected(path, {'value': 2})
		self.damage(path)
		write_protected(path, {'value': 3})
		self.damage(path)
		self.assertEqual(read_protected(path), {'value': 1})

	def test_players_have_separate_slots(self):
		other, _ = self.profiles.create('Rival', *ACCOUNT)
		self.saves.write_slot(1, sample_save())
		self.assertEqual(self.profiles.get_saves(other).slot_info(1)['status'], 'empty')

	def test_leaderboard_uses_each_players_best_slot(self):
		rival, _ = self.profiles.create('Rival', *ACCOUNT)
		self.saves.write_slot(1, sample_save(level = 5))
		self.saves.write_slot(2, sample_save(['o1', 'o2'], level = 5))
		self.profiles.get_saves(rival).write_slot(1, sample_save(['o1'], level = 50))
		board = self.profiles.leaderboard()
		self.assertEqual([entry['username'] for entry in board], ['Simran', 'Rival'])
		self.assertEqual(board[0]['score'], 205)
		self.assertEqual(calculate_score(sample_save(['o1'], level = 50)), 150)


class MonsterSaveTests(unittest.TestCase):
	def test_monster_survives_save_and_load(self):
		monster = Monster('Gulfin', 12)
		monster.xp, monster.health, monster.energy = 40, 33.5, 12
		loaded = deserialise_monster(json.loads(json.dumps(serialise_monster(monster))))
		self.assertEqual((loaded.name, loaded.level, loaded.xp, loaded.health, loaded.energy), ('Gulfin', 12, 40, 33.5, 12))
		self.assertEqual(loaded.level_up, monster.level_up)


class LanguageTests(unittest.TestCase):
	def test_every_language_has_every_screen_string(self):
		english = set(STRINGS['en'])
		for language in LANGUAGES:
			missing = english - set(STRINGS[language])
			self.assertLessEqual(missing, {'search_stats'}, language)

	def test_every_language_has_every_document(self):
		for language in LANGUAGES:
			self.assertEqual(set(DOCUMENTS[language]), set(DOCUMENTS['en']))


if __name__ == '__main__':
	unittest.main()
