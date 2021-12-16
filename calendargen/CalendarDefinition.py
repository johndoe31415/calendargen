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
import pkgutil
from .Exceptions import IllegalCalendarDefinitionException
from .PlausibilizationTools import PlausibilizationTools
from .DateRange import Birthdays, DateRanges

class CalendarDefinition():
	def __init__(self, json_filename):
		with open(json_filename) as f:
			self._definition = json.load(f)
		self._plausibilize()
		self._locale_data = self._load_locale_data()
		self._parsed_dates = DateRanges.parse_all(self.dates)
		self._parsed_birthdays = Birthdays.parse_all(self.birthdays)

	def _load_locale_data(self):
		locales_data = json.loads(pkgutil.get_data("calendargen.data", "locale.json"))
		return locales_data[self.locale]

	def _plausibilize(self):
		PlausibilizationTools.ensure_dict_with_keys("definition", self._definition, [ "pages" ])

		for date in self.dates:
			PlausibilizationTools.ensure_dict_with_keys("definition[\"dates\"]", date, [ "tags", "colortag" ])
		for birthday in self.birthdays:
			PlausibilizationTools.ensure_dict_with_keys("definition[\"birthdays\"]", birthday, [ "date", "name", "tags" ])
		for coloring_rule in self.coloring_rules:
			PlausibilizationTools.ensure_dict_with_keys("definition[\"coloring_rules\"]", coloring_rule, [ "tag" ])
		for page in self.pages:
			PlausibilizationTools.ensure_dict_with_keys("definition[\"pages\"]", page, [ "type" ])

		variant_names = set()
		for variant in self.variants:
			PlausibilizationTools.ensure_dict_with_keys("definition[\"variants\"]", variant, [ "name" ])
			if variant["name"] in variant_names:
				raise IllegalCalendarDefinitionException("Duplicate variant name: %s" % (variant["name"]))
			variant_names.add(variant["name"])

		coloring_rule_tags = set()
		for coloring_rule in self.coloring_rules:
			if coloring_rule["tag"] in coloring_rule_tags:
				raise IllegalCalendarDefinitionException("Duplicate coloring_rule tag: %s" % (coloring_rule["tag"]))
			coloring_rule_tags.add(coloring_rule["tag"])

		defined_tags = self._get_all_defined_tags()
		used_tags = self._get_all_used_tags()
		for name in [ "day", "birthday", "coloring" ]:
			PlausibilizationTools.set_comparison(name = "%s tag" % (name), defined_set = defined_tags["%s_tags" % (name)], used_set = used_tags["%s_tags" % (name)])

	@property
	def parsed_dates(self):
		return self._parsed_dates

	@property
	def parsed_birthdays(self):
		return self._parsed_birthdays

	@property
	def meta(self):
		return self._definition.get("meta", { })

	@property
	def format(self):
		return self.meta.get("format", "30x20")

	@property
	def locale(self):
		return self.meta.get("locale", "us")

	@property
	def dates(self):
		return self._definition.get("dates", [ ])

	@property
	def birthdays(self):
		return self._definition.get("birthdays", [ ])

	@property
	def coloring_rules(self):
		return self._definition.get("coloring_rules", [ ])

	@property
	def variants(self):
		return iter(self._definition["variants"])

	@property
	def variant_names(self):
		for variant in self.variants:
			yield variant["name"]

	@property
	def pages(self):
		return iter(self._definition["pages"])

	@property
	def total_page_count(self):
		return len(self._definition["pages"])

	@property
	def locale_data(self):
		return self._locale_data

	def get_variant(self, variant_name):
		return next(variant for variant in self.variants if (variant["name"] == variant_name))

	def _get_all_defined_tags(self):
		day_tags = set()
		coloring_tags = set()
		for date in self.dates:
			day_tags |= set(date.get("tags", [ ]))
			coloring_tags.add(date["colortag"])

		birthday_tags = set()
		for birthday in self.birthdays:
			birthday_tags |= set(birthday.get("tags", [ ]))

		return {
			"day_tags":			day_tags,
			"birthday_tags":	birthday_tags,
			"coloring_tags":	coloring_tags,
		}

	def _get_all_used_tags(self):
		day_tags = set()
		birthday_tags = set()
		image_tags = set()
		for variant in self.variants:
			day_tags |= set(variant.get("day_tags", [ ]))
			birthday_tags |= set(variant.get("birthday_tags", [ ]))
			image_tags |= set(variant.get("image_tags", [ ]))

		coloring_tags = set()
		for coloring_rule in self.coloring_rules:
			coloring_tags.add(coloring_rule["tag"])

		# Some coloring tags are defined implicitly, ignore them.
		coloring_tags -= set([ "weekday-mon", "weekday-tue", "weekday-wed", "weekday-thu", "weekday-fri", "weekday-sat", "weekday-sun" ])
		return {
			"day_tags":			day_tags,
			"birthday_tags":	birthday_tags,
			"image_tags":		image_tags,
			"coloring_tags":	coloring_tags,
		}
