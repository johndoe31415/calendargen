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

import re
import datetime
import mako.template
import lxml.etree

class GenericDataObject():
	def __init__(self):
		self._variables = { }

	@property
	def variables(self):
		return self._variables

	def have_var(self, key):
		return key in self._variables

	def format_box(self, args, style):
		raise NotImplementedError(__class__.__name__)

	def __setitem__(self, key, value):
		self._variables[key] = value

	def __getitem__(self, key):
		return self._variables[key]

class CalendarDataObject(GenericDataObject):
	def __init__(self, data, locale_data):
		GenericDataObject.__init__(self)
		assert(isinstance(data, dict))
		self["day_comment"] = lambda day_of_month: ""
		self._variables.update(data)
		self._locale = locale_data

		self["weekday_abbreviation"]  = self._weekday_abbreviation
#		self["day_comment"] = lambda day_of_month: "Emmy %d" % (day_of_month) if (day_of_month % 8) == 0 else ""
		if self.have_var("month"):
			self["month_name_long"] = locale_data["months_long"][self["month"] - 1]
			self["month_name_short"] = locale_data["months_short"][self["month"] - 1]
			self["days_in_month"] = self._get_days_in_month()

	def _get_days_in_month(self):
		next_month = self["month"] + 1
		next_year = self["year"]
		if next_month == 13:
			next_month = 1
			next_year += 1
		start_of_next_month = datetime.date(next_year, next_month, 1)
		last_day_of_month = start_of_next_month - datetime.timedelta(1)
		return last_day_of_month.day

	def get_day(self, day_of_month):
		try:
			return datetime.date(self["year"], self["month"], day_of_month)
		except ValueError:
			return None

	def _weekday_abbreviation(self, day_of_month):
		day = self.get_day(day_of_month)
		if day is None:
			return "-"
		day_index = day.weekday()
		return self._locale["days_short"][day_index]

	def is_special_day(self, day_of_month):
		day = self.get_day(day_of_month)
		if day is None:
			return False
		day_index = day.weekday()
		return day_index in [ 5, 6 ]

	def format_box(self, args, style):
		if int(args[1]) % 2 == 0:
			style["fill"] = "#ff0000"
		else:
			style.hide()

class SVGStyle():
	def __init__(self, style_dict):
		self._style_dict = style_dict

	@classmethod
	def parse(cls, style_text):
		elements = style_text.split(";")
		style_dict = { }
		for element in elements:
			(key, value) = element.split(":", maxsplit = 1)
			style_dict[key] = value
		return cls(style_dict)

	def remove(self, key):
		if key in self._style_dict:
			del self._style_dict[key]

	def to_string(self):
		return ";".join("%s:%s" % (key, value) for (key, value) in self._style_dict.items())

	def hide(self):
		self["fill"] = "none"
		self["fill-opacity"] = "0"
		self["stroke"] = "none"
		self["stroke-opacity"] = "0"
		self["opacity"] = "0"

	def __setitem__(self, key, value):
		self._style_dict[key] = value

	def __getitem__(self, key):
		return self._style_dict[key]

class SVGCommand():
	_COMMAND_RE = re.compile("(?P<cmdname>[_a-z]+)(:(?P<args>.*))?")
	def __init__(self, cmdname, args_text):
		self._cmdname = cmdname
		self._args_text = args_text

	@classmethod
	def parse(cls, text):
		match = cls._COMMAND_RE.fullmatch(text)
		if match is None:
			return None
		return cls(cmdname = match["cmdname"], args_text = match["args"])

	def _apply_textcmd(self, node, data_object):
		# Mako text substitution
		template = mako.template.Template(self._args_text, strict_undefined = True)
		render_result = template.render(**data_object.variables)

		if node.tag == "{http://www.w3.org/2000/svg}text":
			tspan = node.find("{http://www.w3.org/2000/svg}tspan")
			if tspan is not None:
				tspan.text = render_result
			else:
				print("No tspan found in text element.")
		elif node.tag == "{http://www.w3.org/2000/svg}flowRoot":
			para = node.find("{http://www.w3.org/2000/svg}flowPara")
			if para is not None:
				para.text = render_result
			else:
				print("No flowPara found in flowRoot element.")
		else:
			print("Do not know how to substitute text in node '%s'." % (node.tag))

	def _apply_fill_color_cmd(self, node, data_object):
		style = SVGStyle.parse(node.get("style"))
		cmd_args = self._args_text.split(",")
		if (cmd_args[0] == "day_color"):
			if data_object.is_special_day(int(cmd_args[1])):
				style["fill"] = "#e74c3c"
		node.set("style", style.to_string())

	def _apply_box_cmd(self, node, data_object):
		cmd_args = self._args_text.split(",")
		style = SVGStyle.parse(node.get("style"))
		data_object.format_box(cmd_args, style)
		node.set("style", style.to_string())

	def _apply_removecmd(self, node, data_object):
		expression = self._args_text
		result = eval(expression, data_object.variables)
		if result:
			node.getparent().remove(node)

	def apply(self, node, data_object):
		handler_name = "_apply_%s" % (self._cmdname)
		handler = getattr(self, handler_name, None)
		if handler is None:
			print("Unhandled command: %s" % (self._cmdname))
		else:
			handler(node, data_object)

	def __repr__(self):
		return "%s:(%s)" % (self._cmdname, self._args_text)

class SVGCommands():
	def __init__(self, commands):
		self._commands = commands

	@classmethod
	def parse(cls, text):
		commands = [ SVGCommand.parse(command) for command in text.split("\n") ]
		commands = [ command for command in commands if (command is not None) ]
		return cls(commands)

	def apply(self, node, data_object):
		for command in self._commands:
			command.apply(node, data_object)

	def __repr__(self):
		return "SVGCommands<%d: %s>" % (len(self._commands), ", ".join(str(command) for command in self._commands))

class SVGProcessor():
	def __init__(self, template_svg_data, data_object):
		self._ns = {
			"svg": "http://www.w3.org/2000/svg",
		}
		self._xml = lxml.etree.ElementTree(lxml.etree.fromstring(template_svg_data))
		self._data_object = data_object

	def _transform_desc(self, node, command_text):
		svg_commands = SVGCommands.parse(command_text)
		svg_commands.apply(node, self._data_object)

	def transform(self):
		for desc_node in self._xml.xpath("//svg:desc", namespaces = self._ns):
			target_node = desc_node.getparent()
			commands = desc_node.text
			self._transform_desc(target_node, commands)

	def write(self, output_filename):
		self._xml.write(output_filename, xml_declaration = True, encoding = "utf-8")

if __name__ == "__main__":
	import json
	with open("calendargen/data/locale.json") as f:
		locale_data = json.load(f)["de"]
	with open("calendargen/data/templates/a4_landscape_calendar.svg", "rb") as f:
		svg_data = f.read()
	data = {
		"year":		2021,
		"month":	2,
	}
	data_object = CalendarDataObject(data, locale_data = locale_data)
	svg = SVGProcessor(svg_data, data_object = data_object)
	svg.transform()
	svg.write("x.svg")