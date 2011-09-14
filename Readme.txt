As cowboys rangle cows, tagboy rangles EXIF/IPTC/XMP tags in images.
Dan Christian
5 Sept 2011

Notes:

--echo can't do anything that --eval can't do, but it's easier to
understand (and safer).  

Our special variables start with _ in --echo and --ls, but not in
begin/eval/end.  This is to distinguish them from tags.

--begin/eval/end execute python code in a restricted environment.
This still may not be secure.  It requires users to understand python
for advanced functionality. Making these arguments repeatable may be
useful for command line organization.  Files to execute would also be
helpful (and allow syntax aware editing).

Tags have types.  pyexiv2 is good at maintaining type (although we
bypass much of it right now) and allowing logical (in python) options
for that type.  Multi-value tags, rational numbers, dates, and curves
may require special handling.

Figuring out how to select images based on tags is still TBD.  One
possibility:  have an --eval set skip=1 if it should skip that
file.

The test data is severely trimmed for size.  Our priority is tags,
thumbnails, and (lastly) the image.


Examples:
# Different way to find images with GPS info
tagboy.py ./ --iname '*.jpg' --grep '.' '*GPS*' --print'

# Find images with GPS info using --eval
tagboy.py ./ --iname '*.jpg' \
  --eval 'skip= 0 if tags.has_key("GPSTag") else 1' --ls

# Demonstrate begin/eval/end use and how --echo uses different notation
# Note that 'Keywords' is the name of a tag
tagboy.py ./ --iname '*.jpg' \
  --begin 'print "hello world %s" %version' \
  --end 'print "did %d" % (filecount)' \
  --eval 'print "each %s: %s" % (filename, filepath)'  \
  --echo '$_filename: ${Keywords}'

EXAMPLES:
  NOTE: single quotes are necessary to keep the shell from expanding *.jpg

   tagboy.py ./ --iname '*.jpg' --ls
        This will recursively run a case-insensitive search below the 
        current directory on any file that ends with .jpg and list the
        file names

  tagboy.py ./ --iname '*.jpg' --echo '$_filename: ${Copyright}'
        This will recursively run a case-insensitive search below the 
        current directory on any file that ends with .jpg and show
        the filename and the contents of the tag "Copyright".  If there
        is no match, that is that tag is empty, then the output will
        will be a literal "${Copyright}.

  tagboy.py ./ --name '*.jpg' --grep '.' '*GPS*' --print'
        This will recursively run a case-matching search below the 
        current directory on any file that ends with .jpg and print
        out the filename of any file that contains any value in a tag
        with the name that containing GPS, like GPSLatitude, 
        GPSLongitude, GPSAltitude, etc.  Tag names are case sensitive.  
        Try --ls to see what the exact tag name is 

  tagboy.py ./ --iname '*.jpg' --maxdepth=1 --grep 'Bob' '?rtist' --grep '[S|s]huttle' 'Description' --symclear --symlink=../Photos
       This will run a case-insensitive search in the current directory
       and one directory deeper searching for the text "Bob" in tags 
       named "Artist" or "artist" (technically, the "?" will match any 
       letter, so if there was a tag named bartist, kartis, martist,
       and xartist they too would match) that also have the text 
       "Shuttle" or "shuttle" in the tag named "Description".  Files
       that match will have symlinks put in the directory ../Photos AFTER
       any existing symlinks have been removed.

