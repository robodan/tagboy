As cowboys wrangle cows, tagboy wrangles EXIF/IPTC/XMP tags in images.
Dan Christian
5 Sept 2011

Notes:

The main user documentation is the built in help:  tagboy.py -h

--echo can't do anything that --eval can't do, but it's easier to
understand (and safer).  

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
  Move most of this into a man page
  More unit tests and regression tests
  Expose typed tags in begin/eval/end (e.g. maybe called tagobj)
  Write changed tag value back to image
  Error handling
  Work out some real use examples: near GPS position, near time, time adjust

EXAMPLES:
NOTE: single quotes are necessary to keep the shell from expanding *.jpg

tagboy.py ./ --iname '*.jpg' --grep '.' '*GPS*' --print'
# Different way to find images with GPS info

tagboy.py ./ --iname '*.jpg' \
  --eval 'skip= 0 if tags.has_key("GPSTag") else 1' --ls
# Find images with GPS info using --eval

tagboy.py ./ --iname '*.jpg' \
  --begin 'print "hello world %s" %version' \
  --end 'print "did %d" % (filecount)' \
  --eval 'print "each %s: %s" % (filename, filepath)'  \
  --echo '$_filename: ${Keywords}'
# Demonstrate begin/eval/end use and how --echo uses different notation
# Note that 'Keywords' is the name of a tag

tagboy.py tests/ --iname '*.jpg' \
  --beginfile tests/testdata/tagcount-begin.py \
  --evalfile tests/testdata/tagcount-eval.py \
  --endfile tests/testdata/tagcount-end.py  
# Similar to above, but using files

tagboy.py ./ --iname '*.jpg' --ls
# This will recursively run a case-insensitive search below the 
# current directory on any file that ends with .jpg and list the
# file names

tagboy.py ./ --iname '*.jpg' --echo '$_filename: ${Copyright}'
# This will recursively run a case-insensitive search below the 
# current directory on any file that ends with .jpg and show
# the filename and the contents of the tag "Copyright".  If there
# is no match, that is that tag is empty, then the output will
# will be a literal "${Copyright}".

tagboy.py ./ --name '*.jpg' --grep '.' '*GPS*' --print'
# This will recursively run a case-matching search below the 
# current directory on any file that ends with .jpg and print
# out the filename of any file that contains any value in a tag
# with the name that containing GPS, like GPSLatitude, 
# GPSLongitude, GPSAltitude, etc.  Tag names are case sensitive.  
# Try --ls to see what the exact tag name is 

tagboy.py ./ --iname '*.jpg' --maxdepth=1 \
  --grep 'Bob' '?rtist' --grep '[S|s]huttle' 'Description' \
  --symclear --symlink=../Photos
# This will run a case-insensitive search in the current directory
# and one directory deeper searching for the text "Bob" in tags 
# named "Artist" or "artist" (technically, the "?" will match any 
# letter, so if there was a tag named brtist, krtis, mrtist,
# and xrtist they too would match) that also have the text 
# "Shuttle" or "shuttle" in the tag named "Description".  Files
# that match will have symlinks put in the directory ../Photos AFTER
# any existing symlinks have been removed.

