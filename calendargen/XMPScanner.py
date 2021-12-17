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

import os
import collections
import lxml.etree

class XMPScanner():
	_XMP_NS = {
		"x":	"adobe:ns:meta/",
		"rdf":	"http://www.w3.org/1999/02/22-rdf-syntax-ns#",
		"dc":	"http://purl.org/dc/elements/1.1/",
		"xmp":	"http://ns.adobe.com/xap/1.0/",
	}

	def __init__(self, xmp_filename):
		self._xmp_filename = xmp_filename

	def scan(self):
		if not os.path.isfile(self._xmp_filename):
			return { }

		meta_xml = lxml.etree.parse(self._xmp_filename).getroot()
		tags = collections.defaultdict(set)
		if meta_xml is not None:
			desc = meta_xml.xpath("/x:xmpmeta/rdf:RDF/rdf:Description[1]", namespaces = self._XMP_NS)[0]
			bag = desc.xpath("./dc:subject/rdf:Bag/rdf:li", namespaces = self._XMP_NS)
			for tag_node in bag:
				tag = tag_node.text
				if "=" in tag:
					(key, values) = tag.split("=", maxsplit = 1)
					values = values.split("+")
					tags[key] |= set(values)
		tags = { key: list(values) for (key, values) in tags.items() }
		return tags
