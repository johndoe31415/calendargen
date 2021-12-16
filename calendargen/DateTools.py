#	calendargen - Photo calendar generator
#	Copyright (C) 2020-2021 Johannes Bauer
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

import math
import datetime
import collections
import fractions

class DateTools():
	@classmethod
	def enumerate_month(cls, month, year):
		next_month = month + 1
		next_year = year
		if next_month == 13:
			next_month = 1
			next_year += 1
		first_day = datetime.date(year, month, 1)
		last_day = datetime.date(next_year, next_month, 1)
		days = set()
		current_day = first_day
		while current_day < last_day:
			days.add(current_day)
			current_day += datetime.timedelta(1)
		return days

class AgeTools():
	_AgeDifference = collections.namedtuple("AgeDifference", [ "start_of_pregnancy", "pregnancy_length_days", "birthday", "ref_date", "day_count", "text" ])

	def __init__(self, locale_data):
		self._locale = locale_data["age_terms"]

	@staticmethod
	def _sym(numerator, denominator):
		frc = fractions.Fraction(numerator, denominator)
		if frc == fractions.Fraction(1, 4):
			return "¼"
		elif frc == fractions.Fraction(1, 2):
			return "½"
		elif frc == fractions.Fraction(3, 4):
			return "¾"
		else:
			return ""

	def _date_diff(self, ts1, ts2):
		days = (ts1 - ts2).days
		assert(days > 0)
		if days == 1:
			return "%d %s" % (days, self._locale["day"])
		elif days < 7:
			return "%d %s" % (days, self._locale["days"])
		else:
			year_count = self._full_year_diff(ts1, ts2)
			month_count = self._full_month_diff(ts1, ts2)
			week_count = self._full_week_diff(ts1, ts2)
			if month_count == 0:
				if week_count == 1:
					return "%d %s" % (week_count, self._locale["week"])
				else:
					return "%d %s" % (week_count, self._locale["weeks"])
			elif month_count == 1:
				return "%d %s" % (month_count, self._locale["month"])
			elif year_count == 0:
				return "%d %s" % (month_count, self._locale["months"])
			else:
				# Compute years
				float_year_count = self._float_year_diff(ts1, ts2)
				quad_years = math.floor(float_year_count * 4)
				half_years = math.floor(float_year_count * 2)

				if quad_years < (4 * 3):
					(fyears, ryears) = divmod(quad_years, 4)
					sym = self._sym(ryears, 4)
					if (fyears == 1) and (ryears == 0):
						return "%d%s %s" % (fyears, sym, self._locale["year"])
					else:
						return "%d%s %s" % (fyears, sym, self._locale["years"])
				elif quad_years < (4 * 6):
					(fyears, ryears) = divmod(half_years, 2)
					sym = self._sym(ryears, 2)
					if (fyears == 1) and (ryears == 0):
						return "%d%s %s" % (fyears, sym, self._locale["year"])
					else:
						return "%d%s %s" % (fyears, sym, self._locale["years"])
				elif year_count == 1:
					return "%d %s" % (year_count, self._locale["year"])
				else:
					return "%d %s" % (year_count, self._locale["years"])

	@classmethod
	def _month_idx(cls, ts):
		return (ts.year * 12) + (ts.month - 1)

	@classmethod
	def _full_month_diff(cls, ts1, ts2):
		months = cls._month_idx(ts1) - cls._month_idx(ts2)
		if ts1.day < ts2.day:
			months -= 1
		return months

	@classmethod
	def _month_diff(cls, ts1, ts2):
		mon

	@classmethod
	def _full_week_diff(cls, ts1, ts2):
		days = (ts1 - ts2).days
		return days // 7

	@classmethod
	def _full_year_diff(cls, ts1, ts2):
		years = ts1.year - ts2.year
		if (ts1.month, ts1.day) < (ts2.month, ts2.day):
			years -= 1
		return years

	@classmethod
	def _float_year_diff(cls, ts1, ts2):
		days = (ts1 - ts2).days
		return days / 365.25

	def age_diff(self, birthday, ref_date = None, pregnancy_length_days = 280):
		if ref_date is None:
			ref_date = datetime.datetime.utcnow()
		birthday = birthday.date()
		ref_date = ref_date.date()
		start_of_pregnancy = birthday - datetime.timedelta(pregnancy_length_days)

		day_count = (ref_date - birthday).days
		if day_count < 0:
			# Pre-birth. In pregnancy?
			pregnancy_week = self._full_week_diff(ref_date, start_of_pregnancy)
			date_diff = self._date_diff(birthday, ref_date)
			if (abs(day_count) < pregnancy_length_days) and (pregnancy_week > 0):
				# Yes
				text = "%s %s / %d. %s" % (date_diff, self._locale["before_birth"], pregnancy_week, self._locale["pregnancy_week"])
			else:
				# No, before
				text = "%s %s" % (date_diff, self._locale["before_birth"])
		elif day_count == 0:
			text = self._locale["day_of_birth"]
		else:
			# Is exact birthday?
			if (birthday.day, birthday.month) == (ref_date.day, ref_date.month):
				age = self._full_year_diff(ref_date, birthday)
				text = "%d. %s" % (age, self._locale["birthday"])
			else:
				date_diff = self._date_diff(ref_date, birthday)
				text = "%s %s" % (date_diff, self._locale["old"])

		return self._AgeDifference(start_of_pregnancy = start_of_pregnancy, pregnancy_length_days = pregnancy_length_days, birthday = birthday, ref_date = ref_date, day_count = day_count, text = text)

if __name__ == "__main__":
	import json
	import pkgutil

	locales_data = json.loads(pkgutil.get_data("calendargen.data", "locale.json"))
	locale_data = locales_data["de"]
	dt = AgeTools(locale_data)
	birthday = datetime.datetime(2020, 2, 29)

	current = birthday - datetime.timedelta(2 * 365 + 10)
	last = birthday + datetime.timedelta(8 * 365 + 10)
	while current < last:
		print(dt.age_diff(birthday, current))
		current += datetime.timedelta(1)

