# test_stay_signed_in.py
# Iteration 37: the player stays signed in after closing the game, until they choose Log Out.
# Run with:  python -m unittest test_stay_signed_in

import json
import os
import tempfile
import unittest

from save_system import ProfileManager

ACCOUNT = ('Strong#Pass1', 'question_pet', 'Rex')


class StaySignedInTests(unittest.TestCase):
	def setUp(self):
		self.root = tempfile.mkdtemp()
		self.manager = ProfileManager(self.root)
		self.profile, _ = self.manager.create('Speedy', *ACCOUNT)
		self.session = os.path.join(self.root, 'session.json')

	def reopen(self):
		# a new ProfileManager reads everything from disk again, like starting the game again
		return ProfileManager(self.root).restore_session()

	def test_nobody_signed_in_at_first(self):
		self.assertIsNone(self.reopen())

	def test_still_signed_in_after_restart(self):
		self.manager.remember(self.profile)
		self.assertEqual(self.reopen()['username'], 'Speedy')

	def test_log_out_ends_the_session(self):
		self.manager.remember(self.profile)
		self.manager.forget(self.profile)
		self.assertFalse(os.path.exists(self.session))
		self.assertIsNone(self.reopen())

	def test_token_is_not_stored_in_profiles(self):
		self.manager.remember(self.profile)
		token = json.load(open(self.session))['data']['token']
		self.assertNotIn(token, open(os.path.join(self.root, 'profiles.json')).read())

	def test_edited_session_file_is_rejected(self):
		self.manager.remember(self.profile)
		payload = json.load(open(self.session))
		payload['data']['token'] = '0' * 64
		json.dump(payload, open(self.session, 'w'))
		self.assertIsNone(self.reopen())

	def test_forged_token_with_right_checksum_is_rejected(self):
		from save_system import write_protected
		self.manager.remember(self.profile)
		write_protected(self.session, {'id': self.profile['id'], 'token': 'f' * 64})
		self.assertIsNone(self.reopen())

	def test_password_change_signs_out(self):
		self.manager.remember(self.profile)
		self.manager.change_password(self.profile, 'Strong#Pass1', 'Other#Pass22')
		self.assertIsNone(self.reopen())

	def test_switching_account_remembers_the_new_one(self):
		other, _ = self.manager.create('Simran', *ACCOUNT)
		self.manager.remember(self.profile)
		self.manager.forget(self.profile)
		self.manager.remember(other)
		self.assertEqual(self.reopen()['username'], 'Simran')

	def test_garbage_file_does_not_crash(self):
		open(self.session, 'w').write('not json')
		self.assertIsNone(self.reopen())


if __name__ == '__main__':
	unittest.main()
