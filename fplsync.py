#!/usr/bin/python3

import math
import re
import os
import sys
import ntpath
import argparse
import tempfile
import shutil
import subprocess


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
		self.max_size = None
	
	def validate(self):
		dirprops = ["playlist_source", "source", "dest"]
		if self.playlist_dest is not None:
			dirprops.append("playlist_dest")
		for prop in dirprops:
			value = getattr(self, prop)
			if not os.path.isdir(value):
				raise IOError(prop + "=" + value + " is not a directory")
		if self.fb2k_source_mapping is not None:
			self.fb2k_source_mapping = ntpath.abspath(self.fb2k_source_mapping)
			if not self.fb2k_source_mapping.endswith(ntpath.sep):
				self.fb2k_source_mapping = self.fb2k_source_mapping + ntpath.sep
		if not isinstance(self.dry_run, bool):
			raise TypeError("dry_run must be a bool")
		if self.max_size is not None:
			if not isinstance(self.max_size, int):
				self.max_size = self.size_str_to_bytes(self.max_size)
			if self.max_size < 1024 and self.max_size > 0:
				raise Exception("max_size is less than a kibibyte - probably a mistake")
	
	def size_str_to_bytes(self, string):
		"""Take in a size argument (20M, 1.5T, etc.) and return number of bytes (IEC)"""
		if re.match('\d', string[-1]) is None:
			units = ['k', 'm', 'g', 't']
			number = float(string[:-1])
			power = 10 * (units.index(string[-1].lower()) + 1)
			return int(number * math.pow(2, power))
		return int(string)
	
	def __repr__(self):
		return "Config {" + ', '.join("%s: %s" % item for item in vars(self).items()) + "}"


class Song:
	"""Describes a song (which is just some file path)"""
	
	def __init__(self, windows_path, config):
		"""Create a song with the given windows path
		
		windows_path must be whatever was originally in the fpl file, normalized with abspath
		ex: ntpath.abspath("F:\Music\Trucker's Atlas.mp3")
		"""
		self.windows_path = windows_path
		self.config = config
		self.cached_size = None
		
		# the path to the song in the source directory
		self.source_path = self.windows_path
		if config.fb2k_source_mapping is not None:
			# need to transform e.g. F:\Music\artist\song.mp3 to /media/A/Music/artist/song.mp3
			if not self.source_path.startswith(config.fb2k_source_mapping):
				raise Exception("Song " + self.source_path + " does not use source mapping")
			relpath = ntpath.relpath(self.source_path, start=config.fb2k_source_mapping)
			relpath = relpath.replace(ntpath.sep, os.path.sep)
			self.source_path = os.path.join(self.config.source, relpath)
		elif not self.source_path.startswith(self.config.source):
			raise Exception("Song " + self.source_path + " is not within source")
		
		# the path of the song relative to the source directory
		self.relative_path = os.path.relpath(self.source_path, start=self.config.source)
		dest_path = os.path.join(self.config.dest, self.relative_path)
		# the path of the song after copied to dest, relative to playlist_dest
		self.playlist_path = os.path.relpath(dest_path, start=self.config.playlist_dest)
		
	def get_size(self):
		"""Return the size of the song in its source directory"""
		if self.cached_size is None:
			self.cached_size = os.path.getsize(self.source_path)
		return self.cached_size

	def __repr__(self):
		return "Song at " + self.windows_path


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
		
		print("Parsing playlist " + self.name + "...")
		with open(self.fpl, 'rb') as infile:
			# FPL entries have file URIs surrounded by null bytes
			paths = re.findall(b'(?<=\x00file://)[^\x00]*(?=\x00)', infile.read())
			# decode the paths as utf-8 and create our songs array
			self.songs = [self.song_index.get_song(path.decode('utf-8')) for path in paths]
	
	def write(self, path):
		"""Write this playlist as an m3u8 to path/name.m3u8
		
		Acts like it is being written to config.playlist_dest with relative paths pointing to
		config.dest.
		"""
		if not os.path.isdir(path):
			raise Exception("path must point to a directory")
		print("Writing playlist " + self.name)
		full_path = os.path.join(path, self.name + ".m3u8")
		with open(full_path, "w") as outfile:
			for song in self.songs:
				print(song.playlist_path, file=outfile)
		return full_path

	def __iter__(self):
		return iter(self.songs)

	def __repr__(self):
		return "Playlist '" + self.name + "' with " + str(len(self.songs)) + " songs"
	

class SongIndex:
	"""Holds map of windows paths to Songs

	Since the same song can be used many times even among a single playlist, we don't want to create
	a whole bunch of duplicate paths in memory
	"""
	
	def __init__(self, config):
		self.songs = {} # windows path -> Song instance
		self.config = config
	
	def get_song(self, windows_path):
		normalized = ntpath.abspath(windows_path)
		if not normalized in self.songs:
			self.songs[normalized] = Song(normalized, self.config)
		return self.songs[normalized]


class PlaylistIndex:
	"""Responsible for getting named playlists from fb2k"""
	
	def __init__(self, config):
		"""Construct a PlaylistIndex

		Reads playlist name/path associations from index.dat,
		which is found in the config.playlist_source directory along with fpl files.
		config.playlist_source should be something like ~/.foobar2000/playlists
		"""
		self.config = config
		self.fpl_files = {} # name -> fpl path
		self.playlists = {} # name -> playlist
		self.song_index = SongIndex(self.config)
		
		# parse out the name/path associations
		indexpath = os.path.join(self.config.playlist_source, "index.dat")
		with open(indexpath, 'rb') as infile:
			data = infile.read()
			# entries have two null bytes, then fpl_path,
			# then a 16-bit int containing the length of the playlist name,
			# two null bytes, then the playlist name
			# re.DOTALL is important, otherwise \x10 doesn't match the dot
			fpl_re = re.compile(b'(?<=\x00\x00)(\d+\.fpl)(..)(\x00\x00)', re.DOTALL)
			lastpos = 0
			
			while True: # keep finding matches for the above pattern until there are no more
				result = fpl_re.search(data, lastpos)
				if result is None:
					break
				fpl_path = result.group(1).decode('utf-8')
				name_length = int.from_bytes(result.group(2), sys.byteorder)
				if name_length < 1:
					raise Exception("Error reading index.dat: name length must be > 0")
				# update the point that the next search will start from - the end of the name
				lastpos = result.end() + name_length
				if lastpos > len(data) - 1:
					raise Exception("Error reading index.dat: not enough data for name")
				name = data[result.end():lastpos].decode('utf-8')
				self.fpl_files[name] = os.path.join(self.config.playlist_source, fpl_path)
			print(self.fpl_files)

	def get_playlist(self, name):
		"""Get the playlist with the given name, raises KeyError if it does not exist"""
		if not name in self.playlists:
			if name in self.fpl_files:
				self.playlists[name] = Playlist(name, self.fpl_files[name], self.song_index)
			else:
				raise KeyError("Playlist " + name + " does not exist")
		return self.playlists[name]


class OutOfSpaceException(Exception):
	"""Raised when we run out of space on the device"""
	
	def __init__(self, failed_object, failed_size):
		"""failed_object is the object that was too big to be transferred (Playlist, Song)
		failed_size is the size of that object in bytes
		"""
		self.failed_object = failed_object
		self.failed_size = failed_size
		super().__init__(str(self.failed_object) + " was too big at " + str(self.failed_size)
		                 + " bytes")


class SyncDirector:
	"""Responsible for actually moving files around

	Can add playlists to transfer and songs to transfer, then trigger the transfer
	Both operations will throw an exception upon adding if source files are too big
	"""
	
	def __init__(self, config):
		config.validate()
		self.config = config
		self.is_gathering = True # gathering files, transfer hasn't begun
		self.songs = set() # set of all Songs to transfer
		# create a temporary directory to hold playlists and rsync include file
		self.temp_dir = tempfile.mkdtemp(prefix="fplsync")
		print("Created temp directory at " + self.temp_dir)
		if self.config.playlist_dest is not None:
			self.playlist_dir = os.path.join(self.temp_dir, "playlists")
			os.mkdir(self.playlist_dir)
		self.is_playlist_added = False
		self.cumulative_size = 0
		self.find_max_size()
	
	def find_max_size(self):
		# things get very unportable here...
		stat = os.statvfs(self.config.dest)
		free = stat.f_bavail * stat.f_frsize # free space on dest disk
		# anything that doesn't belong in dest is going to be deleted, so we can consider it free
		space_dirs = [self.config.dest]
		if self.config.playlist_dest is not None:
			space_dirs.append(self.config.playlist_dest)
		# universal_newlines needed for string output rather than bytes
		output = subprocess.check_output(["du", "-csb"] + space_dirs, universal_newlines=True)
		free += int(re.search('(\d+)\s+total', output).group(1))
		self.max_size = free
		if self.config.max_size is not None:
			if self.config.max_size < 0:
				self.max_size = free + self.config.max_size
			else:
				self.max_size = min(free, self.config.max_size)
		if self.max_size < 1024:
			raise Exception("Not enough free space")
		print("SyncDirector.max_size: " + str(self.max_size))
	
	def add_playlist(self, playlist):
		"""Add a playlist, which will be transferred to playlist_dest as an m3u8 file.
		
		Paths in the playlist will be relative paths pointing to files in dest.
		Raises an OutOfSpaceException if the playlist file would be too big.
		"""
		if not self.is_gathering:
			raise Exception("Cannot add playlist after transfer begins")
		if self.config.playlist_dest is None:
			raise Exception("Cannot add playlist if playlist_dest was not provided")
		# write to our temp playlist directory
		path = playlist.write(self.playlist_dir)
		# make sure adding it doesn't put us over the limit
		size = os.path.getsize(path)
		if self.cumulative_size + size > self.max_size:
			os.remove(path)
			raise OutOfSpaceException(playlist, size)
		else:
			self.cumulative_size += size
		self.is_playlist_added = True
	
	def add_songs(self, songs):
		"""Add the given songs, which will be transferred to dest.
		
		songs must be an iterable of Song instances (like a Playlist), or a single Song instance.
		Adds songs until there wouldn't be enough space to fit one.
		Once space runs out, OutOfSpaceException is raised, but the successfully added songs remain.
		"""
		if not self.is_gathering:
			raise Exception("Cannot add songs after transfer begins")
		if isinstance(songs, Song):
			songs = [songs]
		for song in songs:
			if song not in self.songs: # don't double-count any songs!
				size = song.get_size()
				if self.cumulative_size + size > self.max_size:
					raise OutOfSpaceException(song, size)
				else:
					self.songs.add(song)
					self.cumulative_size += size
	
	def transfer(self):
		self.is_gathering = False
		if self.is_playlist_added:
			# TODO: rsync tmp/playlists
			pass
		if len(self.songs) > 0:
			# TODO: make include file, rsync source and dest
			pass
		# clean up temporary directory we made
		if self.config.dont_delete_temp:
			print("Skipping temp directory deletion!")
			pass
		else:
			shutil.rmtree(self.temp_dir)
			print("Deleted temp directory at " + self.temp_dir)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Sync foobar2000 playlists and their songs")
	parser.add_argument("playlist_source", metavar="playlist-source",
	                    help="directory containing foobar2000's FPL files")
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
	parser.add_argument("--max-size", help="maximum number of bytes of space to take up among songs\
	                    and playlists.  Always limited by the free space on the device.  If\
	                    negative, leave that much space free.  Can use units ('1.5T', '-200M').\
	                    Units are short for base 2 units (KiB, MiB, ...).")
	
	# create a Config instance and set its properties according to command line args
	config = parser.parse_args(namespace=Config())
	config.dont_delete_temp = True

	director = SyncDirector(config)
	index = PlaylistIndex(config)
	print(config)
	for name in config.playlists:
		try:
			director.add_playlist(index.get_playlist(name))
		except OutOfSpaceException as e:
			print(e)
			break
	for name in config.playlists:
		try:
			director.add_songs(index.get_playlist(name))
		except OutOfSpaceException as e:
			print(e)
			break
	director.transfer()


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

