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

import sys
from .FriendlyArgumentParser import FriendlyArgumentParser
from .CalendarGenerator import CalendarGenerator

def _pagedef(page_str):
	if "-" in page_str:
		(from_page, to_page) = page_str.split("-", maxsplit = 1)
		return (int(from_page), int(to_page))
	else:
		page = int(page_str)
		return (page, page)

parser = FriendlyArgumentParser(description = "Create a calendar based on a template definition file.")
parser.add_argument("-f", "--force", action = "store_true", help = "Force overwriting of already rendered files if they exist.")
parser.add_argument("--remove", action = "store_true", help = "Remove already rendered output directory if it exists.")
parser.add_argument("-p", "--page", metavar = "pageno", type = _pagedef, action = "append", default = [ ], help = "Render only defined page(s). Can be either a number (e.g., \"7\") or a range (e.g., \"7-10\"). Defaults to all pages.")
parser.add_argument("-o", "--output-dir", metavar = "dirname", default = "generated_calendars", help = "Output directory in which genereated calendars reside. Defaults to %(default)s.")
parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
parser.add_argument("input_file", nargs = "+", help = "JSON definition input file(s) which should be rendered")
args = parser.parse_args(sys.argv[1:])

for filename in args.input_file:
	cal_gen = CalendarGenerator(args, filename)
	cal_gen.render()
