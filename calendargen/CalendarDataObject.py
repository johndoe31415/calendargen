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

import datetime
from .SVGProcessor import GenericDataObject

class CalendarDataObject(GenericDataObject):
	def __init__(self, renderer, data, locale_data):
		GenericDataObject.__init__(self)
		assert(isinstance(data, dict))
		self._renderer = renderer
		self._variables.update(data)
		self._locale = locale_data

		self["weekday_abbreviation"]  = self._weekday_abbreviation
		self["day_comment"] = self._day_comment
		self["has_star"] = self._has_star
		if self.have_var("month"):
			self["month_name_long"] = locale_data["months_long"][self["month"] - 1]
			self["month_name_short"] = locale_data["months_short"][self["month"] - 1]
			self["days_in_month"] = self._get_days_in_month()

			day_comments = [ ]
			for day in self.all_days_of_month:
				comment = self._renderer.callback_day_comment(day)
				if comment != "":
					day_comments.append("%d: %s" % (day.day, comment))
			self["month_comment"] = ",   ".join(day_comments)

	@property
	def all_days_of_month(self):
		for day_of_month in range(1, 31):
			day = self.get_day(day_of_month)
			if day is not None:
				yield day

	def _get_days_in_month(self):
		next_month = self["month"] + 1
		next_year = self["year"]
		if next_month == 13:
			next_month = 1
			next_year += 1
		start_of_next_month = datetime.date(next_year, next_month, 1)
		last_day_of_month = start_of_next_month - datetime.timedelta(1)
		return last_day_of_month.day

	def get_day(self, day_of_month):
		try:
			return datetime.date(self["year"], self["month"], day_of_month)
		except ValueError:
			return None

	def _weekday_abbreviation(self, day_of_month):
		day = self.get_day(day_of_month)
		if day is None:
			return "-"
		day_index = day.weekday()
		return self._locale["days_short"][day_index]

	def _day_comment(self, day_of_month):
		day = self.get_day(day_of_month)
		if day is None:
			return ""
		return self._renderer.callback_day_comment(day)

	def fill_color(self, args, style):
		assert(args[0] == "day_color")
		assert(len(args) == 2)
		day = self.get_day(int(args[1]))
		if day is not None:
			self._renderer.callback_fill_day_color(day, style)

	def format_box(self, args, style):
		assert(args[0] == "day_box")
		assert(len(args) == 2)
		day = self.get_day(int(args[1]))
		if day is not None:
			self._renderer.callback_format_day_box(day, style)

	def _has_star(self, day_of_month):
		day = self.get_day(day_of_month)
		if day is None:
			return False
		return self._renderer.callback_has_star(day)

	def get_image(self, image_name, dimensions):
		return self._renderer.callback_get_image(self, image_name, dimensions)
