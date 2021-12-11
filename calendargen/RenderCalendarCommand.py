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
import shutil
from .BaseCommand import BaseCommand
from .CalendarDefinition import CalendarDefinition
from .CalendarPageRenderer import CalendarPageRenderer
from .JobServer import JobServer

class RenderCalendarCommand(BaseCommand):
	def run(self):
		with JobServer(verbose = self._args.verbose >= 1) as job_server:
			for input_filename in self._args.input_file:
				calendar_definition = CalendarDefinition(input_filename)
				output_dir = self._args.output_dir + "/" + calendar_definition.name + "/"
				if (not self._args.force) and os.path.exists(output_dir):
					print("Refusing to overwrite output directory: %s" % (output_dir))
					continue
				if self._args.remove_output_dir:
					shutil.rmtree(output_dir)

				for (page_no, page_definition) in enumerate(calendar_definition.pages, 1):
					output_file = "%s%s_%03d.%s" % (output_dir, calendar_definition.name, page_no, self._args.output_format)
					page_renderer = CalendarPageRenderer(page_no = page_no, page_definition = page_definition, output_file = output_file, flatten_output = self._args.flatten_output)
					page_renderer.render(job_server)
