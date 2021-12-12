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

import logging
import subprocess

logging.TRACE = logging.DEBUG - 1
logging.SINGLESTEP = logging.DEBUG - 2
logging.addLevelName(logging.TRACE, "TRACE")
logging.addLevelName(logging.SINGLESTEP, "SINGLESTEP")

class CustomLogger(logging.Logger):
	@property
	def subproc_target(self):
		if self.isEnabledFor(logging.TRACE):
			return None
		else:
			return subprocess.DEVNULL

	def trace(self, msg, *args, **kwargs):
		if self.isEnabledFor(logging.TRACE):
			self._log(logging.TRACE, msg, args, **kwargs)

logging.setLoggerClass(CustomLogger)
