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

import pkgutil
import tempfile
import subprocess
import logging
from .SVGProcessor import SVGProcessor
from .JobServer import Job
from .CmdlineEscape import CmdlineEscape

_log = logging.getLogger(__spec__.name)

class LayoutLayerRenderer():
	def __init__(self, layout_definition, page_no, layer_definition, resolution_dpi, output_file, temp_dir):
		self._layout_definition = layout_definition
		self._page_no = page_no
		self._layer_definition = layer_definition
		self._resolution_dpi = resolution_dpi
		self._output_file = output_file
		self._temp_dir = temp_dir

	def _render_svg(self, svg_processor):
		# Then render the SVG. Note we're already in a job thread, so we can
		# block here.
		with tempfile.NamedTemporaryFile(prefix = "calgen_layer_", suffix = ".svg") as svg_file:
			svg_processor.write(svg_file.name)
			render_cmd = [ "inkscape", "-d", str(self._resolution_dpi), "-o", self._output_file, svg_file.name ]
			_log.debug("Render SVG: %s", CmdlineEscape().cmdline(render_cmd))
			subprocess.check_call(render_cmd, stdout = _log.subproc_target, stderr = _log.subproc_target)

	def render(self, job_server):
		layer_vars = {
			"page_no":		self._page_no,
			"total_pages":	self._layout_definition.total_page_count,
		}
		if "vars" in self._layer_definition:
			layer_vars.update(self._layer_definition["vars"])
		svg_name = "%s_%s.svg" % (self._layout_definition.format, self._layer_definition["template"])
		svg_data = pkgutil.get_data("calendargen.data", "templates/" + svg_name)

		svg_processor = SVGProcessor(svg_data, self._temp_dir)
		image_metadata = self._layout_definition.images
		for (element_name, transform_instructions) in self._layer_definition.get("transform", { }).items():
			svg_processor.handle_instructions(element_name, image_metadata, transform_instructions)

		if len(svg_processor.unused_elements) > 0:
			_log.warning("SVG transformation of %s had %d unhandled elements: %s", svg_name, len(svg_processor.unused_elements), ", ".join(sorted(svg_processor.unused_elements)))

		render_svg_job = Job(self._render_svg, (svg_processor, ), info = "layer_render_svg").depends_on(*svg_processor.dependent_jobs)
		return render_svg_job
