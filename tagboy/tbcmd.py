#!/usr/bin/env python2

# ******************************************************************************
#
# Copyright (C) 2018 Dan Christian <DanChristian65@gmail.com>
#
# This file is part of tagboy distribution.
#
# tagboy is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# tagboy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagboy; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, 5th Floor, Boston, MA 02110-1301 USA.
#
# Author: Dan Christian <DanChristian65@gmail.com>
#
# ******************************************************************************

# As cowboys wrangle cows, tagboy wrangles EXIF/IPTC/XMP tags in images.
# Uses pyexiv2 (and therefore libexiv2) for tag reading/writing.
# Dan Christian
# 5 Sept 2011
# Requires pyexiv2 0.3+ and python 2.7

# Command line parsing and script execution

# TODO: convert to gexiv2 https://wiki.gnome.org/Projects/gexiv2

# Features:
# Be able to take filenames or directories on the command line
# Be able to search directory trees for files matching patterns
# Be able to select files based on tag patterns
# Be able to write/insert/append to tag fields (include from other fields)

"""As cowboys wrangle cows, tagboy wrangles EXIF/IPTC/XMP tags in images.

USAGE:
  tagboy [path|filename]... [action] [options]

There are three phases of execution:
  Find files: --iname or --name, or just pass on the command line
  Select based on tags: --grep or --eval
  Show/do something: --print, --ls, --echo, --symlink, --exec, or --eval

tagboy uses similar concepts and arguments to find(1), but acts on
tags.  We use new style argument names (double dash before
multi-character arguments), and some arguments can be repeated.
Unlike find, argument order doesn't matter (but repeated arguments
execute from left to right).

If multiple --iname or --name options are given, select a file if ANY
of them match.

if multiple --grep options are given, only continue if ALL of them
match.

If multiple --near options are given, select a file if ANY of them
match.  The special tags _near and _distance will be set to the
nearest match.

For --echo or --exec, $TAG or ${TAG} will expand into the files value
for that tag.  If the file doesn't have that tag, then it will passed
through unchanged.  In addition to file tags, the program defines:
_arg, _filecount, _filename, _filepath, _matchcount, _version.
See:  http://docs.python.org/library/string.html#string.Template

For arguments that take 'globs' (e.g. --iname, --name, grep's tags_glob):
  ?   - matches any single character
  *   - match zero or more characters
  []  - match the letters or range in the brackets.  e.g. [A-z]
        If [] starts with !, then match all except these letters or range.
Unlike shell globbing, {} is not supported (but you can repeat --iname/name).
See:  http://docs.python.org/library/fnmatch.html#module-fnmatch

The --grep PATTERN is a python regular expression:
  .   - match any single character
  []  - match the letters or range in the brackets.  e.g. [A-z]
  [!] - match anything except the letters or range in the brackets.  e.g. [!0-9]
  \d  - match a decimal digit.  \D is anthing except a decimal digit
  \s  - match whitespace.       \S is anthing except whitespace
  \w  - match an alphanumeric.  \W is anthing except an alphanumeric
  *   - match zero or more of the preceeding character or range
  +   - match one or more of the preceeding character or range
  ?   - match zero or one of the preceeding character or range
  ^   - match the start of the string
  $   - match the end of the string
There is MUCH MORE here:  http://docs.python.org/howto/regex.html

For --begin/eval/end, all tags are in a dictionary names 'tags'.  In
addition, the program defines: arg, filecount, filename, filepath,
matchcount, version, and skip.  The skip variable defaults to 0.  If
the --eval sets skip to a non False value, further processing
(e.g. --grep, --ls, --print) will be skipped.

Examples:
  tagboy ./ --iname '*.jpg' --ls
  tagboy ./ --iname '*.jpg' --echo '$_filename: ${Keywords}'
  tagboy ./ --iname '*.jpg' --grep '.' '*GPS*' --print'
  tagboy ./ --iname '*.jpg' --near '37.273852, -107.884577' --distance=99  --print'
  NOTE: that you need single quotes to keep the shell from expanding *.jpg
"""                             # NOTE: this is also the usage string in help

from __future__ import absolute_import
from __future__ import division

# This line must also be valid borne shell for Makefile extraction.  No spaces allowed.
VERSION='0.13'

#TODO: Field comparisons (more than --eval ?)
#TODO: Field assignments
#TODO: Thumbnail extraction
#TODO: Read/write image comments (separate from EXIF comments)
#TODO: Whitelist of interesting tags (others ignored)
#TODO: Write/read a sqlite3? database with ???
#TODO:

import optparse              # deprecated.  TODO:  convert to argparse
import os
import sys

from tbcore import *


def ArgParser():
    parser = optparse.OptionParser(usage=__doc__)
    parser.add_option(
        "--iname",
        help="Match filename using IGLOBS (case is ignored, repeatable)",
        action="append", dest="iGlobs", default=[])
    parser.add_option(
        "--name",
        help="Match filename using NAMEGLOBS (repeatable)",
        action="append", dest="nameGlobs", default=[])
    parser.add_option(
        "--maxdepth", type="int",
        help="Maximum number of directories to descend. 0 means no decent",
        dest="maxdepth", default=-1)
    parser.add_option(
        "-g",
        "--grep",
        help="search for PATTERN in TAGS_GLOB[;GLOB] (repeatable, -v shows match)",
        nargs = 2,
        action="append", dest="grep", default=[])
    parser.add_option(
        "-i",
        "--ignore-case", help="grep PATTERN should be case insensitive",
        action="store_true", dest="igrep", default=False)
    parser.add_option(
        "--print",
        help="Print the name of the file",
        action="store_true", dest="printpath", default=False)
    parser.add_option(
        "--echo",
        help="Echo string with $var substitution (repeatable)",
        action="append", dest="echoStrings", default=[])
    parser.add_option(
        "--exec",
        help="Execute string with $var substitution (repeatable)",
        action="append", dest="execStrings", default=[])
    parser.add_option(
        "-n",
        "--noexec",
        help="Don't actually execute --exec options, just show them.",
        action="store_true", dest="noexec", default=False)
    parser.add_option(
        "--ls",
        help="Show image info (shows long names with -v or --long)",
        action="store_true", dest="ls", default=False)
    parser.add_option(
        "-s",
        "--select",
        help="select tags TAGS_GLOB[;GLOB] (repeatable)",
        action="append", dest="selects", default=[])
    parser.add_option(
        "--near",
        help="match files with GPS position near 'LAT, LON' (repeatable, -v shows match)",
        nargs = 1,
        action="append", dest="near", default=[])
    parser.add_option(
        "--distance",
        help="radius for a --near match in kilometers (default 5)",
        dest="near_dist", default=5)
    parser.add_option(
        "--maxstr", type="int",
        help="Maximum string length to print (default 50, 0 = unlimited)",
        dest="maxstr", default=50)
    parser.add_option(
        "--symlink",
        help="Symlink selected files into LINKDIR",
        dest="linkdir", default=None)
    parser.add_option(
        "--symclear",
        help="Remove all symlinks in LINKDIR before creating new ones",
        action="store_true", dest="symclear", default=False)
    parser.add_option(
        "--begin",
        help="Python statement(s) to run before first file (repeatable)",
        action="append", dest="do_begin", default=[])
    parser.add_option(
        "--eval",
        help="Python statement(s) to run for each file (repeatable)",
        action="append", dest="do_eval", default=[])
    parser.add_option(
        "--end",
        help="Python statement(s) to run after last file (repeatable)",
        action="append", dest="do_end", default=[])
    parser.add_option(
        "--beginfile",
        help="Python file to run before first file (repeatable)",
        action="append", dest="begin_files", default=[])
    parser.add_option(
        "--evalfile",
        help="Python file to run for each file (repeatable)",
        action="append", dest="eval_files", default=[])
    parser.add_option(
        "--arg",
        help="Pass this argument to begin/eval/end",
        dest="argument", default='')
    parser.add_option(
        "--endfile",
        help="Python file to run after last file (repeatable)",
        action="append", dest="end_files", default=[])
    parser.add_option(
        "-L",
        "--follow", help="Follow symbolic links to directories",
        action="store_true", dest="follow", default=False)
    parser.add_option(
        "-l",
        "--long", help="Use only long form tag names",
        action="store_true", dest="long", default=False)
    parser.add_option(
        "-H",
        "--with-filename", help="Show filename for each grep -v",
        action="store_true", dest="withname", default=False)
    parser.add_option(
        "--human", help="Use human friendly names for tags",
        action="store_true", dest="human", default=False)
    parser.add_option(
        "-u",
        "--unknown", help="Show unknown tags",
        action="store_true", dest="unknown", default=False)
    parser.add_option(
        "-v",
        "--verbose", help="Show more detail",
        action="store_true", dest="verbose", default=False)
    parser.add_option(
        "-D",
        "--debug", help="Show internal details",
        action="count", dest="debug", default=0)
    parser.add_option(
        "-V",
        "--version", help="Show version and exit",
        action="store_true", dest="version", default=False)

    return parser


def main():
    tb = TagBoy(version=VERSION)
    parser = ArgParser()
    options, pos_args = parser.parse_args(sys.argv[1:])

    args = tb.HandleArgs(options, pos_args)
    if not args:
        tb.Error("No arguments.  Nothing to do.  Use -h for help.")
        sys.exit(2)
    try:
        for parg in args:
            if os.path.isdir(parg):
                tb.EachDir(parg)
            elif os.path.isfile(parg):
                tb.EachFile(parg)
            else:
                print >> sys.stderr, ("Can't find a file/directory named: %s"
                                      % (parg))
    except (KeyboardInterrupt, SystemExit):
        pass
    if tb.DoEnd():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
