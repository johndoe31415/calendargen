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

import tempfile
from .JobServer import Job
from .Enums import LayerCompositionMethod

class CalendarPageRenderer():
	def __init__(self, page_no, page_definition, output_file, flatten_output):
		self._page_definition = page_definition
		self._output_file = output_file
		self._flatten_output = flatten_output

	def _render_layer_job(self, layer, output_filename):
		print("render", layer, output_filename)

	def _compose_layers(self, lower_filename, upper_filename, composition_method):
		assert(isinstance(composition_method, LayerCompositionMethod))

	def render(self, job_server):
		with tempfile.TemporaryDirectory(prefix = "calendargen_page_") as tmpdir:
			layer_jobs = [ ]
			for (layer_no, layer) in enumerate(self._page_definition, 1):
				output_filename = tmpdir + "/layer_%03d.png" % (layer_no)
				layer_jobs.append(Job(self._render_layer_job, (layer, output_filename)))




			job_server.add_jobs(*layer_jobs)
