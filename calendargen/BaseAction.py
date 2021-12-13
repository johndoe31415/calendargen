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

import logging

class BaseAction():
	def __init__(self, cmd, args):
		self._cmd = cmd
		self._args = args
		if self._args.verbose == 0:
			loglevel = logging.WARN
		elif self._args.verbose == 1:
			loglevel = logging.INFO
		elif self._args.verbose == 2:
			loglevel = logging.DEBUG
		else:
			loglevel = logging.TRACE
		logging.basicConfig(format = "{name:>30s} [{levelname:.1s}]: {message}", style = "{", level = loglevel)
		self.run()

	def run(self):
		raise NotImplementedError(self.__class__.__name__)
