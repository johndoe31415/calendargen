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
import logging
from .BaseAction import BaseAction
from .CalendarDefinition import CalendarDefinition
from .CalendarGenerator import CalendarGenerator

_log = logging.getLogger(__spec__.name)

class ActionCreateLayout(BaseAction):
	def run(self):
		definition = CalendarDefinition(self._args.input_calendar_file)

		for variant in definition.variants:
			generator = CalendarGenerator(definition, variant)
			output_filename = "%s/%s.json" % (self._args.output_dir, variant["name"])
			if (not self._args.force) and os.path.exists(output_filename):
				_log.warning("Not overwriting: %s", output_filename)
				continue
			_log.info("Generating: %s", output_filename)
			generator.generate(output_filename)
