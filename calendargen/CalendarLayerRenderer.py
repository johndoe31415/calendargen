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

import sys
import pkgutil
import tempfile
import subprocess
from .SVGProcessor import SVGProcessor

class CalendarLayerRenderer():
	def __init__(self, calendar_definition, page_no, layer_definition, resolution_dpi, output_file):
		self._calendar_definition = calendar_definition
		self._page_no = page_no
		self._layer_definition = layer_definition
		self._resolution_dpi = resolution_dpi
		self._output_file = output_file

	def render(self):
		layer_vars = {
			"page_no":		self._page_no,
			"total_pages":	self._calendar_definition.total_page_count,
		}
		if "vars" in self._layer_definition:
			layer_vars.update(self._layer_definition["vars"])
		svg_name = "%s_%s.svg" % (self._calendar_definition.format, self._layer_definition["template"])
		svg_data = pkgutil.get_data("calendargen.data", "templates/" + svg_name)

		svg_processor = SVGProcessor(svg_data)
		for (element_name, transform_instructions) in self._layer_definition.get("transform", { }).items():
			svg_processor.handle_instructions(element_name, transform_instructions)

		if len(svg_processor.unused_elements) > 0:
			print("Warning: SVG transformation of %s had %d unhandled elements: %s" % (svg_name, len(svg_processor.unused_elements), ", ".join(sorted(svg_processor.unused_elements))), file = sys.stderr)

		with tempfile.NamedTemporaryFile(prefix = "calgen_layer_", suffix = ".svg") as svg_file:
			svg_processor.write(svg_file.name)
			subprocess.check_call([ "inkscape", "-d", str(self._resolution_dpi), "-o", self._output_file, svg_file.name ])
			input("DONE " +self._output_file)
