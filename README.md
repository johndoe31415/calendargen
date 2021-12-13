
## Tags
Supported tags:
	* grp=a5102b1be2b0f5e0
      Two images in the same group will never appear together. Similar images can be put in the same group to force a maximum of one image of that group to be shown.
	* only=foobar
    * force=foobar
    * prob=2


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
