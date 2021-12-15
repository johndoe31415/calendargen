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
from .Exceptions import IllegalLayoutDefinitionException

class LayoutDefinition():
	def __init__(self, json_filename):
		with open(json_filename) as f:
			self._definition = json.load(f)
		self._plausibilize()
		self._locales_data = json.loads(pkgutil.get_data("calendargen.data", "locale.json"))

	def _ensure_dict_with_keys(self, name, source, must_have_keys = None):
		if not isinstance(source, dict):
			raise IllegalLayoutDefinitionException("'%s' is not a dictionary." % (name))
		if must_have_keys is not None:
			for key in must_have_keys:
				if key not in source:
					raise IllegalLayoutDefinitionException("'%s' dictionary must have a '%s' key, but does not." % (name, key))

	def _plausibilize(self):
		self._ensure_dict_with_keys("definition", self._definition, [ "pages" ])

	@property
	def format(self):
		return self._definition.get("meta", { }).get("format", "30x20")

	@property
	def name(self):
		return self._definition.get("meta", { }).get("name", "unnamed")

	@property
	def pages(self):
		return iter(self._definition["pages"])

	@property
	def total_page_count(self):
		return len(self._definition["pages"])

	@property
	def locale_data(self):
		return self._locales_data[self.locale]
