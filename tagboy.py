#!/usr/bin/env python
# As cowboys wrangle cows, tagboy wrangles EXIF/IPTC/XMP tags in images.
# Uses pyexiv2 (and therefore libexiv2) for tag reading/writing.
# Dan Christian
# 5 Sept 2011

# Features:
# Be able to take filename on the command line (??? or stdin (e.g. find))
# Be able to search directory trees for files matching patterns
# Be able to select files based on tag patterns
# Be able to write/insert/append to tag fields (include from other fields)

"""As cowboys wrangle cows, tagboy wrangles EXIF/IPTC/XMP tags in images.

Usage:
  tagboy --match '*.location=Phoenix' --print
"""

import os
import pyexiv2 as ex
import string
import sys

# hmm? use backported argparse: http://code.google.com/p/argparse/
import optparse                 # because argparse requires python >= 2.7

def ReadMetadata(fname):
    """Read file metadata and return."""
    metadata = ex.ImageMetadata(fname)
    try:
        metadata.read()
    except IOError:
        print "Error reading: %s" % fname
        metadata = None         # force object distruction
    return metadata

def FlattenTags(metadata):
    """Convert all tags to a dictionary with a uniform naming style.

    We store both the fully qualified name and the short name.
    For short names, XMP has precedence over IPTC over EXIF.
    """
    uni = dict()
    # BUG? XMP has a copy of everything in EXIF
    for k in metadata.exif_keys:
        kwords = k.split('.')
        try:
            v = metadata[k].raw_value
        except ex.ExifValueError:
            continue
        uni[k] = v
        uni[kwords[-1]] = v
    for k in metadata.iptc_keys:
        kwords = k.split('.')
        try:
            v = metadata[k].raw_value
        except ex.IptcValueError:
            continue
        uni[k] = v
        uni[kwords[-1]] = v
    for k in metadata.xmp_keys:
        kwords = k.split('.')
        try:
            v = metadata[k].raw_value
        except ex.XmpValueError:
            continue
        uni[k] = v
        uni[kwords[-1]] = v
    return uni

def HandleArgs(args):
    """Setup argument parsing and return parsed arguments."""
    parser = optparse.OptionParser()
    parser.add_option("--name", help="Match files with this name (repeatable)",
                      action="append", dest="nameGlobs", default=[])
    parser.add_option("--echo", help="Echo argument with $vars (repeatable)",
                      action="append", dest="echoStrings", default=[])
    parser.add_option("--ls", help="Show image info",
                      action="store_true", dest="ls", default=False)
    parser.add_option("-v", "--verbose", help="Show more detail",
                      action="store_true", dest="verbose", default=False)
    return parser.parse_args(args)

def PrintKeyValue(d, verbose):
    """Pretty print key-values."""
    for k in sorted(d.keys()):
        if not verbose and k.find('.') >= 0:
            continue            # skip the dotted names
        print "%40s: %s" % (k, d[k])

FILENAME = '_filename_'
FILEPATH = '_filepath_'

def EachFile(fn, options):
    meta = ReadMetadata(fn)
    if not meta:
        return
    unified = FlattenTags(meta)
    unified[FILEPATH] = fn
    unified[FILENAME] = os.path.basename(fn)
    if options.ls:
        print "========= %s =========" % (fn)
        PrintKeyValue(unified, options.verbose)  # DEBUG
    for ss in options.echoStrings:
        out = string.Template(ss).safe_substitute(unified)
        print out
    
def main():
    (options, args) = HandleArgs(sys.argv[1:])
    print "tagboy begins:", options, args # DEBUG
    if options.nameGlobs:
        print "Oops:  --name isn't supported yet"
    for fn in args:
        # TODO: if ends in / (or \\), do directory traverse
        # TODO: check name against nameGlob, inameGlob, nameRegex
        EachFile(fn, options)

if __name__ == '__main__':
    main()
