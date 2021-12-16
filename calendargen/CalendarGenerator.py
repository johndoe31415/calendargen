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

import json
import datetime
import collections
import pkgutil
from .Exceptions import IllegalCalendarDefinitionException
from .DateTools import DateTools, AgeTools
from .SVGProcessor import SVGProcessor

class CalendarGenerator():
	def __init__(self, calendar_definition, variant):
		self._def = calendar_definition
		self._variant = variant
		self._page = None
		self._page_no = None
		self._layers = None

	@property
	def current_layer(self):
		return self._layers[-1]

	def _new_layer(self, template_name, compose = None):
		layer = collections.OrderedDict()
		layer["template"] = template_name
		if compose is not None:
			layer["compose"] = compose
		layer["transform"] = collections.OrderedDict()
		self._layers.append(layer)

	def _get_svg_processor(self):
		layer_name = self.current_layer["template"]
		svg_name = "%s_%s.svg" % (self._def.format, layer_name)
		svg_data = pkgutil.get_data("calendargen.data", "templates/%s" % (svg_name))
		return SVGProcessor(svg_data)

	def _transform_text(self, key, value):
		self._transform_noop(key)
		self.current_layer["transform"][key].append(collections.OrderedDict((
			("cmd", "set_text"),
			("text", value),
		)))

	def _transform_remove(self, key):
		self.current_layer["transform"][key] = [
			collections.OrderedDict((
				("cmd", "set_style"),
				("hide", True),
			))
		]

	def _transform_noop(self, key):
		if key not in self.current_layer["transform"]:
			self.current_layer["transform"][key] = [ { "cmd": "noop" } ]

	def _transform_style(self, key, style):
		if key not in self.current_layer["transform"]:
			self.current_layer["transform"][key] = [ ]
		style_dict = collections.OrderedDict((
			("cmd", "set_style"),
		))
		style_dict.update(style)
		self.current_layer["transform"][key].append(style_dict)

	def _generate_header_layer(self):
		if not self._page.get("header", True):
			return
		if "heading" in self._variant:
			text = "%s %d/%d" % (self._variant["heading"], self._page_no, self._def.total_page_count)
		else:
			text = "%d/%d" % (self._page_no, self._def.total_page_count)
		self._new_layer("header", compose = "inverted")
		self._transform_text("header_text", text)

	def _get_image_image_cover_page(self):
		name = "%03d-cover" % (self._page_no)
		print(name)

	def _get_image_image_month_page(self):
		name = "%03d-month" % (self._page_no)
		print(name)

	def _fill_images(self, *image_names):
		svg_processor = self._get_svg_processor()
		for image_name in image_names:
			print(svg_processor.get_image_dimensions(image_name))

	def _generate_image_cover_page(self):
		year = self._page.get("year", self._def.meta["year"])

		self._new_layer("image_cover_page")
		self._transform_text("year_text", str(year))
		self._fill_images("image")

	def _determine_day_rule(self, day_tags):
		for rule in self._def.coloring_rules:
			if rule["tag"] in day_tags:
				# Match!
				return rule
		return None

	def _generate_only_month_calendar(self):
		year = self._page.get("year", self._def.meta["year"])
		month = self._page["month"]
		month_days = DateTools.enumerate_month(month, year)
		last_day = max(month_days)

		relevant_day_ranges = self._def.parsed_dates.filter_ranges(only_days = month_days, only_tags = set(self._variant.get("day_tags", [ ])))
		relevant_birthdays = self._def.parsed_birthdays.filter_birthdays(only_tags = set(self._variant.get("birthday_tags", [ ])))

		self._new_layer("month_calendar")
		month_name = self._def.locale_data["months_long"][month - 1]
		self._transform_text("month_text", month_name)
		self._transform_text("year_text", str(year))

		month_comment_by_day = collections.defaultdict(list)

		for day_no in range(1, last_day.day + 1):
			day = datetime.date(year, month, day_no)
			day_tags = relevant_day_ranges.get_tags(day)
			dow_text = self._def.locale_data["days_short"][day.weekday()]
			coloring_rule = self._determine_day_rule(day_tags)

			has_birthday = relevant_birthdays.on_day(day)
			for birthday in has_birthday:
				birthday_text = "%s (%d)" % (birthday.name, year - birthday.date.year)
				month_comment_by_day[day_no].append(birthday_text)

			dayrange_starts = relevant_day_ranges.starts(day)
			if len(dayrange_starts) > 0:
				month_comment_by_day[day_no] += [ dayrange.name for dayrange in dayrange_starts ]

			have_star = len(has_birthday) > 0
			day_box_style = { }
			day_text_style = { }
			if coloring_rule is not None:
				if "day_box_fill" in coloring_rule:
					day_box_style["fill"] = coloring_rule["day_box_fill"]
				if "day_text_fill" in coloring_rule:
					day_text_style["fill"] = coloring_rule["day_text_fill"]

			self._transform_style("day_box_%02d" % (day_no), day_box_style)
			self._transform_text("dow_%02d_text" % (day_no), dow_text)
			self._transform_style("dow_%02d_text" % (day_no), day_text_style)
			if have_star:
				self._transform_noop("star_%02d" % (day_no))
			else:
				self._transform_remove("star_%02d" % (day_no))
			if day_no >= 29:
				self._transform_noop("group_%02d" % (day_no))

		month_comment_list = [ ]
		for (day_no, day_comment_list) in sorted(month_comment_by_day.items()):
			day_comment = "%d: %s" % (day_no, ", ".join(day_comment_list))
			month_comment_list.append(day_comment)
		month_comment = "; ".join(month_comment_list)
		self._transform_text("month_comment_text", month_comment)

		for day_no in range(last_day.day + 1, 31 + 1):
			# Remove all these days from the calendar
			self._transform_remove("group_%02d" % (day_no))
			self._transform_noop("star_%02d" % (day_no))
			self._transform_noop("day_box_%02d" % (day_no))
			self._transform_noop("dow_%02d_text" % (day_no))

	def _append_single_image(self):
		self._new_layer("landscape_single_image")
		self._fill_images("image")

	def _generate_image_month_page(self):
		self._generate_only_month_calendar()
		self._append_single_image()

	def _determine_image_dependencies(self):
		for (self._page_no, self._page) in enumerate(self._def.pages, 1):
			handler_name = "_get_image_%s" % (self._page["type"])
			handler = getattr(self, handler_name, None)
			if handler is not None:
				handler()

	def _generate_calendar_layout(self):
		layout = collections.OrderedDict()
		layout["meta"] = collections.OrderedDict()
		layout["meta"]["name"] = self._variant["name"]
		layout["meta"]["format"] = self._def.format
		layout["pages"] = [ ]
		for (self._page_no, self._page) in enumerate(self._def.pages, 1):
			handler_name = "_generate_%s" % (self._page["type"])
			handler = getattr(self, handler_name, None)
			if handler is None:
				raise IllegalCalendarDefinitionException("No such handler: %s; page type '%s' is not supported" % (handler_name, self._page["type"]))
			self._layers = [ ]
			handler()
			self._generate_header_layer()
			layout["pages"].append(self._layers)
		return layout

	def generate(self, output_filename):
		try:
			self._determine_image_dependencies()
			layout = self._generate_calendar_layout()
			with open(output_filename, "w") as f:
				json.dump(layout, f, indent = 4)
				f.write("\n")
		finally:
			self._page = None
			self._page_no = None
			self._layers = None
