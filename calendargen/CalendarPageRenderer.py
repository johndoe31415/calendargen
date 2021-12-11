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
import subprocess
from .JobServer import Job
from .CalendarLayerRenderer import CalendarLayerRenderer
from .Enums import LayerCompositionMethod
from .Exceptions import IllegalCalendarDefinitionException

class CalendarPageRenderer():
	def __init__(self, calendar_definition, page_no, page_definition, output_file, flatten_output):
		self._calendar_definition = calendar_definition
		self._page_no = page_no
		self._page_definition = page_definition
		self._output_file = output_file
		self._flatten_output = flatten_output
		if self.layer_count == 0:
			raise IllegalCalendarDefinitionException("No layers defined for page.")

	@property
	def layer_count(self):
		return len(self._page_definition)

	def _layer_filename(self, base_dir, layer_no):
		output_filename = base_dir + "/layer_%03d.png" % (layer_no)
		return output_filename

	def _render_layer_job(self, layer_definition, output_filename):
		layer_renderer = CalendarLayerRenderer(self._calendar_definition, self._page_no, layer_definition, output_filename)
		layer_renderer.render()

	def _compose_layers(self, lower_filename, upper_filename, composition_method):
		assert(isinstance(composition_method, LayerCompositionMethod))
		if composition_method == LayerCompositionMethod.AlphaCompose:
			conversion_cmd = [ "convert", "-background", "transparent", "-layers", "flatten", lower_filename, upper_filename, upper_filename ]
		elif composition_method == LayerCompositionMethod.InvertedCompose:
			print("NOT IMPLEMENTED")
			conversion_cmd = [ "convert", "-background", "transparent", "-layers", "flatten", lower_filename, upper_filename, upper_filename ]
		subprocess.check_call(conversion_cmd)

	def _final_conversion(self, input_filename):
		conversion_cmd = [ "convert" ]
		conversion_cmd += [ input_filename ]
		if self._flatten_output:
			conversion_cmd += [ "-background", "white", "-flatten", "+repage" ]
		conversion_cmd += [ self._output_file ]
		subprocess.check_call(conversion_cmd)

	def render(self, job_server):
		with tempfile.TemporaryDirectory(prefix = "calendargen_page_") as tmpdir:
			layer_jobs = [ ]
			for (layer_no, layer) in enumerate(self._page_definition, 1):
				output_filename = self._layer_filename(tmpdir, layer_no)
				layer_jobs.append(Job(self._render_layer_job, (layer, output_filename)))

			last_merge_job = layer_jobs[0]
			if self.layer_count > 1:
				# Need to always merge two layers, then
				for (lower_layer_no, layer) in enumerate(self._page_definition[:-1], 1):
					next_merge_job = layer_jobs[lower_layer_no]
					upper_layer_no = lower_layer_no + 1
					lower_filename = self._layer_filename(tmpdir, lower_layer_no)
					upper_filename = self._layer_filename(tmpdir, upper_layer_no)
					composition_method = LayerCompositionMethod(layer.get("compose", "compose"))
					last_merge_job = Job(self._compose_layers, (lower_filename, upper_filename, composition_method)).depends_on(last_merge_job)

			last_layer_filename = self._layer_filename(tmpdir, self.layer_count)
			finalization_job = Job(self._final_conversion, (last_layer_filename, )).depends_on(last_merge_job)

			job_server.add_jobs(*layer_jobs)
