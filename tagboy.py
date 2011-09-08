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

This has similar concepts and arguments to find(1), but acts on tags.
We use new style argument names (double dash before multi-character
arguments), and many arguments can be repeated.  Unlike find(1),
argument order doesn't matter.

Usage:
  tagboy ./ --iname '*.jpg' --ls
  note: that you need single quotes to keep the shell from expanding *.jpg
"""                             # NOTE: this is also the usage string in help
_VERSION='0.1'

import fnmatch
# hmm? use backported argparse: http://code.google.com/p/argparse/
import optparse                 # because argparse requires python >= 2.7
import os
import pyexiv2 as ex
import string
import sys


class TagBoy(object):
    FILENAME = '_filename_'
    FILEPATH = '_filepath_'

    def ReadMetadata(self, fname):
        """Read file metadata and return."""
        metadata = ex.ImageMetadata(fname)
        try:
            metadata.read()
        except IOError:
            print "Error reading: %s" % fname
            metadata = None         # force object distruction
        return metadata

    def FlattenTags(self, metadata):
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

    def HandleArgs(self, args):
        """Setup argument parsing and return parsed arguments."""
        parser = optparse.OptionParser(usage=__doc__)
        parser.add_option(
            "--iname",
            help="Match files (supports ?*[]) with this case insensitive name (repeatable)",
            action="append", dest="inameGlobs", default=[])
        parser.add_option(
            "--name",
            help="Match files (supports ?*[]) with this name (repeatable)",
            action="append", dest="nameGlobs", default=[])
        parser.add_option(
            "--echo",
            help="Echo argument with $vars (repeatable)",
            action="append", dest="echoStrings", default=[])
        parser.add_option(
            "--ls",
            help="Show image info (more with -v)",
            action="store_true", dest="ls", default=False)
        parser.add_option(
            "-v",
            "--verbose", help="Show more detail",
            action="store_true", dest="verbose", default=False)
        (self.options, pos_args) = parser.parse_args(args)

        self.echoTemplates = list() # convert echo list into templates
        for ss in self.options.echoStrings:
            # TODO: subclass Template to allow . in variable pattern
            self.echoTemplates.append(string.Template(ss))
        return pos_args

    def PrintKeyValue(self, d):
        """Pretty print key-values."""
        for k in sorted(d.keys()):
            if not self.options.verbose and k.find('.') >= 0:
                continue            # skip the dotted names
            print "%40s: %s" % (k, d[k])


    def CheckMatch(self, fname):
        """Check if path matches a command line match expression."""
        if not self.options.nameGlobs and not self.options.inameGlobs:
            return True         # Nothing means match all
        for chk in self.options.inameGlobs: # First try case insensitive
            if fnmatch.fnmatch(fname, chk):
                return True
        for chk in self.options.nameGlobs:
            if fnmatch.fnmatchcase(fname, chk):
                return True
        # TODO: path match
        return False

    def EachFile(self, fn):
        meta = self.ReadMetadata(fn)
        if not meta:
            return
        unified = self.FlattenTags(meta)
        unified[self.FILEPATH] = fn
        unified[self.FILENAME] = os.path.basename(fn)
        if self.options.ls:
            print "========= %s =========" % (fn)
            self.PrintKeyValue(unified)
        for et in self.echoTemplates:
            out = et.safe_substitute(unified)
            print out
    
def main():
    tb = TagBoy()
    args = tb.HandleArgs(sys.argv[1:])
    if not args:
        print "No arguments.  Nothing to do."
        return
    for parg in args:
        if os.path.isdir(parg):
            # TODO Python 2.6+ supports following links with followlinks=True
            for root, dirs, files in os.walk(parg):
                #print "DEBUG: walk", root, dirs, files
                for d in dirs:
                    if d.startswith('.'): # ignore hidden directories
                        dirs.remove(d)
                for fn in files:
                    if not tb.CheckMatch(fn):
                        continue
                    tb.EachFile(os.path.join(root, fn))
        elif os.path.isfile(parg):
            tb.EachFile(parg)
        else:
            print "Can't find a file/directory named: %s" % (fn)

if __name__ == '__main__':
    main()
