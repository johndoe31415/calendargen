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
import json
import fractions
import collections
import re

class ImageTools():
	_SNAPTIME_RE = re.compile("(?P<year>\d{4}):(?P<month>\d{2}):(?P<day>\d{2}) (?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})")
	_AspectRatio = collections.namedtuple("AspectRatio", [ "value", "width", "height", "ideal", "short" ])

	@classmethod
	def get_image_stats(cls, filename):
		json_data = subprocess.check_output([ "convert", filename, "json:-" ])
		data = json.loads(json_data)
		image = data[0]["image"]

		snaptime = None
		for key in [ "exif:DateTimeOriginal", "exif:DateTime" ]:
			if key in image["properties"]:
				snaptime = image["properties"][key]
				break
		else:
			print("No EXIF timestamp:")
			print(image["properties"])

		if snaptime is not None:
			result = cls._SNAPTIME_RE.fullmatch(snaptime)
			result = result.groupdict()
			snaptime_fmt = "%04d-%02d-%02dT%02d:%02d:%02d" % (int(result["year"]), int(result["month"]), int(result["day"]), int(result["hour"]), int(result["minute"]), int(result["second"]))
		else:
			snaptime_fmt = None
		return {
			"geometry":		(image["geometry"]["width"], image["geometry"]["height"]),
			"snaptime":		snaptime_fmt,
			"statistic": {
				"img":		image["imageStatistics"],
				"chan":		image["channelStatistics"],
			},
		}

	@classmethod
	def get_image_geometry(cls, filename):
		return cls.get_image_stats(filename)["geometry"]

	@classmethod
	def approximate_aspect_ratio(cls, width, height, shorten_above = 20):
		if height is not None:
			ideal_ratio = fractions.Fraction(width, height)
			float_ratio = float(ideal_ratio)
		else:
			float_ratio = width
			height = 10000
			width = round(height * float_ratio)
			ideal_ratio = fractions.Fraction(width, height)

		ratio = ideal_ratio
		while (ratio.numerator > shorten_above) or (ratio.denominator > shorten_above):
			if (ratio.numerator % 2) == 1:
				ratio1 = fractions.Fraction(ratio.numerator - 1, ratio.denominator)
				ratio2 = fractions.Fraction(ratio.numerator + 1, ratio.denominator)
			else:
				ratio1 = fractions.Fraction(ratio.numerator, ratio.denominator - 1)
				ratio2 = fractions.Fraction(ratio.numerator, ratio.denominator + 1)
			if ratio1.numerator < ratio2.numerator:
				ratio = ratio1
			else:
				ratio = ratio2
		return cls._AspectRatio(value = float_ratio, width = width, height = height, ideal = ideal_ratio, short = ratio)

	@classmethod
	def approximate_float_aspect_ratio(cls, ratio, shorten_above = 20):
		return cls.approximate_aspect_ratio(width = ratio, height = None, shorten_above = shorten_above)

if __name__ == "__main__":
	print(ImageTools.approximate_aspect_ratio(1920, 1080))
	print(ImageTools.approximate_aspect_ratio(800, 600))
	print(ImageTools.approximate_aspect_ratio(768, 600))
	print(ImageTools.approximate_aspect_ratio(600, 768))
	print(ImageTools.approximate_aspect_ratio(6240, 4160))
	print(ImageTools.approximate_aspect_ratio(1920, 1080, shorten_above = 8))
