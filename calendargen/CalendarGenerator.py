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
from .Exceptions import IllegalCalendarDefinitionException
from .DateTools import DateTools, AgeTools

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

	def _generate_image_cover_page(self):
		year = self._page.get("year", self._def.meta["year"])

		self._new_layer("image_cover_page")
		self._transform_text("year_text", str(year))

	def _determine_day_style(self, day):
		assert(isinstance(day, datetime.date))
		style = { }
		return style

	def _generate_image_month_page(self):
		year = self._page.get("year", self._def.meta["year"])
		month = self._page["month"]
		month_days = DateTools.enumerate_month(month, year)
		last_day = max(month_days)


		self._new_layer("month_calendar")
		month_name = self._def.locale_data["months_long"][month - 1]
		self._transform_text("month_text", month_name)
		self._transform_text("year_text", str(year))

		month_comment = "TEST COMMENT"
		self._transform_text("month_comment_text", month_comment)

		for day_no in range(1, last_day.day + 1):
			day = datetime.date(year, month, day_no)
			have_star = False
			dow_text = self._def.locale_data["days_short"][day.weekday()]
			style = self._determine_day_style(day)

			self._transform_style("day_box_%02d" % (day_no), style)
			self._transform_text("dow_%02d_text" % (day_no), dow_text)
			if have_star:
				self._transform_noop("star_%02d" % (day_no))
			else:
				self._transform_remove("star_%02d" % (day_no))
			if day_no >= 29:
				self._transform_noop("group_%02d" % (day_no))


		for day_no in range(last_day.day + 1, 31 + 1):
			# Remove all these days from the calendar
			self._transform_remove("group_%02d" % (day_no))
			self._transform_noop("star_%02d" % (day_no))
			self._transform_noop("day_box_%02d" % (day_no))
			self._transform_noop("dow_%02d_text" % (day_no))

	def generate(self, output_filename):
		try:
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

			with open(output_filename, "w") as f:
				json.dump(layout, f, indent = 4)
				f.write("\n")
		finally:
			self._page = None
			self._page_no = None
			self._layers = None
