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

import re
import geo
import mako.template
import lxml.etree
from .Exceptions import InvalidSVGException, IllegalCalendarDefinitionException

class GenericDataObject():
	def __init__(self):
		self._variables = { }

	@property
	def variables(self):
		return self._variables

	def have_var(self, key):
		return key in self._variables

	def fill_color(self, args, style):
		raise NotImplementedError(self.__class__.__name__)

	def format_box(self, args, style):
		raise NotImplementedError(self.__class__.__name__)

	def get_image(self, image_name, dimensions):
		raise NotImplementedError(self.__class__.__name__)

	def __setitem__(self, key, value):
		self._variables[key] = value

	def __getitem__(self, key):
		return self._variables[key]

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

	def _get_transformation_matrix(self, node):
		matrix = geo.TransformationMatrix.identity()
		current = node
		while current is not None:
			transform_str = current.get("transform")
			if transform_str is not None:
				transform = geo.SVGTools.parse_transform(transform_str)
				matrix *= transform
			current = current.getparent()
		return matrix

	def _apply_text_cmd(self, node, data_object):
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
		cmd_args = self._args_text.split(",")
		style = SVGStyle.parse(node.get("style"))
		data_object.fill_color(cmd_args, style)
		node.set("style", style.to_string())

	def _apply_box_cmd(self, node, data_object):
		cmd_args = self._args_text.split(",")
		style = SVGStyle.parse(node.get("style"))
		data_object.format_box(cmd_args, style)
		node.set("style", style.to_string())

	def _apply_img_cmd(self, node, data_object):
		image_name = self._args_text
		orig_box = geo.Box2d(base = geo.Vector2d(float(node.get("x")), float(node.get("y"))), dimensions = geo.Vector2d(float(node.get("width")), float(node.get("height"))))
		matrix = self._get_transformation_matrix(node)
		modified_box = orig_box.transform(matrix)
		image_source = data_object.get_image(image_name, modified_box.dimensions)
		if image_source is not None:
			node.set("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}absref", image_source)
			node.set("{http://www.w3.org/1999/xlink}href", image_source)

	def _apply_remove_cmd(self, node, data_object):
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
	def __init__(self, template_svg_data):
		self._ns = {
			"svg": "http://www.w3.org/2000/svg",
		}
		self._xml = lxml.etree.ElementTree(lxml.etree.fromstring(template_svg_data))
		self._desc_nodes = self._find_desc_nodes()
		self._unused_elements = set(self._desc_nodes)

	@property
	def unused_elements(self):
		return self._unused_elements

	def _find_desc_nodes(self):
		desc_nodes = { }
		for desc_node in self._xml.xpath("//svg:desc", namespaces = self._ns):
			target_node = desc_node.getparent()
			description = desc_node.text
			if description in desc_nodes:
				raise InvalidSVGException("SVG data contains duplicate description element '%s'." % (description))
			desc_nodes[description] = target_node
		return desc_nodes

	def _transform_desc(self, node, command_text):
		svg_commands = SVGCommands.parse(command_text)
		svg_commands.apply(node, self._data_object)

	def _handle_noop(self, element, instruction):
		pass

	def _handle_set_text(self, element, instruction):
		if element.tag == "{http://www.w3.org/2000/svg}text":
			tspan = element.find("{http://www.w3.org/2000/svg}tspan")
			if tspan is not None:
				tspan.text = instruction["text"]
			else:
				print("No tspan found in text element.")
		elif element.tag == "{http://www.w3.org/2000/svg}flowRoot":
			para = element.find("{http://www.w3.org/2000/svg}flowPara")
			if para is not None:
				para.text = instruction["text"]
			else:
				raise InvalidSVGException("No flowPara found in flowRoot element.")
		else:
			raise InvalidSVGException("Do not know how to substitute text in element '%s'." % (element.tag))

	def handle_instruction(self, element_name, instruction):
		if element_name not in self._desc_nodes:
			raise IllegalCalendarDefinitionException("Unknown element specified for SVG transformation: %s" % (element_name))
		if element_name in self._unused_elements:
			self._unused_elements.remove(element_name)
		element = self._desc_nodes[element_name]
		cmd = instruction["cmd"]
		handler = getattr(self, "_handle_" + cmd, None)
		if handler is None:
			raise IllegalCalendarDefinitionException("Unknown command specified for SVG transformation: %s" % (cmd))
		handler(element, instruction)

	def handle_instructions(self, element_name, instructions):
		for instruction in instructions:
			self.handle_instruction(element_name, instruction)

	def write(self, output_filename):
		self._xml.write(output_filename, xml_declaration = True, encoding = "utf-8")
