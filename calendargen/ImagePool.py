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
import re
import json
import datetime
import subprocess
import lxml.etree

class ImageEntry():
	_XMP_NS = {
		"x":	"adobe:ns:meta/",
		"rdf":	"http://www.w3.org/1999/02/22-rdf-syntax-ns#",
		"dc":	"http://purl.org/dc/elements/1.1/",
		"xmp":	"http://ns.adobe.com/xap/1.0/",
	}
	_SNAPTIME_RE = re.compile(r"(?P<year>\d{4}):(?P<month>\d{2}):(?P<day>\d{2}) (?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})")
	def __init__(self, filename, json_data):
		self._filename = filename
		self._data = json_data
		self._metadata_xml = None
		self._exif = None
		self._complete_file()

	def _complete_file(self):
		if "tags" in self._data:
			self._data["tags"] = set(self._data["tags"])
		else:
			self._data["tags"] = self._scan_tags()

		if "snaptime" in self._data:
			if self._data["snaptime"] is not None:
				self._data["snaptime"] = datetime.datetime.strptime(self._data["snaptime"], "%Y-%m-%dT%H:%M:%SZ")
		else:
			self._data["snaptime"] = self._scan_snaptime()
		self._process_tags()

	def _process_tags(self):
		self._data["groups"] = set()
		self._data["probability"] = 1
		for tag in self._data["tags"]:
			if tag.startswith("grp="):
				self._data["groups"].add(tag[4:])
			elif tag.startswith("prob="):
				self._data["probability"] = float(tag[5:])

	def _scan_tags(self):
		tags = set()
		if self.meta_xml is not None:
			desc = self.meta_xml.xpath("/x:xmpmeta/rdf:RDF/rdf:Description[1]", namespaces = self._XMP_NS)[0]
			bag = desc.xpath("./dc:subject/rdf:Bag/rdf:li", namespaces = self._XMP_NS)
			for tag_node in bag:
				tag = tag_node.text
				tags.add(tag)
		return tags

	def _scan_snaptime(self):
		if self.exif_info is not None:
			snaptime = self.exif_info.get("CreateDate")
			if snaptime is not None:
				match = self._SNAPTIME_RE.fullmatch(snaptime)
				if match is not None:
					match = match.groupdict()
					return datetime.datetime(int(match["year"]), int(match["month"]), int(match["day"]), int(match["hour"]), int(match["minute"]), int(match["second"]))
				else:
					print("Warning: no match for EXIF timestamp: %s" % (snaptime))

	@property
	def meta_xml(self):
		if self._metadata_xml is None:
			metadata_xml_filename = os.path.expanduser("~/.local/share/geeqie/metadata" + self._filename + ".gq.xmp")
			if os.path.isfile(metadata_xml_filename):
				self._metadata_xml = lxml.etree.parse(metadata_xml_filename).getroot()
		return self._metadata_xml

	@property
	def exif_info(self):
		if self._exif is None:
			exif = json.loads(subprocess.check_output([ "exiftool", "-j", self._filename ]))[0]
			return exif

	@property
	def filename(self):
		return self._filename

	@property
	def size(self):
		return self._data["size"]

	@property
	def mtime(self):
		return self._data["mtime"]

	@property
	def snaptime(self):
		return self._data["snaptime"]

	@property
	def groups(self):
		return self._data["groups"]

	@property
	def probability(self):
		return self._data["probability"]

	def to_json(self):
		return {
			"size":		self.size,
			"mtime":	self.mtime,
			"tags":		list(self._data["tags"]),
			"snaptime":	self._data["snaptime"].strftime("%Y-%m-%dT%H:%M:%SZ") if (self._data["snaptime"] is not None) else None,
		}

class ImagePool():
	def __init__(self):
		self._images = { }

	@classmethod
	def load_cache_file(cls, cache_filename):
		cache = cls()
		with open(cache_filename) as f:
			cache_file = json.load(f)
			cache._images = { filename: ImageEntry(filename, data) for (filename, data) in cache_file.items() }
		return cache

	def save_cache_file(self, cache_filename):
		data = { key: entry.to_json() for (key, entry) in self._images.items() }
		with open(cache_filename, "w") as f:
			json.dump(data, f)

	def add_file(self, filename):
		filename = os.path.realpath(filename)
		stat = os.stat(filename)
		if (filename in self._images) and (self._images[filename].mtime == stat.st_mtime) and (self._images[filename].size == stat.st_size):
			# Actually not modified, return.
			return

		data = {
			"mtime":	stat.st_mtime,
			"size":		stat.st_size,
		}
		entry = ImageEntry(filename, data)
		self._images[filename] = entry
		return entry

	def add_directory(self, root_dirname):
		for (dirname, subdirs, files) in os.walk(root_dirname):
			for filename in files:
				full_filename = dirname + "/" + filename
				if filename.lower().endswith(".jpg"):
					self.add_file(full_filename)

	def __iter__(self):
		return iter(self._images.values())
