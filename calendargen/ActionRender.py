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
import tempfile
import uuid
import contextlib
from .BaseAction import BaseAction
from .LayoutDefinition import LayoutDefinition
from .LayoutPageRenderer import LayoutPageRenderer
from .JobServer import JobServer

class ActionRender(BaseAction):
	def run(self):
		if len(self._args.page) == 0:
			included_pages = None
		else:
			included_pages = set()
			for (from_page, to_page) in self._args.page:
				for page_no in range(from_page, to_page + 1):
					included_pages.add(page_no)

		with tempfile.TemporaryDirectory(prefix = "calendargen_") as temp_dir:
			with JobServer(write_graph_file = self._args.job_graph) as job_server:
				for input_filename in self._args.input_layout_file:
					calendar_definition = LayoutDefinition(input_filename)
					output_dir = self._args.output_dir + "/" + calendar_definition.name + "/"
					if (not self._args.force) and os.path.exists(output_dir):
						print("Refusing to overwrite output directory: %s" % (output_dir))
						continue
					with contextlib.suppress(FileExistsError):
						os.makedirs(output_dir)
					if self._args.remove_output_dir:
						shutil.rmtree(output_dir)

					for (page_no, page_definition) in enumerate(calendar_definition.pages, 1):
						if (included_pages is None) or (page_no in included_pages):
							page_temp_dir = temp_dir + "/" + str(uuid.uuid4())
							os.makedirs(page_temp_dir)
							output_file = "%s%s_%03d.%s" % (output_dir, calendar_definition.name, page_no, self._args.output_format)
							page_renderer = LayoutPageRenderer(calendar_definition = calendar_definition, page_no = page_no, page_definition = page_definition, resolution_dpi = self._args.resolution_dpi, output_file = output_file, flatten_output = not self._args.no_flatten_output, temp_dir = page_temp_dir)
							page_renderer.render(job_server)
			if self._args.wait_keypress:
				input("Waiting for keypress before returning...")
