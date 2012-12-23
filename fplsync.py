#!/usr/bin/python3

import re
import os
import argparse

class Config:
	"""Holds all config info - must not be altered after it's passed off to a consumer"""
	def __init__(self):
		# see ArgumentParser below - set default values
		self.playlist_source = None
		self.source = None
		self.dest = None
		self.playlists = []
		self.playlist_dest = None
		self.fb2k_source_mapping = None
		self.dry_run = False
	def validate(self):
		# TODO
		pass
	def __repr__(self):
		return "Config {" + ', '.join("%s: %s" % item for item in vars(self).items()) + "}"

class Song:
	"""Describes a song (which is just some file path)"""
	def __init__(self, windows_path):
		"""Create a song with the given windows path
		
		windows_path must be whatever was originally in the fpl file, normalized with abspath
		ex: os.ntpath.abspath("F:\Music\Trucker's Atlas.mp3")
		"""
		self.windows_path = windows_path
	def get_relative_path(self, source, win_prefix=None):
		""""""
	def get_source_path(self, source, falsePrefix=None):
		"""Get the path to the local file
		
		source - the source directory of all songs (e.g. /media/Tassadar/music)
		falsePrefix
		"""

class Playlist:
	"""Holds a list of songs"""
	def __init__(self, name, fpl, song_index):
		"""Create a playlist

		name - the name of the playlist
		fpl - the path to a fpl playlist
		"""
		self.name = name
		self.fpl = fpl
		self.songs = []
		self.song_index = song_index
		with open(self.fpl, 'rb') as infile:
			# FPL entries have file URIs surrounded by null bytes
			paths = re.findall(b'(?<=\x00file://)[^\x00]*(?=\x00)', infile.read())
			# decode the paths as utf-8 and create our songs array
			self.songs = [self.song_index.get_song(path.decode('utf-8')) for path in paths]
	

class SongIndex:
	"""Holds map of windows paths to Songs

	Since the same song can be used many times even among a single playlist, we don't want to create
	a whole bunch of duplicate paths in memory
	"""
	def __init__(self):
		self.songs = {} # windows path -> Song instance
	def get_song(self, windows_path):
		normalized = os.ntpath.abspath(windows_path)
		if not normalized in self.songs:
			self.songs[normalized] = Song(normalized)
		return self.songs[normalized]

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
		self.song_index = SongIndex()
		# TODO: parse index.dat, fill in fpl_files dict
	def get_playlist(self, name):
		"""Get the playlist with the given name, raises KeyError if it does not exist"""
		if not name in self.playlists:
			if name in self.fpl_files:
				self.playlists[name] = Playlist(name, self.fpl_files[name], self.song_index)
			else:
				raise KeyError("Playlist " + name + " does not exist")
		return self.playlists[name]

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Sync foobar2000 playlists and their songs")
	parser.add_argument("playlist-source", help="directory containing foobar2000's FPL files")
	parser.add_argument("source", help="directory where all songs in FPLs are stored under")
	parser.add_argument("dest", help="directory to copy songs to - ALL EXTRANEOUS FILES DELETED")
	parser.add_argument("playlists", nargs='+', help="at least one playlist name, for which the\
	                    contained songs will be copied into DEST")
	parser.add_argument("--playlist-dest", help="if specified, copy PLAYLISTS to this directory as\
	                    m3u8 files that use relative paths to point to their songs in DEST")
	parser.add_argument("--fb2k-source-mapping", help="absolute path to the SOURCE directory that\
	                    foobar2000 uses, if different than SOURCE (e.g. 'F:\Music')")
	parser.add_argument("--dry-run", "-n", action='store_true', help="print what will happen, but\
	                    don't actually copy or delete any files - highly recommended before a real\
						run")
	
	# create a Config instance and set its properties according to command line args
	config = parser.parse_args(namespace=Config())
	config.validate()
	print(config)
	# TODO: actually do stuff


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

