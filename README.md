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
