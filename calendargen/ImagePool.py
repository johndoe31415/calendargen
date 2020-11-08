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
import collections
import subprocess
import lxml.etree
from .RandomDist import RandomDist

class ImageSelectionException(Exception): pass

class ImageEntry():
	_XMP_NS = {
		"x":	"adobe:ns:meta/",
		"rdf":	"http://www.w3.org/1999/02/22-rdf-syntax-ns#",
		"dc":	"http://purl.org/dc/elements/1.1/",
		"xmp":	"http://ns.adobe.com/xap/1.0/",
	}
	_SNAPTIME_RE = re.compile(r"(?P<year>\d{4}):(?P<month>\d{2}):(?P<day>\d{2}) (?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})")
	def __init__(self, filename, modification_key, tags, snaptime):
		filename = os.path.realpath(filename)
		assert((snaptime is None) or isinstance(snaptime, datetime.datetime))
		assert(isinstance(tags, set))
		self._filename = filename
		self._modification_key = modification_key
		self._tags = tags
		self._snaptime = snaptime

		self._groups = None
		self._probability = None
		self._only_in = None
		self._force_in = None
		self._interpret_tags()

	def _interpret_tags(self):
		self._groups = set()
		self._probability = 1
		self._only_in = set()
		self._force_in = set()
		for tag in self._tags:
			if tag.startswith("grp="):
				self._groups |= set(tag[4:].split(","))
			elif tag.startswith("only="):
				self._only_in |= set(tag[5:].split(","))
			elif tag.startswith("force="):
				self._force_in |= set(tag[6:].split(","))
			elif tag.startswith("prob="):
				self._probability = float(tag[5:])

	@classmethod
	def geeqie_metadata_xml_filename(cls, image_filename):
		metadata_xml_filename = os.path.expanduser("~/.local/share/geeqie/metadata" + image_filename + ".gq.xmp")
		return metadata_xml_filename

	@classmethod
	def meta_xml(cls, image_filename):
		metadata_xml_filename = cls.geeqie_metadata_xml_filename(image_filename)
		if os.path.isfile(metadata_xml_filename):
			return lxml.etree.parse(metadata_xml_filename).getroot()
		else:
			return None

	@classmethod
	def _parse_geeqie_metadata(cls, image_filename):
		meta_xml = cls.meta_xml(image_filename)
		tags = set()
		if meta_xml is not None:
			desc = meta_xml.xpath("/x:xmpmeta/rdf:RDF/rdf:Description[1]", namespaces = cls._XMP_NS)[0]
			bag = desc.xpath("./dc:subject/rdf:Bag/rdf:li", namespaces = cls._XMP_NS)
			for tag_node in bag:
				tag = tag_node.text
				tags.add(tag)
		return tags

	@classmethod
	def _parse_exif_metadata(cls, image_filename):
		exif = { }
		exif_info = json.loads(subprocess.check_output([ "exiftool", "-j", image_filename ]))[0]
		if exif_info is not None:
			snaptime = exif_info.get("CreateDate")
			if snaptime is not None:
				match = cls._SNAPTIME_RE.fullmatch(snaptime)
				if match is not None:
					match = match.groupdict()
					exif["snaptime"] = datetime.datetime(int(match["year"]), int(match["month"]), int(match["day"]), int(match["hour"]), int(match["minute"]), int(match["second"]))
				else:
					print("Warning: no match for EXIF timestamp: %s" % (snaptime))
		return exif

	@property
	def filename(self):
		return self._filename

	@property
	def snaptime(self):
		return self._snaptime

	@property
	def groups(self):
		return self._groups

	@property
	def only_in(self):
		return self._only_in

	@property
	def force_in(self):
		return self._force_in

	@property
	def probability(self):
		return self._probability

	def to_json(self):
		return {
			"modification_key":		self._modification_key,
			"tags":					list(self._tags),
			"snaptime":				self._snaptime.strftime("%Y-%m-%dT%H:%M:%SZ") if (self._snaptime is not None) else None,
		}

	@classmethod
	def filekey(cls, filename):
		try:
			stat = os.stat(filename)
			return [ filename, stat.st_mtime, stat.st_size ]
		except FileNotFoundError:
			return [ filename, None, None ]

	@classmethod
	def modification_key(cls, filename):
		filename = os.path.realpath(filename)
		meta_xml_filename = cls.geeqie_metadata_xml_filename(filename)
		modification_key = [ cls.filekey(filename), cls.filekey(meta_xml_filename) ]
		return modification_key

	@classmethod
	def from_file(cls, filename):
		filename = os.path.realpath(filename)
		modification_key = cls.modification_key(filename)
		tags = cls._parse_geeqie_metadata(filename)
		exif = cls._parse_exif_metadata(filename)
		return cls(filename = filename, modification_key = modification_key, tags = tags, snaptime = exif.get("snaptime"))

	@classmethod
	def from_json(cls, filename, json_data):
		snaptime = datetime.datetime.strptime(json_data["snaptime"], "%Y-%m-%dT%H:%M:%SZ") if (json_data["snaptime"] is not None) else None
		return cls(filename = filename, modification_key = json_data["modification_key"], tags = set(json_data["tags"]), snaptime = snaptime)

	def update(self):
		current_mkey = self.modification_key(self.filename)
		if current_mkey == self._modification_key:
			return self
		else:
			return self.from_file(self.filename)

	def __lt__(self, other):
		return self.filename < other.filename

	def __eq__(self, other):
		return self.filename == other.filename

	def __neq__(self, other):
		return not (self == other)

	def __hash__(self):
		return hash(self.filename)

	def __str__(self):
		return "Image<%s>" % (self.filename)

class ImagePoolSelection():
	_SelectionResult = collections.namedtuple("SelectionResult", [ "initial_selection_length", "forced_count", "min_timedelta", "images" ])

	def __init__(self, pool, remove_groups = True, remove_timewindow_secs = None):
		self._pool = pool
		self._images = list(pool)
		self._remove_groups = remove_groups
		self._remove_timewindow_secs = remove_timewindow_secs

	def _filter_images(self, predicate):
		return [ image for image in self._images if predicate(image) ]

	def remove_tag(self, remove_tag):
		self._images = self._filter_images(predicate = lambda image: remove_tag not in image.tags)

	def remove_tags(self, remove_tags):
		for remove_tag in reove_tags:
			self.remove_tag(remove_tag)

	def keep_only_tags(self, keep_tags):
		self._images = self._filter_images(predicate = lambda image: tag in keep_tags)

	def remove_group(self, remove_group_name):
		self._images = self._filter_images(predicate = lambda image: remove_group_name not in image.groups)

	def remove(self, remove_image):
		self._images = self._filter_images(predicate = lambda image: image.filename != remove_image.filename)

	def remove_timewindow(self, reference_image):
		if self._remove_timewindow_secs is None:
			return
		if reference_image.snaptime is None:
			return

		min_ts = reference_image.snaptime - datetime.timedelta(0, self._remove_timewindow_secs)
		max_ts = reference_image.snaptime + datetime.timedelta(0, self._remove_timewindow_secs)
		self._images = self._filter_images(predicate = lambda image: (image.snaptime is None) or not (min_ts < image.snaptime < max_ts))

	def remove_full(self, image):
		self.remove(image)
		if self._remove_groups:
			for group in image.groups:
				self.remove_group(group)
		self.remove_timewindow(image)

	def force_get(self, image_filename):
		found = self._filter_images(predicate = lambda image: image.filename == image_filename)
		if len(found) == 1:
			found = found[0]
			self.remove_full(found)
			return found
		else:
			return None

	def preselect(self, set_name):
		def _set_name_filter(image):
			if len(image.only_in) > 0:
				if set_name not in image.only_in:
					return False
			return True
		self._images = self._filter_images(predicate = _set_name_filter)

	def get(self):
		if len(self._images) == 0:
			raise ImageSelectionException("No more images left in image pool to choose from.")
		options = { image: image.probability for image in self._images }
		image = RandomDist(options).event()
		self.remove_full(image)
		return image

	def select(self, image_count, set_name):
		self.preselect(set_name)
		initial_selection_length = len(self._images)

		images = self._filter_images(predicate = lambda image: set_name in image.force_in)
		forced_count = len(images)
		self._images = self._filter_images(predicate = lambda image: set_name not in image.force_in)

		images = [ self.get() for _ in range(image_count) ]
		if len(images) > image_count:
			raise ImageSelectionException("Too many images forced, %d requested but %d in final selection." % (image_count, len(images)))

		images.sort(key = lambda image: image.snaptime or datetime.datetime(1970, 1, 1, 0, 0, 0))
		min_timedelta = None
		for (image1, image2) in zip(images, images[1:]):
			if (image1.snaptime is not None) and (image2.snaptime is not None):
				timedelta = (image2.snaptime - image1.snaptime).total_seconds()
				if (min_timedelta is None) or (timedelta < min_timedelta):
					min_timedelta = timedelta
		return self._SelectionResult(images = images, forced_count = forced_count, min_timedelta = min_timedelta, initial_selection_length = initial_selection_length)

	def __len__(self):
		return len(self._images)

	def __str__(self):
		return "Selection<%d of %d>" % (len(self), len(self._pool))

class ImagePool():
	def __init__(self):
		self._images = { }
		self._groups = collections.defaultdict(set)

	@classmethod
	def load_cache_file(cls, cache_filename):
		cache = cls()
		with open(cache_filename) as f:
			cache_file = json.load(f)
			cache._images = { filename: ImageEntry.from_json(filename, data) for (filename, data) in cache_file.items() }
		return cache

	@classmethod
	def create_cached_pool(cls, cache_filename, image_directories):
		try:
			pool = cls.load_cache_file(cache_filename)
		except FileNotFoundError:
			pool = cls()
		for dirname in image_directories:
			pool.add_directory(dirname)
		pool.save_cache_file(cache_filename)
		return pool

	@property
	def groups(self):
		return iter(self._groups.items())

	def save_cache_file(self, cache_filename):
		data = { key: entry.to_json() for (key, entry) in self._images.items() }
		with open(cache_filename, "w") as f:
			json.dump(data, f)

	def add_file(self, filename):
		filename = os.path.realpath(filename)
		if filename in self._images:
			entry = self._images[filename].update()
		else:
			entry = ImageEntry.from_file(filename)
		for group in entry.groups:
			self._groups[group].add(filename)
		self._images[filename] = entry
		return entry

	def add_directory(self, root_dirname):
		for (dirname, subdirs, files) in os.walk(root_dirname):
			for filename in files:
				full_filename = dirname + "/" + filename
				if filename.lower().endswith(".jpg"):
					self.add_file(full_filename)

	def __len__(self):
		return len(self._images)

	def __iter__(self):
		return iter(self._images.values())
