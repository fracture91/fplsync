"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import unittest
import fplsync
import math

class TestConfig(unittest.TestCase):

	def setUp(self):
		self.config = fplsync.Config()
		self.config.playlist_source = "."
		self.config.source = "."
		self.config.dest = "."

	def test_basic(self):
		self.config.validate() # no errors

	def test_size_params(self):
		self.config.max_size = 1000
		self.config.min_free = 1000
		self.config.validate()

		self.config.min_free = -1000
		with self.assertRaises(ValueError):
			self.config.validate()

		self.config.max_size = {}
		with self.assertRaises(Exception):
			self.config.validate()

		self.config.min_free = {}
		with self.assertRaises(Exception):
			self.config.validate()

		self.config.min_free = "1k"
		self.config.max_size = "1k"
		self.config.validate()
		self.assertEqual(self.config.min_free, self.config.max_size, 1024)

	def test_size_str_to_bytes(self):
		self.assertEqual(self.config.size_str_to_bytes("1"), 1)
		self.assertEqual(self.config.size_str_to_bytes("-1"), -1)
		self.assertEqual(self.config.size_str_to_bytes("1k"), 1024)
		self.assertEqual(self.config.size_str_to_bytes("1K"), 1024)
		self.assertEqual(self.config.size_str_to_bytes("2K"), 2 * 1024)
		self.assertEqual(self.config.size_str_to_bytes("-1K"), -1024)
		self.assertEqual(self.config.size_str_to_bytes("1M"), math.pow(1024, 2))
		self.assertEqual(self.config.size_str_to_bytes("1G"), math.pow(1024, 3))
		self.assertEqual(self.config.size_str_to_bytes("1T"), math.pow(1024, 4))
		with self.assertRaises(Exception):
			self.config.size_str_to_bytes("1O")
		with self.assertRaises(Exception):
			self.config.size_str_to_bytes("purple")

