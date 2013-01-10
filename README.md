fplsync
=======

fplsync is a python script/module that allows you to synchronize
foobar2000's FPL playlists and their contents to some other directory,
such as the SD card on an Android phone.

Features
--------
* Runs without opening foobar2000
* Works fine with large libraries (tested with a 26k track library)
* Works fine with autoplaylists, allowing you to take advantage of
  foobar2000's powerful query syntax
* Basic CLI that allows you to sync music from given playlists until
  space runs out
* Specify a maximum amount of data to copy and/or a minimum amount of
  free space to keep
* Save playlists as m3u8 files at the destination device, with relative
  file paths pointing to music in the destination directory
* Python module to enable more complex logic (e.g. copy all songs from
  playlist A, copy 50 random songs from playlist B if it's a Tuesday,
  copy the first 10 songs from Playlist C, then fill any remaining space
  with random tracks)
* Preserves directory structure from the source directory

Limitations
--------
* Pretty sure it won't work on Windows (I got lazy at one point)
* Based on reverse-engineering of the binary format that foobar2000
  uses, which is purposefully undocumented and unstable
* Not tested with MTP/PTP protocols - I'm just plugging my SD card into
  my machine.  I assume connecting your phone as UMS will work.
* Python module is very bare bones and untested at the moment

See the [GitHub Issues](https://github.com/fracture91/fplsync/issues)

Requirements
--------
* foobar2000 1.1.13, presumably running under Wine, though all that's
  really needed is its "playlists" directory
* rsync (I have 3.0.9)
* Python 3.2
* du (I have 8.13)

Usage
--------
./fplsync.py --help

I *highly* recommend using the --dry-run flag before syncing for real.

See [my dotfiles]
(https://github.com/fracture91/dotfiles/blob/master/syncmusic.py)
for an example script that uses fplsync

Note that foobar2000 doesn't normally write its playlist files to disk
while it's running.  You can force a write by shift-clicking the
File menu > Save configuration.
