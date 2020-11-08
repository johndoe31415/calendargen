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

import os
import contextlib
from .BaseCommand import BaseCommand
from .ImagePool import ImagePool

class ScanPoolCommand(BaseCommand):
	def run(self):
		pool = ImagePool.create_cached_pool(self._args.cache_file, self._args.image_directory)

		if self._args.verbose >= 1:
			for entry in pool:
				print("%s: p=%.3f groups=%s" % (entry.filename, entry.probability, ", ".join(sorted(entry.groups))))

		if self._args.link_groups:
			for (group_name, group_members) in pool.groups:
				output_dir = self._args.link_groups + "/" + group_name + "/"
				with contextlib.suppress(FileExistsError):
					os.makedirs(output_dir)
				for (member_id, member) in enumerate(sorted(group_members)):
					with contextlib.suppress(FileExistsError):
						os.symlink(member, output_dir + str(member_id) + ".jpg")
