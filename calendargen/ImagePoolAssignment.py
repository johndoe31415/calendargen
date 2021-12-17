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

import datetime
import logging
import collections
import random
from .Exceptions import IllegalImagePoolActionException
from .ImageTools import ImageTools

PlacementResult = collections.namedtuple("PlacementResults", [ "total_slots", "total_filled", "remaining_open" ])
ImagePoolCandidate = collections.namedtuple("ImagePoolCandidate", [ "filename", "snaptime", "aspect_ratio", "tag_sets" ])

_log = logging.getLogger(__spec__.name)

class ImagePoolSlot():
	def __init__(self, name, aspect_ratio, filled_by = None):
		self._name = name
		self._aspect_ratio = aspect_ratio
		self._initially_filled_by = filled_by
		self._filled_by = filled_by

	@property
	def filled(self):
		return self._filled_by is not None

	@property
	def name(self):
		return self._name

	@property
	def aspect_ratio(self):
		return self._aspect_ratio

	@property
	def filled_by(self):
		return self._filled_by

	@filled_by.setter
	def filled_by(self, value):
		self._filled_by = value

	def reset(self):
		self._filled_by = self._initially_filled_by

	def __repr__(self):
		if self.filled_by is None:
			return "Slot<%s, %.3f>" % (self.name, self.aspect_ratio)
		else:
			return "Slot<%s, %.3f: %s>" % (self.name, self.aspect_ratio, self.filled_by)

class ImagePoolAssignment():
	def __init__(self, image_pool, variant_name = None, exclusion_window_secs = 3600):
		self._image_pool = image_pool
		self._variant_name = variant_name
		self._exclusion_window_secs = exclusion_window_secs
		self._slots = collections.OrderedDict()
		self._candidates = None
		self._initial_candidates = None

	@property
	def slots(self):
		return iter(self._slots.values())

	def _compatible_aspect_ratio(self, candidate, crop_aspect_ratio):
		coverage_ratio = ImageTools.usable_image_ratio(candidate.aspect_ratio, crop_aspect_ratio)
		return coverage_ratio >= 0.75

	def _find_candidates(self, filter_condition, source = None):
		if source is None:
			source = self._candidates
		return [ candidate for candidate in source if filter_condition(candidate) ]

	def _remove_candidate_when(self, filter_condition):
		keep = [ ]
		removed = [ ]
		for candidate in self._candidates:
			if filter_condition(candidate):
				removed.append(candidate)
			else:
				keep.append(candidate)
		self._candidates = keep
		return removed

	def _remove_candidate_with_dependencies(self, filter_condition, remove_timewindow = True, remove_groups = True):
		removed = self._remove_candidate_when(filter_condition)
		for removed_candidate in removed:
			if remove_timewindow:
				min_ts = removed.snaptime - datetime.timedelta(0, self._exclusion_window_secs)
				max_ts = removed.snaptime + datetime.timedelta(0, self._exclusion_window_secs)
				self._remove_candidate_when(lambda candidate: min_ts <= candidate.snaptime <= max_ts)
			if remove_groups:
				for remove_grp in removed_candidate.tag_sets.get("grp", [ ]):
					self._remove_candidate_when(lambda candidate: remove_grp in candidate.tag_sets.get("grp", [ ]))

	def _calculate_candidates(self):
		if self._candidates is not None:
			return

		# Ensure those files which are already placed are part of the pool.
		filled_filenames = [ ]
		for slot in self.slots:
			if slot.filled:
				filled_filenames.append(slot_filled_by)
		if len(filled_filenames) > 0:
			self._image_pool.scan_files(filled_filenames)

		# Then create the initial list of all candidates
		self._candidates = [ ]
		for (filename, meta) in self._image_pool:
			aspect_ratio = meta["meta"]["geometry"][0] / meta["meta"]["geometry"][1]
			snaptime = datetime.datetime.strptime(meta["meta"]["snaptime"], "%Y-%m-%dT%H:%M:%S")
			tag_sets = { name: set(items) for (name, items) in meta["tags"].items() }
			candidate = ImagePoolCandidate(filename = filename, snaptime = snaptime, aspect_ratio = aspect_ratio, tag_sets = tag_sets)
			_log.trace("Candidate: %s", str(candidate))
			self._candidates.append(candidate)
		_log.debug("Initial list of candidates: %d images", len(self._candidates))

		# Then filter all those that are already assigned
		for slot in self.slots:
			if slot.filled:
				self._remove_candidate_with_dependencies(lambda candidate: candidate.filename == slot.filename)

		# Then filter all those which have tags that are incompatible with this variant
		if self._variant_name is not None:
			self._remove_candidate_when(lambda candidate: ("only" in candidate.tag_sets) and (self._variant_name not in candidate.tag_sets["only"]))

		_log.debug("After filtering: %d images", len(self._candidates))
		self._initial_candidates = list(self._candidates)

	def add_slot(self, name, aspect_ratio, filled_by = None):
		if name in self._slots:
			raise IllegalImagePoolActionException("Attempt to add slot '%s' twice." % (name))
		self._slots[name] = ImagePoolSlot(name = name, aspect_ratio = aspect_ratio, filled_by = filled_by)
		return self

	def _attempt_placement_of(self, slot, forced_images):
		_log.debug("Attempting placement of slot: %s", str(slot))

		# First search for hits in the forced image list
		candidates = self._find_candidates(lambda candidate: self._compatible_aspect_ratio(candidate, slot.aspect_ratio), forced_images)
		if len(candidates) > 0:
			choice = random.choice(candidates)
			forced_images.remove(choice)
			slot.filled_by = choice.filename
			return True

		# Then search among all images
		candidates = self._find_candidates(lambda candidate: self._compatible_aspect_ratio(candidate, slot.aspect_ratio))
		if len(candidates) > 0:
			choice = random.choice(candidates)
			slot.filled_by = choice.filename
			return True

		return False

	def attempt_placement(self):
		self._calculate_candidates()
		self._candidates = list(self._initial_candidates)
		for slot in self.slots:
			slot.reset()
		remaining_slots = [ slot for slot in self.slots if not slot.filled ]
		if self._variant_name is not None:
			forced_images = self._find_candidates(lambda candidate: ("forced" in candidate.tag_sets) and (self._variant_name in candidate.tag_sets["forced"]))
		else:
			forced_images = [ ]
		_log.debug("Attempting to fill %d slots.", len(remaining_slots))
		failed_count = 0
		while len(remaining_slots) > 0:
			next_slot = remaining_slots.pop()
			success = self._attempt_placement_of(next_slot, forced_images)
			if not success:
				failed_count += 1
		if failed_count > 0:
			_log.error("Failure of image placement: %d images could not be filled with suitable candidates.", failed_count)
		if len(forced_images) > 0:
			_log.warning("%d images which are marked as forced were not placed.", len(forced_images))
		return (failed_count == 0) and (len(forced_images) == 0)

if __name__ == "__main__":
	logging.basicConfig(format = "{name:>30s} [{levelname:.1s}]: {message}", style = "{", level = logging.TRACE)

	from .ImagePool import ImagePool
	ip = ImagePool([ "pool2020", "pool2021" ])
	ipa = ImagePoolAssignment(ip, variant_name = "foobar")
	ipa.add_slot("foo", 16/9)
	success = ipa.attempt_placement()
	for slot in ipa.slots:
		print(slot)
