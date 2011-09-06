#!/usr/bin/env python
# As cowboys wrangle cows, tagboy wrangles EXIF/IPTC/XMP tags in images.
# Uses pyexiv2 (and therefore libexiv2) for tag reading/writing.
# Dan Christian
# 5 Sept 2011

# Features:
# Be able to take filename on the command line or stdin (e.g. find)
# Be able to search directory trees for files matching patterns
# Be able to select files based on tag patterns
# Be able to write/insert/append to tag fields (include from other fields)

"""As cowboys wrangle cows, tagboy wrangles EXIF/IPTC/XMP tags in images.
Usage:
  tagboy --match '*.location=Phoenix' --print
"""

import sys
import pyexiv2 as ex

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
                      action="append", dest="nameGlob", default=[])
    parser.add_option("-v", "--verbose", help="Show more detail",
                      action="store_true", dest="verbose", default=False)
    return parser.parse_args(args)

def PrintKeyValue(d):
    """Pretty print key-values."""
    for k in sorted(d.keys()):
        print "%40s: %s" % (k, d[k])

def EachFile(fn):
    meta = ReadMetadata(fn)
    if not meta:
        return
    unified = FlattenTags(meta)
    print "========= %s =========" % (fn)
    PrintKeyValue(unified)  # DEBUG
    #print "Everything:", unified # DEBUG
    #print "EXIF", meta.exif_keys # DEBUG
    #print "IPTC", meta.iptc_keys # DEBUG
    #print "XMP", meta.xmp_keys   # DEBUG
    
def main():
    (options, args) = HandleArgs(sys.argv[1:])
    print "tagboy begins:", options, args # DEBUG
    if options.nameGlob:
        print "Oops:  --name isn't supported yet"
    if options.verbose:
        print "Oops: verbose isn't... yet"
    for fn in args:
        # TODO: if ends in / (or \\), do directory traverse
        # TODO: check name against nameGlob, inameGlob, nameRegex
        EachFile(fn)

if __name__ == '__main__':
    main()
