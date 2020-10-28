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

class DateRange():
	def __init__(self, days, name, tags):
		self._days = days
		self._name = name
		self._tags = tags

	@property
	def name(self):
		return self._name

	@property
	def tags(self):
		return self._tags

	@property
	def first_day(self):
		return min(self._days)

	@classmethod
	def parsedate(cls, date_str):
		return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

	@classmethod
	def from_to_date(cls, from_date, to_date):
		current_day = from_date
		while current_day <= to_date:
			yield current_day
			current_day += datetime.timedelta(1)

	@classmethod
	def parse(cls, text, name, tags):
		days = set()
		text = text.replace(" ", "")
		text = text.replace("\t", "")
		date_ranges = text.split("+")
		for date_range in date_ranges:
			if "," not in date_range:
				days.add(cls.parsedate(date_range))
			else:
				(first, last) = date_range.split(",", maxsplit = 1)
				first = cls.parsedate(first)
				last = cls.parsedate(last)
				days |= set(cls.from_to_date(first, last))
		return cls(days, name = name, tags = tags)

	def __contains__(self, day):
		return day in self._days

	def __str__(self):
		return "DateRange<%s / %s: %s>" % (self.name, ", ".join(sorted(self.tags)), ", ".join(str(x) for x in sorted(self._days)))

class DateRanges():
	def __init__(self, date_ranges):
		self._ranges = date_ranges

	@classmethod
	def parse_all(cls, definitions):
		date_ranges = [ ]

		for range_definition in definitions:
			tags = range_definition.get("tag")
			if tags is None:
				tags = set()
			else:
				tags = set(tags.split(","))
			date_range = DateRange.parse(range_definition["date"], name = range_definition.get("name"), tags = tags)
			date_ranges.append(date_range)
		return cls(date_ranges)

	def get_tags(self, day):
		applicable_tags = set()
		if day is None:
			return applicable_tags
		applicable_tags.add({
			0:	"weekday-mon",
			1:	"weekday-tue",
			2:	"weekday-wed",
			3:	"weekday-thu",
			4:	"weekday-fri",
			5:	"weekday-sat",
			6:	"weekday-sun",
		}[day.weekday()])
		for date_range in self._ranges:
			if day in date_range:
				applicable_tags |= date_range.tags
		return applicable_tags

class Birthday():
	def __init__(self, date, name):
		self._date = date
		self._name = name

	@property
	def name(self):
		return self._name

	def on_day(self, day):
		if day.year <= self._date.year:
			return False

		if (day.month == self._date.month) and (day.day == self._date.day):
			return True

		if (self._date.month == 2) and (self._date.day == 29):
			# Birthday on leap day. Does the requested year have a leap day?
			try:
				possible_birthday = datetime.date(day.year, 2, 29)
			except ValueError:
				# The requested year does not have a leap day. Then we
				# celebrate on the first of March (German custom). This can
				# easily be substituted by 28th of February (e.g., in New
				# Zealand).
				return (day.month, day.day) == (3, 1)
		return False

	def age_in(self, year):
		return year - self._date.year

	@classmethod
	def parse(cls, definition):
		date = datetime.datetime.strptime(definition["date"], "%Y-%m-%d").date()
		return cls(date = date, name = definition["name"])

class Birthdays():
	def __init__(self, birthdays):
		self._birthdays = birthdays

	@classmethod
	def parse_all(cls, definitions):
		return cls(birthdays = [ Birthday.parse(definition) for definition in definitions ])

	def on_day(self, day):
		return [ birthday for birthday in self._birthdays if birthday.on_day(day) ]

if __name__ == "__main__":
	dr = DateRanges.parse_all([
		{ "date": "2021-11-02,2021-11-05 + 2021-11-17", "name": "Herbstferien", "tag": "school-by" },
		{ "date": "2021-12-24,2022-01-08", "name": "Weihnachtsferien", "tag": "school-by" }
	])
	print(dr.get_tags(datetime.date(2021, 11, 17)))

	birthdays = Birthdays.parse_all([
		{ "date": "1983-02-10", "name": "Someone" },
		{ "date": "2016-02-29", "name": "Else" }
	])
	print(birthdays.on_day(datetime.date(2020, 3, 1)))
