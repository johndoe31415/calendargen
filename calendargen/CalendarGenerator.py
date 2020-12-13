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
from .DateRange import DateRanges, Birthdays
from .ImageTools import ImageTools

class CalendarGenerator():
	def __init__(self, args, json_filename):
		self._args = args
		with open(json_filename) as f:
			self._defs = json.load(f)
		self._locales = json.loads(pkgutil.get_data("calendargen.data", "locale.json"))
		self._date_ranges = None
		self._current_layer = None
		self._tempfiles = [ ]

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

	def get_day_tags(self, day):
		applicable_tags = self._date_ranges.get_tags(day)
		birthdays = self._birthdays.on_day(day)
		if len(birthdays) > 0:
			applicable_tags.add("birthday")
		return applicable_tags

	def callback_day_comment(self, day):
		birthdays = self._birthdays.on_day(day)
		if len(birthdays) > 0:
			return ", ".join("%s (%d)" % (birthday.name, birthday.age_in(self.year)) for birthday in birthdays)
		start_of = self._date_ranges.starts(day)
		if len(start_of) > 0:
			return start_of[0].name
		return ""

	def callback_format_day_box(self, day, style):
		style["stroke-opacity"] = "0"
		applicable_tags = self.get_day_tags(day)
		for render_date in self._defs["render_dates"]:
			if render_date["tag"] in applicable_tags:
				if "background_fill" in render_date:
					style["fill"] = render_date["background_fill"]

	def callback_fill_day_color(self, day, style):
		applicable_tags = self.get_day_tags(day)
		for render_date in self._defs["render_dates"]:
			if render_date["tag"] in applicable_tags:
				if "day_text_fill" in render_date:
					style["fill"] = render_date["day_text_fill"]

	def _create_tempfile(self, *args, **kwargs):
		f = tempfile.NamedTemporaryFile(*args, **kwargs)
		self._tempfiles.append(f)
		return f

	def callback_has_star(self, day):
		tags = self.get_day_tags(day)
		return "birthday" in tags

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

		if self._args.output_format in [ "png", "jpg" ]:
			# Rendered image will only be there temprarily
			cropped_image_filename = self._create_tempfile(prefix = "cal_cropped_image_", suffix = ".jpg").name
		elif self._args.output_format == "svg":
			# We want to keep the rendered image
			(page_no, layer_no) = self._current_layer
			cropped_image_filename = self.output_dir + "page_%02d_layer_%02d_image_%s.jpg" % (page_no, layer_no, image_name)
		else:
			raise NotImplementedError(self._args.output_format)
		crop_cmd = [ "convert", image_filename, "-gravity", crop_gravity, "-crop", "%dx%d+0+0" % (target_dimensions[0], target_dimensions[1]), cropped_image_filename ]
		subprocess.check_call(crop_cmd)
		return cropped_image_filename

	def _render_layer_to_svg(self, page_no, layer_no, layer_content):
		self._current_layer = (page_no, layer_no)
		layer_filename = self._create_tempfile(prefix = "page_%02d_layer_%02d_" % (page_no, layer_no), suffix = ".svg").name
		layer_vars = {
			"year":			self.year,
			"page_no":		page_no,
			"layer_no":		layer_no,
			"total_pages":	self.total_pages,
		}
		if "vars" in layer_content:
			layer_vars.update(layer_content["vars"])
		svg_data = pkgutil.get_data("calendargen.data", "templates/%s.svg" % (layer_content["template"]))
		data_object = CalendarDataObject(self, layer_vars, self.locale_data)
		processor = SVGProcessor(svg_data, data_object)
		processor.transform()
		processor.write(layer_filename)
		return layer_filename

	def _merge_layers(self, layer_pngs, output_filename):
		temp_page_filename = self._create_tempfile(suffix = ".png").name

		for (layer_no, layer_png_filename) in enumerate(layer_pngs):
			if layer_no == 0:
				# First layer, just move
				shutil.move(layer_png_filename, temp_page_filename)
			else:
				# Compose
				compose_cmd = [ "convert", "-background", "transparent", "-layers", "flatten", temp_page_filename, layer_png_filename, temp_page_filename ]
				subprocess.check_call(compose_cmd)

		if not self.flatten_output:
			shutil.move(temp_page_filename, output_filename)
		else:
			flatten_cmd = [ "convert", "-background", "white", "-flatten", "+repage", temp_page_filename, output_filename ]
			subprocess.check_call(flatten_cmd)

	def _render_page(self, page_no, page_content, page_filename):
		layer_pngs = [ ]
		for (layer_no, layer_content) in enumerate(page_content, 1):
			if self._args.verbose >= 1:
				print("Rendering page %d of %d, layer %d of %d." % (page_no, self.total_pages, layer_no, len(page_content)))
			layer_svg_filename = self._render_layer_to_svg(page_no, layer_no, layer_content)

			if self._args.output_format == "svg":
				target_layer_filename = self.output_dir + "page_%02d_layer_%02d.svg" % (page_no, layer_no)
				shutil.move(layer_svg_filename, target_layer_filename)
			elif self._args.output_format in [ "png", "jpg" ]:
				layer_png_filename = self._create_tempfile(prefix = "page_%02d_layer_%02d_" % (page_no, layer_no), suffix = ".png").name
				render_cmd = [ "inkscape", "-d", str(self.render_dpi), "-e", layer_png_filename, layer_svg_filename ]
				subprocess.check_call(render_cmd, stdout = subprocess.DEVNULL)
				layer_pngs.append(layer_png_filename)
			else:
				raise NotImplementedError(self._args.output_format)

		if self._args.output_format == "png":
			self._merge_layers(layer_pngs, page_filename)
		elif self._args.output_format == "jpg":
			# Merge to temporary PNG first, then convert to JPEG
			page_filename_png = self._create_tempfile(prefix = "cal_page_", suffix = ".png").name
			self._merge_layers(layer_pngs, page_filename_png)
			subprocess.check_call([ "convert", "-quality", "97", page_filename_png, page_filename ])
		else:
			raise NotImplementedError(self._args.output_format)

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
				if self._args.output_format in [ "png", "jpg" ]:
					page_filename = self.output_dir + "page_%02d.%s" % (pageno, self._args.output_format)
				else:
					raise NotImplementedError(self._args.output_format)
				self._render_page(pageno, page_content, page_filename)

	def render(self):
		try:
			if (self._args.remove) and (os.path.exists(self.output_dir)):
				shutil.rmtree(self.output_dir)
			if (not self._args.force) and (os.path.exists(self.output_dir)):
				print("Refusing to overwrite: %s" % (self.output_dir), file = sys.stderr)
				return
			with contextlib.suppress(FileExistsError):
				os.makedirs(self.output_dir)
			self._date_ranges = DateRanges.parse_all(self._defs["dates"])
			self._birthdays = Birthdays.parse_all(self._defs["birthdays"])
			self._do_render()
		finally:
			for f in self._tempfiles:
				with contextlib.suppress(FileNotFoundError):
					f.close()
