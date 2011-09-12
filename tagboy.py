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
  tagboy ./ --iname '*.jpg' --echo '$_filename_: ${Keywords}'
  note: that you need single quotes to keep the shell from expanding *.jpg
"""                             # NOTE: this is also the usage string in help

# This line must also be valid borne shell for Makefile extraction
VERSION='0.3'

#TODO: Field comparisons
#TODO: Field assignments
#TODO: Write/read a sqlite3? database with ???
#TODO: Handle multi-valued fields more nicely
#TODO: Logging/verbose handling
#TODO: Thumbnail extraction
#TODO: 'Grep' for strings in a tag glob
#TODO:


import fnmatch
# hmm? use backported argparse: http://code.google.com/p/argparse/
import optparse                 # because argparse requires python >= 2.7
import os
import pyexiv2 as ex
import string
import sys

class TagTemplate(string.Template):
    """Sub-class string.Template to allow . in variable names."""
    idpattern = r'[_a-z][\._a-z0-9]*'
    

class TagBoy(object):
    """Class that implements tag mapulation."""
    # string constants defining the names of fields/variables
    VERSION   = 'version'     # version of tagboy
    FILECOUNT = 'filecount'   # current count of files read
    FILENAME  = 'filename'    # file base name
    FILEPATH  = 'filepath'    # full path
    SKIP      = 'skip'        # set this to end processing of this file
    TAGS      = 'tags'        # dictionary of all tags

    def __init__(self):
        self.file_count = 0       # number of files encountered
        self.global_vars = dict() # 'global' state passed to eval()
        self.eval_code = None     # compiled code for each file
        self.echoTemplates = list() # list of echo statements
        self.global_vars[self.VERSION] = VERSION

    def ReadMetadata(self, fname):
        """Read file metadata and return."""
        metadata = ex.ImageMetadata(fname)
        try:
            metadata.read()
        except IOError:
            self.Error("Error reading: %s" % fname)
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
            "--print",
            help="Print the name of the file",
            action="store_true", dest="printpath", default=False)
        parser.add_option(
            "--begin",
            help="Statement(s) to eval before first file",
            action="store", dest="do_begin", default=None)
        parser.add_option(
            "--eval",
            help="Statement(s) to eval for each file",
            action="store", dest="do_eval", default=None)
        parser.add_option(
            "--end",
            help="Statement(s) to eval after last file",
            action="store", dest="do_end", default=None)
        parser.add_option(
            "-v",
            "--verbose", help="Show more detail",
            action="store_true", dest="verbose", default=False)
        (self.options, pos_args) = parser.parse_args(args)
        self.inameGlobs = list()
        for chk in self.options.inameGlobs: # make case insensitive
            self.inameGlobs.append(chk.lower())
        return pos_args

    def Error(self, msg):
        """Output an error message."""
        print >> sys.stderr, msg

    def Verbose(self, msg):
        """Output a message if verbose is set."""
        if not self.options.verbose:
            return
        print >> sys.stderr, msg

    def PrintKeyValue(self, d):
        """Pretty print key-values."""
        for k in sorted(d.keys()):
            if not self.options.verbose and k[0] == '_': # internal variable
                continue
            if not self.options.verbose and k.find('.') >= 0:
                continue            # skip the dotted names
            print "%40s: %s" % (k, d[k])


    def CheckMatch(self, fname):
        """Check if path matches a command line match expression."""
        if not self.options.nameGlobs and not self.options.inameGlobs:
            return True         # Nothing means match all
        # BUG: fnmatch is only case insensitive if the filesystem is
        for chk in self.inameGlobs: # First try case insensitive
            if fnmatch.fnmatchcase(fname.lower(), chk):
                return True
        for chk in self.options.nameGlobs: # always case sensitive
            if fnmatch.fnmatchcase(fname, chk):
                return True
        # TODO: path match
        return False

    def Compile(self, statements):
        """Our compile with error handling."""
        # TODO: make private
        try:
            code = compile(statements, '<string>', 'exec')
            return code
            c = compile(code, self.global_vars, local_vars)
        except Exception as inst:
            self.Error("Compile failed <%s>: %s"
                       % (inst, self.options.do_eval))
            return None

    def Eval(self, code, local_vars):
        """Our eval with error handling."""
        # TODO: make private
        # TODO: verify security of all this
        try:
            eval(code, self.global_vars, local_vars)
        except Exception as inst:
            self.Error("Eval failed <%s>: %s" % (inst, self.options.do_eval))

    def DoStart(self):
        """Do setup for first file."""
        for ss in self.options.echoStrings: # convert echo list into templates
            self.echoTemplates.append(TagTemplate(ss))
        if self.options.do_begin:
            self.global_vars[self.FILECOUNT] = self.file_count
            code = self.Compile(self.options.do_begin)
            self.Eval(code, {})
        if self.options.do_eval:
            self.eval_code = self.Compile(self.options.do_eval)

    def EachFile(self, fn):
        meta = self.ReadMetadata(fn)
        if not meta:
            return
        if self.file_count == 0:
            self.DoStart()
        self.file_count += 1
        unified = self.FlattenTags(meta)

        skip = False
        if self.options.do_eval:
            local_tags = dict()
            for k, v in unified.iteritems(): # clone tags as variables
                local_tags[k] = v
            self.global_vars[self.FILECOUNT] = self.file_count
            local_vars = dict()
            local_vars[self.TAGS] = local_tags
            local_vars[self.FILEPATH] = fn
            local_vars[self.FILENAME] = os.path.basename(fn)
            local_vars[self.SKIP] = 0
            self.Eval(self.eval_code, local_vars)
            if local_vars[self.SKIP]:
                return
            for k, v in local_tags.iteritems(): # look for changes
                if not unified.has_key(k):
                    # BUG: we should just create the tag (if possible)
                    print "New tag '%s' is ignored" # DEBUG/verbose
                    continue
                if unified[k] != v:
                    print "Oh look, %s changed: %s -> %s (no writes, yet)" % (
                        k, unified[k], v) # DEBUG/verbose
                    # TODO: write changes to meta
                    pass
        unified['_'+self.FILEPATH] = fn
        unified['_'+self.FILENAME] = os.path.basename(fn)
        if self.options.printpath:
            print fn
        if self.options.ls:
            print "==== %s ====" % (fn)
            self.PrintKeyValue(unified)
        for et in self.echoTemplates:
            out = et.safe_substitute(unified)
            print out

    def DoEnd(self):
        """Do setup after last file."""
        if self.file_count == 0:
            return
        if self.options.do_end:
            self.global_vars[self.FILECOUNT] = self.file_count
            code = self.Compile(self.options.do_end)
            self.Eval(code, {})
        
def main():
    tb = TagBoy()
    args = tb.HandleArgs(sys.argv[1:])
    if not args:
        print >> sys.stderr, "No arguments.  Nothing to do."
        return
    try:
        for parg in args:
            if os.path.isdir(parg):
                # TODO Python 2.6+ supports followlinks=True
                for root, dirs, files in os.walk(parg):
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
                print >> sys.stderr, ("Can't find a file/directory named: %s"
                                      % (parg))
    except (KeyboardInterrupt, SystemExit):
        pass
    tb.DoEnd()

if __name__ == '__main__':
    main()
