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

import os
import sys
import json
import pkgutil
import collections
import datetime
import mako.template
from .DateTools import DateTools
from .ImagePool import ImagePool, ImagePoolSelection, ImageSelectionException

class CalendarTemplate():
	def __init__(self, args, json_filename):
		self._args = args
		with open(json_filename) as f:
			self._defs = json.load(f, object_pairs_hook = collections.OrderedDict)
		self._locales = json.loads(pkgutil.get_data("calendargen.data", "locale.json"))
		self._image_pools = { name: self._load_image_pool(value) for (name, value) in self._defs.get("image_pools", { }).items() }
		self._variant = None
		self._prerender = True
		self._requested_images = [ ]
		self._chosen_images = { }

	def _load_image_pool(self, pool_definition):
		return ImagePool.create_cached_pool(pool_definition.get("cache_filename", ".image_pool.json"), pool_definition["directories"])

	def _render_template_varname(self, template):
		variables =self._variant.get("vars", { })
		name = template["name"]
		if (name not in variables) and (not self._prerender):
			print("Warning: variable %s not defined for variant %s." % (name, self._variant["name"]), file = sys.stderr)
		return variables.get(name, "Undefined: %s" % (name))

	def _render_template_image(self, template):
		if self._prerender:
			self._requested_images.append(template)
			return None
		else:
			pool_name = template.get("pool", "default")
			image = self._chosen_images[pool_name].images.pop(0)
			template_vars = {
				"snaptime":	image.snaptime,
				"agediff":	DateTools.age_diff,
				"datetime":	datetime,
			}
			caption_template = mako.template.Template(template.get("caption", ""), strict_undefined = True)
			caption = caption_template.render(**template_vars)
			return {
				"filename":	image.filename,
				"caption":	caption,
			}

	def _render_template_structure(self, template):
		name = template["substitute"]
		handler = getattr(self, "_render_template_" + name, None)
		if handler is None:
			raise NotImplementedError(name)
		return handler(template)

	def _render_data_structure(self, obj):
		if isinstance(obj, list):
			result = [ ]
			for item in obj:
				result.append(self._render_data_structure(item))
			return result
		elif isinstance(obj, dict):
			if "substitute" in obj:
				return self._render_template_structure(obj)
			else:
				result = collections.OrderedDict()
				for (key, value) in obj.items():
					result[key] = self._render_data_structure(value)
				return result
		else:
			return obj

	def _init_prerender(self):
		self._prerender = True
		self._requested_images = [ ]

	def _finish_prerender(self):
		self._prerender = False
		self._chosen_images = collections.defaultdict(list)
		images_by_pool = collections.defaultdict(list)
		for requested_image in self._requested_images:
			pool_name = requested_image.get("pool", "default")
			images_by_pool[pool_name].append(requested_image)

		for (pool_name, pool_images) in images_by_pool.items():
			pool = self._image_pools[pool_name]
			pool_def = self._defs["image_pools"][pool_name]
			chosen_selection = None
			for run_no in range(pool_def.get("run_count", 100)):
				try:
					selection = ImagePoolSelection(pool, remove_timewindow_secs = pool_def.get("timewindow_secs"))
					selection = selection.select(len(pool_images), set_name = self._variant["name"])
					if (chosen_selection is None) or (selection.fitness > chosen_selection.fitness):
						chosen_selection = selection
				except ImageSelectionException:
					pass
			if selection is None:
				raise Exception("Pool exhausted: %s / %s" % (self._variant["name"], pool_name))
			self._chosen_images[pool_name] = selection

	def _filter_birthdays(self, variant, variant_data):
		if "birthdays" not in variant_data:
			return

		included_birthdays = set(variant.get("birthday_tags", [ ]))
		filtered_birthdays = [ ]
		for birthday_data in variant_data["birthdays"]:
			is_included = ("tag" not in birthday_data) or (birthday_data["tag"] in included_birthdays)
			if is_included:
				filtered_birthdays.append(birthday_data)
		variant_data["birthdays"] = filtered_birthdays


	def _render_variant(self, variant):
		variant_name = variant["name"]
		output_file = self._args.output_dir + "/" + variant_name + ".json"
		if os.path.exists(output_file) and (not self._args.force):
			if self._args.verbose >= 1:
				print("Not overwriting: %s" % (output_file), file = sys.stderr)
			return

		self._variant = variant
		self._init_prerender()
		self._render_data_structure(self._defs["template"])
		self._finish_prerender()
		variant_data = self._render_data_structure(self._defs["template"])
		self._filter_birthdays(variant, variant_data)
		variant_data["meta"]["name"] = variant_name
		with open(output_file, "w") as f:
			json.dump(variant_data, f, indent = 4)

	def render(self):
		for variant in self._defs["variants"]:
			self._render_variant(variant)
