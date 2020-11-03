#	calendargen - Photo calendar generator
#	Copyright (C) 2020-2020 Johannes Bauer
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

from .BaseCommand import BaseCommand
from .ImagePool import ImagePool

class ScanPoolCommand(BaseCommand):
	def run(self):
		try:
			pool = ImagePool.load_cache_file(self._args.cache_file)
		except FileNotFoundError:
			pool = ImagePool()
		for dirname in self._args.image_directory:
			pool.add_directory(dirname)
		pool.save_cache_file(self._args.cache_file)

		if self._args.verbose >= 1:
			for entry in pool:
				print("%s: p=%.3f groups=%s" % (entry.filename, entry.probability, ", ".join(sorted(entry.groups))))
