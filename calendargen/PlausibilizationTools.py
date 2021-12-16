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

from .Exceptions import ImplausibleDataException

class PlausibilizationTools():
	@classmethod
	def ensure_dict_with_keys(cls, name, source, must_have_keys = None):
		if not isinstance(source, dict):
			raise ImplausibleDataException("'%s' is not a dictionary." % (name))
		if must_have_keys is not None:
			for key in must_have_keys:
				if key not in source:
					raise ImplausibleDataException("'%s' dictionary must have a '%s' key, but does not." % (name, key))

	@classmethod
	def set_comparison(cls, name, defined_set, used_set):
		used_but_never_defined = used_set - defined_set
		defined_but_not_used = defined_set - used_set
		if len(used_but_never_defined) > 0:
			raise ImplausibleDataException("%s: tags(s) %s are used but have never been defined anywhere" % (name, ", ".join(sorted(used_but_never_defined))))
		if len(defined_but_not_used) > 0:
			raise ImplausibleDataException("%s: tags(s) %s have been defined but are never used anywhere" % (name, ", ".join(sorted(defined_but_not_used))))
