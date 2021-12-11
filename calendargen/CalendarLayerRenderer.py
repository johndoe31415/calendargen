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

import pkgutil
from .SVGProcessor import SVGProcessor
from .CalendarDataObject import CalendarDataObject

class CalendarLayerRenderer():
	def __init__(self, calendar_definition, page_no, layer_definition, output_file):
		self._calendar_definition = calendar_definition
		self._page_no = page_no
		self._layer_definition = layer_definition
		self._output_file = output_file

	def callback_day_comment(self, day):
		print(day)

	def render(self):
		layer_vars = {
			"page_no":		self._page_no,
			"total_pages":	self._calendar_definition.total_page_count,
		}
		if "vars" in self._layer_definition:
			layer_vars.update(self._layer_definition["vars"])
		svg_data = pkgutil.get_data("calendargen.data", "templates/%s_%s.svg" % (self._calendar_definition.format, self._layer_definition["template"]))
		data_object = CalendarDataObject(self, layer_vars, self._calendar_definition.locale_data)
		processor = SVGProcessor(svg_data, data_object)
		processor.transform()
		processor.write(layer_filename)
