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

import subprocess
import logging
import lxml.etree
import geo
from .CmdlineEscape import CmdlineEscape
from .Exceptions import InvalidSVGException, IllegalLayoutDefinitionException
from .ImageTools import ImageTools
from .JobServer import Job

_log = logging.getLogger(__spec__.name)

class SVGStyle():
	def __init__(self, style_dict):
		self._style_dict = style_dict

	@classmethod
	def parse(cls, style_text):
		if style_text is None:
			return cls({ })
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

	def __repr__(self):
		return "Style<%s>" % (self.to_string())

class SVGProcessor():
	def __init__(self, template_svg_data, temp_dir = None):
		self._ns = {
			"svg": "http://www.w3.org/2000/svg",
		}
		self._xml = lxml.etree.ElementTree(lxml.etree.fromstring(template_svg_data))
		self._temp_dir = temp_dir
		self._desc_nodes = self._find_desc_nodes()
		self._unused_elements = set(self._desc_nodes)
		self._dependent_jobs = [ ]
		self._image_no = 0

	@property
	def unused_elements(self):
		return self._unused_elements

	@property
	def dependent_jobs(self):
		return self._dependent_jobs

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
				_log.error("No tspan found in text element.")
		elif element.tag == "{http://www.w3.org/2000/svg}flowRoot":
			para = element.find("{http://www.w3.org/2000/svg}flowPara")
			if para is not None:
				para.text = instruction["text"]
			else:
				raise InvalidSVGException("No flowPara found in flowRoot element.")
		else:
			raise InvalidSVGException("Do not know how to substitute text in element '%s'." % (element.tag))

	def _handle_set_style(self, element, instruction):
		style = SVGStyle.parse(element.get("style"))
		for keyword in [ "fill", "stroke", "opacity", "stroke-opacity", "fill-opacity", "stoke-width" ]:
			if keyword in instruction:
				style[keyword] = instruction[keyword]
		if instruction.get("hide"):
			style.hide()
		element.set("style", style.to_string())


	def _get_transformation_matrix(self, element):
		matrix = geo.TransformationMatrix.identity()
		current = element
		while current is not None:
			transform_str = current.get("transform")
			if transform_str is not None:
				transform = geo.SVGTools.parse_transform(transform_str)
				matrix *= transform
			current = current.getparent()
		return matrix

	def _get_element_dimensions(self, element):
		orig_box = geo.Box2d(base = geo.Vector2d(float(element.get("x")), float(element.get("y"))), dimensions = geo.Vector2d(float(element.get("width")), float(element.get("height"))))
		matrix = self._get_transformation_matrix(element)
		modified_box = orig_box.transform(matrix)
		dimensions = modified_box.dimensions
		return dimensions

	def get_image_dimensions(self, element_name):
		return self._get_element_dimensions(self._desc_nodes[element_name])

	def _handle_image(self, element, instruction):
		dimensions = self._get_element_dimensions(element)

		image_filename = instruction["filename"]
		image_dimensions = ImageTools.get_image_geometry(image_filename)
		crop_gravity = instruction.get("gravity", "center")

		image_aspect_ratio = ImageTools.approximate_aspect_ratio(image_dimensions[0], image_dimensions[1])
		placement_aspect_ratio = ImageTools.approximate_float_aspect_ratio(dimensions[0] / dimensions[1])

		_log.debug("Image %s: %d x %d pixels (ratio %d:%d); placement dimensions %.3f x %.3f (ratio %d:%d)", image_filename, image_dimensions[0], image_dimensions[1], image_aspect_ratio.short.numerator, image_aspect_ratio.short.denominator, dimensions[0], dimensions[1], placement_aspect_ratio.short.numerator, placement_aspect_ratio.short.denominator)
		target_width = round(image_dimensions[1] * placement_aspect_ratio.value)
		target_height = round(image_dimensions[0] / placement_aspect_ratio.value)
		if target_width <= image_dimensions[0]:
			# Cropping height
			target_dimensions = (target_width, image_dimensions[1])
			cropped_ratio = (image_dimensions[0] - target_width) / image_dimensions[0]
			cropped_target = "height"
		else:
			# Cropping width
			target_dimensions = (image_dimensions[0], target_height)
			cropped_ratio = (image_dimensions[1] - target_height) / image_dimensions[1]
			cropped_target = "width"

		self._image_no += 1
		cropped_image_filename = self._temp_dir + "/cropped_%03d.jpg" % (self._image_no)

		_log.trace("Cropping %s: %d x %d (gravity %s) to %s", image_filename, target_dimensions[0], target_dimensions[1], crop_gravity, cropped_image_filename)
		threshold_percent = 2
		if cropped_ratio > (threshold_percent / 100):
			_log.warning("Warning: More than %.1f%% of the image %s of %s are cropped (%.1f%% cropped).", threshold_percent, image_filename, cropped_target, cropped_ratio * 100)

		crop_cmd = [ "convert", image_filename, "-gravity", crop_gravity, "-crop", "%dx%d+0+0" % (target_dimensions[0], target_dimensions[1]), cropped_image_filename ]
		_log.debug("Crop image: %s", CmdlineEscape().cmdline(crop_cmd))
		self._dependent_jobs.append(Job(subprocess.check_call, (crop_cmd, ), name = "crop-image"))

		element.set("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}absref", cropped_image_filename)
		element.set("{http://www.w3.org/1999/xlink}href", cropped_image_filename)

	def handle_instruction(self, element_name, instruction):
		if element_name not in self._desc_nodes:
			raise IllegalLayoutDefinitionException("Unknown element specified for SVG transformation: %s" % (element_name))
		if "cmd" not in instruction:
			raise IllegalLayoutDefinitionException("No 'cmd' key given in SVG transformation: %s" % (element_name))
		if element_name in self._unused_elements:
			self._unused_elements.remove(element_name)
		element = self._desc_nodes[element_name]
		cmd = instruction["cmd"]
		handler = getattr(self, "_handle_" + cmd, None)
		if handler is None:
			raise IllegalLayoutDefinitionException("Unknown command specified for SVG transformation: %s" % (cmd))
		handler(element, instruction)

	def handle_instructions(self, element_name, instructions):
		for instruction in instructions:
			self.handle_instruction(element_name, instruction)

	def write(self, output_filename):
		self._xml.write(output_filename, xml_declaration = True, encoding = "utf-8")
