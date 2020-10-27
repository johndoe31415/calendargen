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

import json
import os
import contextlib
import sys
import tempfile
import shutil
import pkgutil
import subprocess
from .SVGProcessor import SVGProcessor, CalendarDataObject

class CalendarGenerator():
	def __init__(self, args, json_filename):
		self._args = args
		with open(json_filename) as f:
			self._defs = json.load(f)
		self._locales = json.loads(pkgutil.get_data("calendargen.data", "locale.json"))

	@property
	def render_dpi(self):
		return self._defs["meta"].get("output_dpi", 300)

	@property
	def calendar_name(self):
		return self._defs["meta"].get("name", "unnamed_calendar")

	@property
	def locale(self):
		return self._defs["meta"].get("locale", "en")

	@property
	def locale_data(self):
		return self._locales[self.locale]

	@property
	def year(self):
		return self._defs["meta"]["year"]

	@property
	def output_dir(self):
		return self._args.output_dir + "/" + self.calendar_name + "/"

	def _render_layer(self, page_no, layer_content, layer_filename):
		layer_vars = {
			"year":		self.year,
		}
		if "vars" in layer_content:
			layer_vars.update(layer_content["vars"])
		svg_data = pkgutil.get_data("calendargen.data", "templates/%s.svg" % (layer_content["template"]))
		data_object = CalendarDataObject(layer_vars, self.locale_data)
		processor = SVGProcessor(svg_data, data_object)
		processor.transform()

		with tempfile.NamedTemporaryFile(prefix = "page_%02d_layerdata_" % (page_no), suffix = ".svg") as f:
			processor.write(f.name)
			render_cmd = [ "inkscape", "-d", str(self.render_dpi), "-e", layer_filename, f.name ]
			subprocess.check_call(render_cmd)

	def _render_page(self, page_no, page_content, page_filename):
		with contextlib.suppress(FileNotFoundError), tempfile.NamedTemporaryFile(prefix = "page_%02d_" % (page_no), suffix = ".png") as page_tempfile:
			for (layer_no, layer_content) in enumerate(page_content):
				with contextlib.suppress(FileNotFoundError), tempfile.NamedTemporaryFile(prefix = "page_%02d_layer_%02d_" % (page_no, layer_no), suffix = ".png") as layer_file:
					self._render_layer(page_no, layer_content, layer_file.name)
					if layer_no == 0:
						# First layer, just move
						shutil.move(layer_file.name, page_tempfile.name)
					else:
						# Compose
						compose_cmd = [ "convert", "-background", "transparent", "-layers", "flatten", page_tempfile.name, layer_file.name, page_tempfile.name ]
						subprocess.check_call(compose_cmd)
			shutil.move(page_tempfile.name, page_filename)

	def _do_render(self):
		for (pageno, page_content) in enumerate(self._defs["compose"], 1):
			page_filename = self.output_dir + "page_%02d.png" % (pageno)
			self._render_page(pageno, page_content, page_filename)

	def render(self):
		if (not self._args.force) and (os.path.exists(self.output_dir)):
			print("Refusing to overwrite: %s" % (self.output_dir), file = sys.stderr)
			return
		with contextlib.suppress(FileExistsError):
			os.makedirs(self.output_dir)
		self._do_render()
