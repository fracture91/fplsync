#!/usr/bin/python3

import re
import os

class Config:
	"""Holds all config info"""
	self.playlist_dir = None
	self.source_dir = None
	self.dest_dir = None
	self.dest_playlist_dir = None

class Song:
	"""Describes a song (which is just some file path)"""
	def __init__(self, windows_path):
		"""Create a song with the given windows path
		
		windows_path must be whatever was originally in the fpl file
		ex: F:\Music\Trucker's Atlas.mp3
		"""
		self._windows_path = os.ntpath.windows_path
	def get_relative_path(self, source, win_prefix=None):
		""""""
	def get_source_path(self, source, falsePrefix=None):
		"""Get the path to the local file
		
		source - the source directory of all songs (e.g. /media/Tassadar/music)
		falsePrefix
		"""

class Playlist:
	"""Holds a list of songs"""
	def __init__(self, name, fpl):
		"""Create a playlist

		name - the name of the playlist
		fpl - the path to a fpl playlist
		"""
		self.name = name
		self.fpl = fpl
		self.songs = []
		with open(self.fpl, 'rb') as infile:
			# FPL entries have file URIs surrounded by null bytes
			paths = re.findall(b'(?<=\x00file://)[^\x00]*(?=\x00)', infile.read())
			# decode the paths as utf-8 and create our songs array
			self.songs = [Song(path.decode('utf-8')) for path in paths]
	

class PlaylistIndex:
	"""Responsible for getting named playlists from fb2k"""
	def __init__(self, playlists_path):
		"""Construct a PlaylistIndex

		Reads playlist name/path associations from index.dat,
		which is found in the playlists_path directory along with fpl files.
		playlists_path should be something like ~/.foobar2000/playlists
		"""
		self.playlists_path = playlists_path
		self.fpl_files = {} # name -> fpl path
		self.playlists = {} # name -> playlist
		# TODO: parse index.dat, fill in fpl_files dict
	def get_playlist(self, name):
		"""Get the playlist with the given name, raises KeyError if it does not exist"""
		if not name in self.playlists:
			if name in self.fpl_files:
				self.playlists[name] = Playlist(name, self.fpl_files[name])
			else:
				raise KeyError("Playlist " + name + " does not exist")
		return self.playlists[name]

"""
consumer provides .foobar/playlists, source music mnt, dest music dir,
max size of dest dir
start with empty list of files to sync
get fpl/name associations from playlist index
allow consumer to get playlists from foobar by name
	e.g. Blah.getPlaylist("Ponies")
	if Ponies was already gotten, return cached playlist
	otherwise, pull out m3u from fpl file and rewrite paths to relative, cache
allow consumer to add to list of files to sync
	e.g. Blah.addMusic(Blah.getPlaylist("Ponies"))
	throw exception if size of added files greater than max size
consumer syncs across playlist files of choosing
	Blah.transferPlaylist("Ponies")
consumer triggers sync of music files
	Blah.transferMusic()
	calls rsync to sync list of files from source to dest

Test: does media player ignore playlist entries that don't exist? yes
Test: m3u8 files - work
Test: non-ascii paths - work
Test: putting playlists in /Playlists - work, add path to scanner

rsync files-from arg doesn't delete files that aren't on the list
have to do it the following way
http://stackoverflow.com/a/1813972

rsync -mrltD --modify-window=1 --progress --delete-excluded --include-from=include-list.txt --exclude=* source/ dest

include-list.txt:
/**/
/file1.txt
/somedir/blah.txt
"""

