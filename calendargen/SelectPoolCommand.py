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
import sys
import contextlib
from .BaseCommand import BaseCommand
from .ImagePool import ImagePool, ImagePoolSelection, ImageSelectionException

class SelectPoolCommand(BaseCommand):
	def run(self):
		pool = ImagePool.create_cached_pool(self._args.cache_file, self._args.image_directory)
		chosen_selection = None
		for run_no in range(1, self._args.runs + 1):
			try:
				selection = ImagePoolSelection(pool, remove_groups = not self._args.no_remove_groups, remove_timewindow_secs = self._args.remove_time_window)
				selection = selection.select(image_count = self._args.image_count, set_name = self._args.set_name)
			except ImageSelectionException as e:
				if self._args.verbose >= 2:
					print("Attempt of selection %d / %d failed: %s" % (run_no, self._args.runs, str(e)), file = sys.stderr)
				continue
			if (chosen_selection is None) or (selection.min_timedelta > chosen_selection.min_timedelta):
				chosen_selection = selection

		if chosen_selection is None:
			print("No selections could be made with the critera you specified.", file = sys.stderr)
			sys.exit(1)

		if self._args.link_images is not None:
			for (image_no, image) in enumerate(chosen_selection.images, 1):
				output_filename = "%s/%02d.jpg" % (self._args.link_images, image_no)
				if os.path.islink(output_filename):
					os.unlink(output_filename)
				os.symlink(image.filename, output_filename)
