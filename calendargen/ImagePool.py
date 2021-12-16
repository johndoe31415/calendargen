#	calendargen - Photo calendar generator
#	Copyright (C) 2021-2021 Johannes Bauer
#
#	This file is part of calendargen.
#
#	calendargen is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	calendargen is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with calendargen; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import os
import time
import json
from .ImageTools import ImageTools
from .JobServer import JobServer, Job

class ImagePool():
	_CACHEFILE = os.path.expanduser("~/.cache/calendargen.json")
	_SCAN_VERSION = 0

	def __init__(self, directories):
		self._entries = { }
		self._scan_directories(directories)

	@staticmethod
	def _get_mtime(filename):
		try:
			return round(os.stat(filename).st_mtime * 1000000)
		except FileNotFoundError:
			return None

	def _get_mtimes(self, filenames):
		return [ self._get_mtime(filename) for filename in filenames ]

	def _scan_metadata(self, filename, mtimes, cache_data):
		print(filename)
		new_entry = {
			"mtimes":	mtimes,
			"version":	self._SCAN_VERSION,
			"geometry":	ImageTools.get_image_geometry(filename)
		}
		cache_data[filename] = new_entry
		self._entries[filename] = new_entry

	def _scan_file(self, filename, cache_data, job_server):
		all_dependent_files = [ filename, os.path.expanduser("~/.local/share/geeqie/metadata") + filename + ".gq.xmp" ]
		mtimes = self._get_mtimes(all_dependent_files)
		cached_entry = cache_data.get(filename)
		if cached_entry is not None:
			if (cached_entry["mtimes"] == mtimes) and (cached_entry["version"] == self._SCAN_VERSION):
				# Still accurate, use it.
				self._entries[filename] = cached_entry
				return

		# Either not cached or
		job_server.add_jobs(Job(self._scan_metadata, (filename, mtimes, cache_data)))

	def _scan_directory(self, dirname, cache_data, job_server):
		for (walk_dir, subdirs, files) in os.walk(dirname):
			for filename in files:
				(base, ext) = os.path.splitext(filename)
				if ext.lower() not in [ ".jpg", ".jpeg" ]:
					continue
				full_filename = os.path.realpath(walk_dir + "/" + filename)
				self._scan_file(full_filename, cache_data, job_server)

	def _scan_directories(self, directories):
		try:
			with open(self._CACHEFILE) as f:
				cache_data = json.load(f)
		except FileNotFoundError:
			cache_data = { }
		with JobServer() as job_server:
			for directory in directories:
				self._scan_directory(directory, cache_data, job_server)
		with open(self._CACHEFILE, "w") as f:
			json.dump(cache_data, f)

if __name__ == "__main__":
	ip = ImagePool([ "pool2021" ])
