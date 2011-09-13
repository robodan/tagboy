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

tagboy.py uses similar concepts and arguments to find(1), but acts on
tags.  We use new style argument names (double dash before
multi-character arguments), and some arguments can be repeated.
Unlike find, argument order doesn't matter (but repeated arguments
execute from left to right).

There are three basic phases of execution:
  Find files using: --iname or --name, or just pass on the command line
  Select based on the files tags using: --grep or --eval
  Show something using: --print, --ls, --echo, --symlink, or --eval

If multiple --iname or --name options are given, continue if ANY of
them match.

if multiple --grep options are given, only continue of ALL of them
match.

For --echo, $TAG or ${TAG} will expand into the files value for that
tag.  If the file doesn't have that tag, then it will passed through
unchanged.  In addition to file tags, the program defines: _filename
and _filepath.
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
addition, the program defines: filename, filepath, filecount, version,
and skip.  The skip variable defaults to 0.  If the --eval sets skip
to a non False value, further processing (e.g. --grep, --ls, --print)
will be skipped.

Usage:
  tagboy.py ./ --iname '*.jpg' --ls
  tagboy.py ./ --iname '*.jpg' --echo '$_filename_: ${Keywords}'
  tagboy.py ./ --iname '*.jpg' --grep '.' '*GPS*' --print'
  NOTE: that you need single quotes to keep the shell from expanding *.jpg
"""                             # NOTE: this is also the usage string in help

# This line must also be valid borne shell for Makefile extraction
VERSION='0.5'

#TODO: Field comparisons (more than --eval ?)
#TODO: Field assignments
#TODO: Write/read a sqlite3? database with ???
#TODO: Handle multi-valued fields more nicely
#TODO: Logging/verbose handling
#TODO: Thumbnail extraction
#TODO: Read/write image comments (separate from EXIF comments)
#TODO: Whitelist of interesting tags (others ignored)
#TODO:


import fnmatch
import optparse
import os
import pyexiv2 as ex
import re
import subprocess
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
        self.global_vars[self.VERSION] = VERSION
        self.eval_code = None     # compiled code for each file
        self.echoTemplates = list() # list of echo statement templates
        self.execTemplates = list() # list of exec statement templates
        self.inameGlobs = list()  # list of case converted name globs
        self.greps = list()       # list of (RE, glob)

    def HandleArgs(self, args):
        """Setup argument parsing and return parsed arguments."""
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
            help="Maximum number of directories to descend",
            dest="maxdepth", default=-1)
        parser.add_option(
            "--grep",
            help="search for PATTERN in TAGS_GLOB (repeatable, -v shows match)",
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
            help="Statement(s) to eval before first file",
            dest="do_begin", default=None)
        parser.add_option(
            "--eval",
            help="Statement(s) to eval for each file",
            dest="do_eval", default=None)
        parser.add_option(
            "--end",
            help="Statement(s) to eval after last file",
            dest="do_end", default=None)
        parser.add_option(
            "-l",
            "--long", help="Use only long form tag names",
            action="store_true", dest="long", default=False)
        parser.add_option(
            "-v",
            "--verbose", help="Show more detail",
            action="store_true", dest="verbose", default=False)
        (self.options, pos_args) = parser.parse_args(args)

        # process arguments
        if self.options.linkdir and not os.path.isdir(self.options.linkdir):
            self.Error("linkdir must be an existing directory: %s" %
                       self.options.linkdir)
            sys.exit(1)

        if self.options.symclear and not self.options.linkdir:
            self.Error(
                "Warning: --symclear is ignored if --symlink is not specified")

        for ss in self.options.echoStrings: # convert echo list into templates
            self.echoTemplates.append(TagTemplate(ss))

        for ss in self.options.execStrings: # convert echo list into templates
            self.execTemplates.append(TagTemplate(ss))

        if self.options.do_eval:
            self.eval_code = self.Compile(self.options.do_eval)

        for chk in self.options.iGlobs: # make case insensitive
            self.inameGlobs.append(chk.lower())

        compile_flags = re.IGNORECASE if self.options.igrep else 0
        for pat, targ in self.options.grep:
            self.greps.append((re.compile(pat, compile_flags), targ))

        return pos_args

    def Error(self, msg):
        """Output an error message."""
        print >> sys.stderr, msg

    def Verbose(self, msg):
        """Output a message if verbose is set."""
        if not self.options.verbose:
            return
        print >> sys.stderr, msg

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
            try:
                v = metadata[k].raw_value # raw strings
                #v = metadata[k]           # processed objects
            except ex.ExifValueError:
                continue
            uni[k] = v
            if not self.options.long:
                kwords = k.split('.')
                uni[kwords[-1]] = v
        for k in metadata.iptc_keys:
            try:
                v = metadata[k].raw_value
            except ex.IptcValueError:
                continue
            uni[k] = v
            if not self.options.long:
                kwords = k.split('.')
                uni[kwords[-1]] = v
        for k in metadata.xmp_keys:
            try:
                v = metadata[k].raw_value
            except ex.XmpValueError:
                continue
            uni[k] = v
            if not self.options.long:
                kwords = k.split('.')
                uni[kwords[-1]] = v
        return uni

    def PrintKeyValue(self, d):
        """Pretty print key-values."""
        for k in sorted(d.keys()):
            if not self.options.verbose and k[0] == '_': # internal variable
                continue
            if (not self.options.long and
                not self.options.verbose and k.find('.') >= 0):
                continue            # skip the dotted names
            value = str(d[k])
            if self.options.maxstr > 0 and len(value) > self.options.maxstr:
                value = value[ : self.options.maxstr] + '...'
            print "%45s: %s" % (k, value)

    def SymClear(self):
        """Clear all symbolic links in options.linkdir."""
        for fn in os.listdir(self.options.linkdir):
            dest_path = os.path.join(self.options.linkdir, fn)
            if os.path.islink(dest_path):
                try:            # attempt to unlink
                    os.unlink(dest_path)
                except:
                    pass

    def SymLink(self, fn):
        """Make a symbolic link to file from options.linkdir."""
        if not self.options.linkdir:
            return
        # TODO: be clever and use relative paths if possible
        abs_path = os.path.abspath(fn)
        dest_path = os.path.join(self.options.linkdir, os.path.basename(fn))
        if os.path.exists(dest_path) and os.path.islink(dest_path):
            try:            # attempt to unlink
                os.unlink(dest_path)
            except:
                pass
        try:
            os.symlink(abs_path, dest_path)
            print "ln -s %s %s" % (
                abs_path, self.options.linkdir) # DEBUG/verbose
        except OSError as inst:
            print "Unable to ln -s %s %s: %s" % (
                abs_path, self.options.linkdir, inst) # DEBUG/verbose

    def CheckMatch(self, fname):
        """Check if path matches a command line match expression."""
        if not self.options.nameGlobs and not self.inameGlobs:
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

    def Grep(self, tags):
        """Check if a pattern shows up in selected tags."""
        all_match = True
        for mpat, tag_glob in self.greps:
            keys = fnmatch.filter(tags.keys(), tag_glob) # Expand tag glob
            #print "Matched keys: ", keys # DEBUG/VERBOSE
            matched = False
            for kk in keys:
                if mpat.search(str(tags[kk])):
                    matched = True
                    if self.options.verbose:
                        print '%s: %s' % (kk, tags[kk])
                    else:
                        break
            if not matched:     # all grep options must match
                all_match = False
        return all_match

    def AllExec(self, var_list):
        """Run all --exec commands."""
        for et in self.execTemplates:
            cmd = et.safe_substitute(var_list)
            if self.options.verbose or self.options.noexec:
                print "Executing: %s" % (cmd)
            if self.options.noexec:
                continue
            p = subprocess.Popen(cmd, shell=True)
            sts = os.waitpid(p.pid, 0)[1]

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
        if not self.options.do_begin:
            return
        self.global_vars[self.FILECOUNT] = self.file_count
        code = self.Compile(self.options.do_begin)
        self.Eval(code, {})

    def EachDir(self, parg):
        """Handle directory walk."""
        # TODO Python 2.6+ supports followlinks=True
        if parg[-1] == os.sep: # trim final slash
            parg = parg[:-1]
        base_count = parg.count(os.sep)
        for root, dirs, files in os.walk(parg):
            depth = root.count(os.sep) - base_count
            #print "walk:", root, dirs, depth # DEBUG
            if (self.options.maxdepth >= 0
                and depth >= self.options.maxdepth):
                del dirs[:] # trim all sub directories
            else:        
                for d in dirs:
                    if d.startswith('.'): # ignore hidden directories
                        dirs.remove(d)
            for fn in files:
                if not self.CheckMatch(fn):
                    continue
                self.EachFile(os.path.join(root, fn))

    def EachFile(self, fn):
        """Handle one file."""
        meta = self.ReadMetadata(fn)
        if not meta:
            return
        if self.file_count == 0:
            self.DoStart()
            if self.options.linkdir and self.options.symclear:
                self.SymClear()
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
        if self.greps and not self.Grep(unified):
            return
        if self.options.printpath:
            print fn
        if self.options.ls:
            print "==== %s ====" % (fn)
            self.PrintKeyValue(unified)
        for et in self.echoTemplates:
            out = et.safe_substitute(unified)
            print out
        if self.execTemplates:
            self.AllExec(unified)
        if self.options.linkdir:
            self.SymLink(fn)            

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
                tb.EachDir(parg)
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
