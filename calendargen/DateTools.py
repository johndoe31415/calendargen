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

import math
import datetime
import collections
import fractions

class DateTools():
	_AgeDifference = collections.namedtuple("AgeDifference", [ "start_of_pregnancy", "pregnancy_length_days", "birthday", "ref_date", "day_count", "text" ])

	@classmethod
	def _sym(cls, numerator, denominator):
		frc = fractions.Fraction(numerator, denominator)
		if frc == fractions.Fraction(1, 4):
			return "¼"
		elif frc == fractions.Fraction(1, 2):
			return "½"
		elif frc == fractions.Fraction(3, 4):
			return "¾"
		else:
			return ""

	@classmethod
	def _date_diff(cls, ts1, ts2):
		days = (ts1 - ts2).days
		assert(days > 0)
		if days == 1:
			return "%d Tag" % (days)
		elif days < 7:
			return "%d Tage" % (days)
		else:
			year_count = cls._full_year_diff(ts1, ts2)
			month_count = cls._full_month_diff(ts1, ts2)
			week_count = cls._full_week_diff(ts1, ts2)
			if month_count == 0:
				if week_count == 1:
					return "%d Woche" % (week_count)
				else:
					return "%d Wochen" % (week_count)
			elif month_count == 1:
				return "%d Monat" % (month_count)
			elif year_count == 0:
				return "%d Monate" % (month_count)
			else:
				# Compute years
				float_year_count = cls._float_year_diff(ts1, ts2)
				quad_years = math.floor(float_year_count * 4)
				half_years = math.floor(float_year_count * 2)

				if quad_years < (4 * 3):
					(fyears, ryears) = divmod(quad_years, 4)
					sym = cls._sym(ryears, 4)
					if (fyears == 1) and (ryears == 0):
						return "%d%s Jahr" % (fyears, sym)
					else:
						return "%d%s Jahre" % (fyears, sym)
				elif quad_years < (4 * 6):
					(fyears, ryears) = divmod(half_years, 2)
					sym = cls._sym(ryears, 2)
					if (fyears == 1) and (ryears == 0):
						return "%d%s Jahr" % (fyears, sym)
					else:
						return "%d%s Jahre" % (fyears, sym)
				elif year_count == 1:
					return "%d Jahr" % (year_count)
				else:
					return "%d Jahre" % (year_count)

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

	@classmethod
	def age_diff(cls, birthday, ref_date = None, pregnancy_length_days = 280):
		if ref_date is None:
			ref_date = datetime.datetime.utcnow()
		birthday = birthday.date()
		ref_date = ref_date.date()
		start_of_pregnancy = birthday - datetime.timedelta(pregnancy_length_days)

		day_count = (ref_date - birthday).days
		if day_count < 0:
			# Pre-birth. In pregnancy?
			pregnancy_week = cls._full_week_diff(ref_date, start_of_pregnancy)
			date_diff = cls._date_diff(birthday, ref_date)
			if (abs(day_count) < pregnancy_length_days) and (pregnancy_week > 0):
				# Yes
				text = "%s vor Geburt / %d. SSW" % (date_diff, pregnancy_week)
			else:
				# No, before
				text = "%s vor Geburt" % (date_diff)
		elif day_count == 0:
			text = "Tag der Geburt"
		else:
			# Is exact birthday?
			if (birthday.day, birthday.month) == (ref_date.day, ref_date.month):
				age = cls._full_year_diff(ref_date, birthday)
				text = "%d. Geburtstag" % (age)
			else:
				date_diff = cls._date_diff(ref_date, birthday)
				text = "%s alt" % (date_diff)

		return cls._AgeDifference(start_of_pregnancy = start_of_pregnancy, pregnancy_length_days = pregnancy_length_days, birthday = birthday, ref_date = ref_date, day_count = day_count, text = text)

if __name__ == "__main__":
	birthday = datetime.datetime(2020, 2, 29)

	current = birthday - datetime.timedelta(2 * 365 + 10)
	last = birthday + datetime.timedelta(8 * 365 + 10)
	while current < last:
		print(DateTools.age_diff(birthday, current))
		current += datetime.timedelta(1)

