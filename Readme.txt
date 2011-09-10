As cowboys rangle cows, tagboy rangles EXIF/IPTC/XMP tags in images.
Dan Christian
5 Sept 2011

Notes:

--echo can't do anything that --eval can't do, but it's easier to
understand (and safer).

--begin/eval/end execute python code in a restricted environment.
This still may not be secure.  It requires users to understand python
for advanced functionality. Making these arguments repeatable may be
useful for command line organization.  Files to execute might also be
helpful (and allow syntax aware editing).

Tags have types.  pyexiv2 is good a maintaining type (although we
bypass much of it right now) and allowing logical (in python) options
for that type.  Multi-value tags, rational numbers, dates, and curves
may require special handling.

Figuring out how to select images based on tags is still TBD.  One
possibility:  have an --eval set _skip_=True if it should skip that
file.


