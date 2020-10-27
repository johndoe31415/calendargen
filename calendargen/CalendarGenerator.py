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

class CalendarGenerator():
	def __init__(self, args, json_filename):
		self._args = args
		with open(json_filename) as f:
			self._defs = json.load(f)

	@property
	def render_dpi(self):
		return self._defs["meta"].get("output_dpi", 300)

	@property
	def calendar_name(self):
		return self._defs["meta"].get("name", "unnamed_calendar")

	@property
	def locale(self):
		return self._defs["meta"].get("locale", "en")

	@property
	def year(self):
		return self._defs["meta"]["year"]

	@property
	def output_dir(self):
		return self._args.output_dir + "/" + self.calendar_name + "/"

	def render(self):
		if (not self._args.force) and (os.path.exists(self.output_dir)):
			print("Refusing to overwrite: %s" % (self.output_dir), file = sys.stderr)
			return
		with contextlib.suppress(FileExistsError):
			os.makedirs(self.output_dir)

		print(self.output_dir)
