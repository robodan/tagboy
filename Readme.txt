As cowboys wrangle cows, tagboy wrangles EXIF/IPTC/XMP tags in images.
Dan Christian
5 Sept 2011

Notes:

The main user documentation is the man page tagboy.1 or the built in
help: tagboy -h

--echo is a subset of --eval, but it's easier to understand (and
safer).

Our special variables start with _ in --echo and --exec, but not in
begin/eval/end.  This is somewhat confusing, but necessary to
distinguish them from tag names.

--begin/eval/end and --beginfile/evalfile/endfile execute python code
in a restricted environment, but they can still do things like open
arbitrary files.  Never pass in code from un-trusted sources. 

All --beginfile options run before all --begin options (and likewise
for --eval and --end).

Tags have types.  pyexiv2 is good at maintaining type (although we
bypass much of it right now) and allowing logical (in python) options
for that type.  Multi-value tags, rational numbers, dates, and curves
may require special handling.  We need to at least expose typed values
in --begin/eval/end.

The test data is severely trimmed for size.  Our priority is tags,
thumbnails, and (lastly) the image.

TODO:
  Include helper routines to make dates easier to compare
  Write changed tag value back to image
  Error handling
  Work out some real use examples: near time, time adjust
