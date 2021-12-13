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

import sys
from .MultiCommand import MultiCommand
from .ActionRender import ActionRender
#from .TemplateCalendarCommand import TemplateCalendarCommand
#from .ScanPoolCommand import ScanPoolCommand
#from .SelectPoolCommand import SelectPoolCommand

def _pagedef(page_str):
	if "-" in page_str:
		(from_page, to_page) = page_str.split("-", maxsplit = 1)
		return (int(from_page), int(to_page))
	else:
		page = int(page_str)
		return (page, page)


def main():
	mc = MultiCommand()

#	def genparser(parser):
#		parser.add_argument("-f", "--force", action = "store_true", help = "Force overwriting of already rendered templates if they exist.")
#		parser.add_argument("-o", "--output-dir", metavar = "dirname", default = "generated_calendars", help = "Output directory in which genereated calendars reside. Defaults to %(default)s.")
#		parser.add_argument("-c", "--no-create-symlinks", action = "store_true", help = "Do not create symlinks for selected images.")
#		parser.add_argument("-V", "--only-variant", metavar = "variant_name", help = "Only create this variant.")
#		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
#		parser.add_argument("input_file", help = "JSON definition input file which specifies the calendar definition specifics.")
#	mc.register("template", "Create calendar definition files based on a template.", genparser, action = TemplateCalendarCommand)

	def genparser(parser):
		parser.add_argument("-f", "--force", action = "store_true", help = "Force overwriting of already rendered files if they exist.")
		parser.add_argument("--wait-keypress", action = "store_true", help = "Wait for keypress before finishing to be able to debug the temporary files which were generated.")
		parser.add_argument("--no-flatten-output", action = "store_true", help = "Do not flatten the output image.")
		parser.add_argument("--remove-output-dir", action = "store_true", help = "Remove already rendered output directory if it exists.")
		parser.add_argument("-p", "--page", metavar = "pageno", type = _pagedef, action = "append", default = [ ], help = "Render only defined page(s). Can be either a number (e.g., \"7\") or a range (e.g., \"7-10\"). Defaults to all pages.")
		parser.add_argument("-r", "--output-format", choices = [ "jpg", "png", "svg" ], default = "jpg", help = "Determines what the rendered output is. Can be one of %(choices)s, defaults to %(default)s.")
		parser.add_argument("-o", "--output-dir", metavar = "dirname", default = "generated_calendars", help = "Output directory in which genereated calendars reside. Defaults to %(default)s.")
		parser.add_argument("-d", "--resolution-dpi", metavar = "dpi", type = int, default = 72, help = "Resolution to render target at, in dpi. Defaults to %(default)d dpi.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
		parser.add_argument("input_file", nargs = "+", help = "JSON definition input file(s) which should be rendered")
	mc.register("render", "Render a calendar based on a calendar definition file.", genparser, action = ActionRender)

#	def genparser(parser):
#		parser.add_argument("-g", "--link-groups", metavar = "output_dir", help = "Create symbolic links to all groups so the images can be reviewed easily.")
#		parser.add_argument("-c", "--cache-file", metavar = "filename", default = "pool_cache.json", help = "Image pool cache filename. Defaults to %(default)s.")
#		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
#		parser.add_argument("image_directory", nargs = "+", help = "Directory which should be scanned.")
#	mc.register("scanpool", "Scan an image pool.", genparser, action = ScanPoolCommand)
#
#	def genparser(parser):
#		parser.add_argument("-o", "--link-images", metavar = "output_dir", help = "Create symbolic links to all selected images so they can be reviewed easily.")
#		parser.add_argument("-s", "--set-name", metavar = "name", help = "Name to preselect images from. Influences image selection by the 'forced' and 'only' keywords.")
#		parser.add_argument("-c", "--cache-file", metavar = "filename", default = "pool_cache.json", help = "Image pool cache filename. Defaults to %(default)s.")
#		parser.add_argument("-n", "--image-count", metavar = "count", type = int, default = 12, help = "Number of images to choose form the pool. Defaults to %(default)d.")
#		parser.add_argument("-r", "--runs", metavar = "count", type = int, default = 1, help = "Number of selection runs to do before settling on the final version. Defaults to %(default)d.")
#		parser.add_argument("--no-remove-groups", action = "store_true", help = "Do not remove grouped images if one is chosen.")
#		parser.add_argument("--remove-time-window", metavar = "secs", type = int, help = "When choosing an image, remove all images that were taken this amount of seconds before or after the reference image.")
#		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
#		parser.add_argument("image_directory", nargs = "+", help = "Directory which should be scanned.")
#	mc.register("selectpool", "Select images from an image pool.", genparser, action = SelectPoolCommand)

	mc.run(sys.argv[1:])

if __name__ == "__main__":
	main()
