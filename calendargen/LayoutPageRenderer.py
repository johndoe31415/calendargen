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

import subprocess
import logging
from .JobServer import Job
from .LayoutLayerRenderer import LayoutLayerRenderer
from .Enums import LayerCompositionMethod
from .Exceptions import IllegalLayoutDefinitionException
from .CmdlineEscape import CmdlineEscape

_log = logging.getLogger(__spec__.name)

class LayoutPageRenderer():
	def __init__(self, calendar_definition, page_no, page_definition, resolution_dpi, output_file, flatten_output, temp_dir):
		self._calendar_definition = calendar_definition
		self._page_no = page_no
		self._page_definition = page_definition
		self._resolution_dpi = resolution_dpi
		self._output_file = output_file
		self._flatten_output = flatten_output
		self._temp_dir = temp_dir
		if self.layer_count == 0:
			raise IllegalLayoutDefinitionException("No layers defined for page.")

	@property
	def layer_count(self):
		return len(self._page_definition)

	def _layer_filename(self, base_dir, layer_no):
		output_filename = base_dir + "/layer_%03d.png" % (layer_no)
		return output_filename

	def _render_layer_job(self, layer_definition, output_filename, job_server):
		layer_renderer = LayoutLayerRenderer(self._calendar_definition, self._page_no, layer_definition, self._resolution_dpi, output_filename, temp_dir = self._temp_dir)
		layer_renderer.render(job_server)

	def _compose_layers(self, lower_filename, upper_filename, composition_method):
		assert(isinstance(composition_method, LayerCompositionMethod))
		if composition_method == LayerCompositionMethod.AlphaCompose:
			conversion_cmd = [ "convert", "-background", "transparent", "-layers", "flatten", lower_filename, upper_filename, upper_filename ]
		elif composition_method == LayerCompositionMethod.InvertedCompose:
			conversion_cmd = [ "convert" ]
			conversion_cmd += [ lower_filename, "+write", "mpr:lower" ]
			conversion_cmd += [ "(", upper_filename, "-alpha", "extract", "+write", "mpr:upper", ")" ]
			conversion_cmd += [ "-compose", "multiply", "-composite", "-negate", "mpr:upper" ]
			conversion_cmd += [ "-compose", "multiply", "-composite", "mpr:lower", "+swap", "mpr:upper" ]
			conversion_cmd += [ "-compose", "over", "-composite" ]
			conversion_cmd += [ upper_filename ]
		_log.debug("Compose layers using %s: %s", composition_method.name, CmdlineEscape().cmdline(conversion_cmd))
		subprocess.check_call(conversion_cmd)

	def _final_conversion(self, input_filename):
		conversion_cmd = [ "convert" ]
		if self._flatten_output:
			conversion_cmd += [ "-background", "white", "-flatten", "+repage" ]
		else:
			conversion_cmd += [ "-background", "transparent" ]
		conversion_cmd += [ input_filename ]
		conversion_cmd += [ self._output_file ]
		_log.debug("Final conversion: %s", CmdlineEscape().cmdline(conversion_cmd))
		subprocess.check_call(conversion_cmd)

	def render(self, job_server):
		layer_jobs = [ ]
		for (layer_no, layer) in enumerate(self._page_definition, 1):
			output_filename = self._layer_filename(self._temp_dir, layer_no)
			layer_jobs.append(Job(self._render_layer_job, (layer, output_filename, job_server), name = "layer%d" % (layer_no)))

		last_merge_job = layer_jobs[0]
		if self.layer_count > 1:
			# Need to always merge two layers, then
			for (lower_layer_no, layer) in enumerate(self._page_definition[:-1], 1):
				next_render_job = layer_jobs[lower_layer_no]
				upper_layer_no = lower_layer_no + 1
				upper_layer = self._page_definition[lower_layer_no]
				lower_filename = self._layer_filename(self._temp_dir, lower_layer_no)
				upper_filename = self._layer_filename(self._temp_dir, upper_layer_no)
				composition_method = LayerCompositionMethod(upper_layer.get("compose", "compose"))
				last_merge_job = Job(self._compose_layers, (lower_filename, upper_filename, composition_method), name = "merge%d" % (lower_layer_no)).depends_on(last_merge_job, next_render_job)

		last_layer_filename = self._layer_filename(self._temp_dir, self.layer_count)
		finalization_job = Job(self._final_conversion, (last_layer_filename, ), name = "final").depends_on(last_merge_job)

		job_server.add_jobs(*layer_jobs)
