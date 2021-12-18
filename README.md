# calendargen
calendargen is a tool to generate photo calendars so that they are personalized
(e.g., different birthdays for different people) and so that they are a little
bit different for everyone else (i.e., the subset of chosen images from a given
image pool is randomized). There are specific rules that can influence image
placement (e.g., how much time needs to have passed between images) and
specific images can be used only for calendars (e.g., images of a person X
might never appear in a calendar of person Y). These tags are currently read
from the XMP metadata that geeqie produces.

Calendargen is highly parallelized so that rendering is fast even with high
resolution.

## Working principle
There are two distinct functions:

  * **Calandar generation:** This takes a JSON definition file that is written
    in high level and specifies what holidays there are, who the persons are to
    generate calendars for and what year the calendar is for. The output is a JSON
    "layout" file.
  * **Layout rendering:** This takes a JSON layout file as input and renders it
    to specific rules. Essentially, it uses inkscape to render many layers and
    it uses ImageMagick to layer them on top of each other. This process knows
    nothing about calendars anymore or dates, it is purely taking instructions from
    the layout file.

## Pool selection
After you have created a subdirectory with photos you like, you might want to
tag them. For this purpose, you can add tags of the form `key=value` or
`key=value1+value2+value3`. These are the possible `key` values which
calendargen recognizes:

  * `grp=a5102b1be2b0f5e0`: This defines a "group", here it's just called a
    random string. Two images in the same group will never appear together.
    Similar images can be put in the same group to force a maximum of one image of
    that group to be shown.
  * `only=foobar`: This image will only ever show up in the calendar named
    "foobar", never in any other calendars.
  * `force=foobar`: This image is guaranteed to be included in the calendar of
    `foobar`.
  * `gravity=northeast`: When this image needs to be cropped, the northeast
    part of the image is preserved as much as possible.

## Example
You can play around with the calendar definition file in
`example_calendar.json`. First you create a layout:

```
$ ./calgen create-layout example_calendar.json -o my_calendars
```

This will create three layout files: `my_calendars/alice.json`,
`my_calendars/bob.json` and `my_calendars/eve.json`. Initially you might want
to look at the generated symlinks to validate the image selection was done
well. If one calendar didn't suit you, you can either edit the calendar file
manually and remove the offending image from the "images" section (just set it
to 'null') and then re-render the calendar:

```
$ ./calgen create-layout example_calendar.json -o my_calendars
```

Alternatively, you can just ask it to re-roll the whole selection process for
just an individual calendar (for example, for `bob`):

```
$ ./calgen create-layout example_calendar.json -o my_calendars -V bob --reassign-images -f
```

Once you're satisfied with the image selection, you can render them (in low definition):

```
$ ./calgen render my_calendars/*.json
```

And once that looks good, you can render them in top quality for submission to
a printing service:

```
$ ./calgen render --resolution-dpi=600 my_calendars/*.json
```

The help pages (described below) will give you more ideas on what you can do.

## Help pages
```
$ ./calgen create-layout --help
usage: ./calgen create-layout [-r] [-f] [-o dirname] [-c] [-V variant_name]
                              [-v] [--help]
                              input_calendar_file

Create layout files from a calendar definition template.

positional arguments:
  input_calendar_file   JSON calendar definition input file.

optional arguments:
  -r, --reassign-images
                        By default, even when overwriting the output file, at
                        least the image assignments are kept instead of
                        overwritten. This switch ignores previous image
                        assignments and reassigns all images from scratch.
  -f, --force           Force overwriting of already rendered templates if
                        they exist.
  -o dirname, --output-dir dirname
                        Output directory in which genereated calendars reside.
                        Defaults to generated_calendars.
  -c, --no-create-symlinks
                        Do not create symlinks to the images selected from the
                        pool.
  -V variant_name, --only-variant variant_name
                        Only create these variants. Can be specified multiple
                        times. By default, all variants are created that are
                        defined in the template.
  -v, --verbose         Increases verbosity. Can be specified multiple times
                        to increase.
  --help                Show this help page.
```


```
$ ./calgen render --help
usage: ./calgen render [--job-graph filename] [-f] [--wait-keypress]
                       [--no-flatten-output] [--remove-output-dir] [-p pageno]
                       [-r {jpg,png,svg}] [-o dirname] [-d dpi] [-v] [--help]
                       input_layout_file [input_layout_file ...]

Render the pages of a layout file into multiple images, one per page.

positional arguments:
  input_layout_file     JSON definition input file(s) which should be rendered

optional arguments:
  --job-graph filename  Write a GraphViz document that plots the graph
                        dependencies. Useful for debugging.
  -f, --force           Force overwriting of already rendered files if they
                        exist.
  --wait-keypress       Wait for keypress before finishing to be able to debug
                        the temporary files which were generated.
  --no-flatten-output   Do not flatten the output image.
  --remove-output-dir   Remove already rendered output directory if it exists.
  -p pageno, --page pageno
                        Render only defined page(s). Can be either a number
                        (e.g., "7") or a range (e.g., "7-10"). Defaults to all
                        pages.
  -r {jpg,png,svg}, --output-format {jpg,png,svg}
                        Determines what the rendered output is. Can be one of
                        jpg, png, svg, defaults to jpg.
  -o dirname, --output-dir dirname
                        Output directory in which genereated calendars reside.
                        Defaults to generated_calendars.
  -d dpi, --resolution-dpi dpi
                        Resolution to render target at, in dpi. Defaults to 72
                        dpi.
  -v, --verbose         Increases verbosity. Can be specified multiple times
                        to increase.
  --help                Show this help page.
```

## Debugging
When debugging the jobs server, it is useful to have a visual representation of
the dependency graph to see what's going on exactly. For this purpose, you can
create a GraphViz graph that you'll be able to plot. For example:

```
$ ./calgen render --job-graph graph.dot calendar.json
$ dot -o graph.png -T png graph.dot
```

This will create a `graph.png` image which shows all the jobs and their
respective dependencies.

## License
GNU GPL-3.
