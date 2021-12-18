#	calendargen - Photo calendar generator
#	Copyright (C) 2020-2021 Johannes Bauer
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
import json
import logging
import contextlib
from .BaseAction import BaseAction
from .CalendarDefinition import CalendarDefinition
from .CalendarGenerator import CalendarGenerator

_log = logging.getLogger(__spec__.name)

class ActionCreateLayout(BaseAction):
	def run(self):
		definition = CalendarDefinition(self._args.input_calendar_file)
		if len(self._args.only_variant) == 0:
			only_variants = set(definition.variant_names)
		else:
			only_variants = set(self._args.only_variant)

		with contextlib.suppress(FileExistsError):
			os.makedirs(self._args.output_dir)

		for variant in definition.variants:
			if variant["name"] not in only_variants:
				continue

			output_filename = "%s/%s.json" % (self._args.output_dir, variant["name"])
			if (not self._args.force) and os.path.exists(output_filename):
				_log.warning("Not overwriting: %s", output_filename)
				continue

			if os.path.isfile(output_filename) and (not self._args.reassign_images):
				with open(output_filename) as f:
					previous_data = json.load(f)
					previous_image_data = { key: value["filename"] for (key, value) in previous_data["images"].items() if value["filename"] is not None }
			else:
				previous_image_data = None

			if previous_image_data is not None:
				# Ensure those files which are already placed are part of the pool.
				placed_filenames = previous_image_data.values()
				definition.image_pool.scan_files(placed_filenames)

			_log.info("Generating: %s", output_filename)
			generator = CalendarGenerator(definition, variant, previous_image_data = previous_image_data)
			layout = generator.generate()
			with open(output_filename, "w") as f:
				json.dump(layout, f, indent = 4)
				f.write("\n")
			if not self._args.no_create_symlinks:
				generator.create_image_symlinks(self._args.output_dir)
