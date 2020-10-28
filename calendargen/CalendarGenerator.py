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
from .SVGProcessor import SVGProcessor
from .CalendarDataObject import CalendarDataObject
from .DateRange import DateRanges
from .ImageTools import ImageTools

class CalendarGenerator():
	def __init__(self, args, json_filename):
		self._args = args
		with open(json_filename) as f:
			self._defs = json.load(f)
		self._locales = json.loads(pkgutil.get_data("calendargen.data", "locale.json"))
		self._date_ranges = None
		self._layer_tempfiles = None

	@property
	def render_dpi(self):
		return self._defs["meta"].get("output_dpi", 300)

	@property
	def flatten_output(self):
		return self._defs["meta"].get("flatten_output", True)

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

	@property
	def total_pages(self):
		return len(self._defs["compose"])

	def callback_format_day_box(self, day, style):
		applicable_tags = self._date_ranges.get_tags(day)
		for render_date in self._defs["render_dates"]:
			if render_date["tag"] in applicable_tags:
				if "background_fill" in render_date:
					style["fill"] = render_date["background_fill"]

	def callback_fill_day_color(self, day, style):
		applicable_tags = self._date_ranges.get_tags(day)
		for render_date in self._defs["render_dates"]:
			if render_date["tag"] in applicable_tags:
				if "day_text_fill" in render_date:
					style["fill"] = render_date["day_text_fill"]

	def _create_layer_tempfile(self, **kwargs):
		f = tempfile.NamedTemporaryFile(**kwargs)
		self._layer_tempfiles.append(f)
		return f

	def callback_get_image(self, data_object, image_name, dimensions):
		image_data = data_object[image_name]
		image_filename = image_data["filename"]
		image_dimensions = ImageTools.get_image_geometry(image_filename)
		crop_gravity = image_data.get("gravity", "center")

		image_aspect_ratio = ImageTools.approximate_aspect_ratio(image_dimensions[0], image_dimensions[1])
		placement_aspect_ratio = ImageTools.approximate_float_aspect_ratio(dimensions[0] / dimensions[1])

		if self._args.verbose >= 2:
			print("Image %s: %d x %d pixels (ratio %d:%d); placement dimensions %.3f x %.3f (ratio %d:%d)" % (image_filename, image_dimensions[0], image_dimensions[1], image_aspect_ratio.short.numerator, image_aspect_ratio.short.denominator, dimensions[0], dimensions[1], placement_aspect_ratio.short.numerator, placement_aspect_ratio.short.denominator))
		target_width = round(image_dimensions[1] * placement_aspect_ratio.value)
		target_height = round(image_dimensions[0] / placement_aspect_ratio.value)
		if target_width <= image_dimensions[0]:
			# Cropping height
			target_dimensions = (target_width, image_dimensions[1])
			cropped_ratio = (image_dimensions[0] - target_width) / image_dimensions[0]
			cropped_target = "height"
		else:
			# Cropping width
			target_dimensions = (image_dimensions[0], target_height)
			cropped_ratio = (image_dimensions[1] - target_height) / image_dimensions[1]
			cropped_target = "width"

		if self._args.verbose >= 3:
			print("Cropping %s: %d x %d (gravity %s)" % (image_filename, target_dimensions[0], target_dimensions[1], crop_gravity))
		threshold_percent = 2
		if cropped_ratio > (threshold_percent / 100):
			print("Warning: More than %.1f%% of the image %s of %s are cropped (%.1f%% cropped)." % (threshold_percent, image_filename, cropped_target, cropped_ratio * 100), file = sys.stderr)

		f = self._create_layer_tempfile(prefix = "cal_cropped_image_", suffix = ".jpg")
		crop_cmd = [ "convert", image_filename, "-gravity", crop_gravity, "-crop", "%dx%d+0+0" % (target_dimensions[0], target_dimensions[1]), f.name ]
		subprocess.check_call(crop_cmd)
		return f.name

	def _render_layer(self, page_no, layer_content, layer_filename):
		self._layer_tempfiles = [ ]
		try:
			layer_vars = {
				"year":			self.year,
				"page_no":		page_no,
				"total_pages":	self.total_pages,
			}
			if "vars" in layer_content:
				layer_vars.update(layer_content["vars"])
			svg_data = pkgutil.get_data("calendargen.data", "templates/%s.svg" % (layer_content["template"]))
			data_object = CalendarDataObject(self, layer_vars, self.locale_data)
			processor = SVGProcessor(svg_data, data_object)
			processor.transform()

			with tempfile.NamedTemporaryFile(prefix = "page_%02d_layerdata_" % (page_no), suffix = ".svg") as f:
				processor.write(f.name)
				render_cmd = [ "inkscape", "-d", str(self.render_dpi), "-e", layer_filename, f.name ]
				subprocess.check_call(render_cmd, stdout = subprocess.DEVNULL)
		finally:
			for f in self._layer_tempfiles:
				f.close()

	def _render_page(self, page_no, page_content, page_filename):
		with contextlib.suppress(FileNotFoundError), tempfile.NamedTemporaryFile(prefix = "page_%02d_" % (page_no), suffix = ".png") as page_tempfile:
			for (layer_no, layer_content) in enumerate(page_content):
				if self._args.verbose >= 1:
					print("Rendering page %d of %d, layer %d of %d." % (page_no, self.total_pages, layer_no + 1, len(page_content)))
				with contextlib.suppress(FileNotFoundError), tempfile.NamedTemporaryFile(prefix = "page_%02d_layer_%02d_" % (page_no, layer_no), suffix = ".png") as layer_file:
					self._render_layer(page_no, layer_content, layer_file.name)
					if layer_no == 0:
						# First layer, just move
						shutil.move(layer_file.name, page_tempfile.name)
					else:
						# Compose
						compose_cmd = [ "convert", "-background", "transparent", "-layers", "flatten", page_tempfile.name, layer_file.name, page_tempfile.name ]
						subprocess.check_call(compose_cmd)
			if not self.flatten_output:
				shutil.move(page_tempfile.name, page_filename)
			else:
				flatten_cmd = [ "convert", "-background", "white", "-flatten", "+repage", page_tempfile.name, page_filename ]
				subprocess.check_call(flatten_cmd)

	def _determine_pages(self):
		if len(self._args.page) == 0:
			# By default, render all pages
			return None
		pages = set()
		for (from_page, to_page) in self._args.page:
			pages |= set(range(from_page, to_page + 1))
		return pages

	def _do_render(self):
		applicable_pages = self._determine_pages()
		for (pageno, page_content) in enumerate(self._defs["compose"], 1):
			if (applicable_pages is None) or (pageno in applicable_pages):
				page_filename = self.output_dir + "page_%02d.png" % (pageno)
				self._render_page(pageno, page_content, page_filename)

	def render(self):
		if (self._args.remove) and (os.path.exists(self.output_dir)):
			shutil.rmtree(self.output_dir)
		if (not self._args.force) and (os.path.exists(self.output_dir)):
			print("Refusing to overwrite: %s" % (self.output_dir), file = sys.stderr)
			return
		with contextlib.suppress(FileExistsError):
			os.makedirs(self.output_dir)
		self._date_ranges = DateRanges.parse_all(self._defs["dates"])
		self._do_render()
