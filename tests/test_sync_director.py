"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import unittest
import fplsync
from copy import copy
import tempfile
from contextlib import contextmanager
import shutil
import os

class TestSizeParams(unittest.TestCase):
	
	def run(self, result=None):
		with self.make_mock_fs() as self.original_config:
			self.original_config.free_override = 10000
			self.original_config.total_override = 20000
			super().run(result)

	@contextmanager
	def make_mock_fs(self):
		"""Create a mock filesystem in a temp directory containing expected structure"""
		temp = tempfile.mkdtemp(prefix="fpltest")
		try:
			config = fplsync.Config()
			config.playlist_source = os.path.join(temp, "fb2k_playlists")
			config.source = os.path.join(temp, "source")
			config.dest = os.path.join(temp, "dest")
			config.playlist_dest = os.path.join(temp, "playlists")
			os.mkdir(config.source)
			with open(os.path.join(config.source, "a.mp3"), "w") as f:
				print("a" * 1000, file=f, end="")
			with open(os.path.join(config.source, "b.mp3"), "w") as f:
				print("b" * 1000, file=f, end="")
			with open(os.path.join(config.source, "c.mp3"), "w") as f:
				print("c" * 1000, file=f, end="")
			os.mkdir(config.dest)
			os.mkdir(config.playlist_source)
			os.mkdir(config.playlist_dest)
			yield config
		finally:
			shutil.rmtree(temp)

	def setUp(self):
		self.config = copy(self.original_config)

	def test_max_size(self):
		sd = fplsync.SyncDirector(self.config)
		self.assertEqual(sd.max_size, self.config.free_override)

		self.config.max_size = 0
		with self.assertRaises(Exception):
			sd = fplsync.SyncDirector(self.config)

		self.config.max_size = -15000
		sd = fplsync.SyncDirector(self.config)
		self.assertEqual(sd.max_size, self.config.total_override - 15000)

		self.config.max_size = 7000
		sd = fplsync.SyncDirector(self.config)
		self.assertEqual(sd.max_size, 7000)

		# free space limit takes precedence
		self.config.max_size = 15000
		sd = fplsync.SyncDirector(self.config)
		self.assertEqual(sd.max_size, self.config.free_override)

	def test_min_free(self):
		self.config.min_free = 3000
		sd = fplsync.SyncDirector(self.config)
		self.assertEqual(sd.max_size, self.config.free_override - 3000)

		# not enough free space on the destination device
		self.config.min_free = 15000
		with self.assertRaises(Exception):
			sd = fplsync.SyncDirector(self.config)

	def test_min_max(self):
		self.config.max_size = 5000
		self.config.min_free = 3000
		sd = fplsync.SyncDirector(self.config)
		self.assertEqual(sd.max_size, 5000)

		self.config.max_size = 5000
		self.config.min_free = 7000
		sd = fplsync.SyncDirector(self.config)
		self.assertEqual(sd.max_size, self.config.free_override - 7000)

		self.config.max_size = -13000
		self.config.min_free = 2000
		sd = fplsync.SyncDirector(self.config)
		self.assertEqual(sd.max_size, self.config.total_override - 13000)

		self.config.max_size = -13000
		self.config.min_free = 5000
		sd = fplsync.SyncDirector(self.config)
		self.assertEqual(sd.max_size, self.config.free_override - 5000)

	def test_existing_files(self):
		with self.make_mock_fs() as self.config:
			self.config.free_override = 10000
			self.config.total_override = 20000
			mp3path = os.path.join(self.config.source, "a.mp3")
			shutil.copy(mp3path, self.config.dest)
			
			# the size of the file in dest should be added to free space count
			sd = fplsync.SyncDirector(self.config)
			self.assertEqual(sd.max_size, self.config.free_override + 1000)

			# make sure playlist_dest is counted, too
			shutil.copy(mp3path, self.config.playlist_dest)
			sd = fplsync.SyncDirector(self.config)
			self.assertEqual(sd.max_size, self.config.free_override + 2000)

