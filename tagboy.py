#!/usr/bin/env python

# ******************************************************************************
#
# Copyright (C) 2011 Dan Christian <DanChristian65@gmail.com>
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
# Requires pyexiv2 0.3+ and python 2.6+

# Features:
# Be able to take filename on the command line (??? or stdin (e.g. find))
# Be able to search directory trees for files matching patterns
# Be able to select files based on tag patterns
# Be able to write/insert/append to tag fields (include from other fields)

"""As cowboys wrangle cows, tagboy wrangles EXIF/IPTC/XMP tags in images.

USAGE:
  tagboy.py [path|filename]... [action] [options]

There are three phases of execution:
  Find files: --iname or --name, or just pass on the command line
  Select based on tags: --grep or --eval
  Show/do something: --print, --ls, --echo, --symlink, --exec, or --eval

tagboy.py uses similar concepts and arguments to find(1), but acts on
tags.  We use new style argument names (double dash before
multi-character arguments), and some arguments can be repeated.
Unlike find, argument order doesn't matter (but repeated arguments
execute from left to right).

If multiple --iname or --name options are given, select a file if ANY
of them match.

if multiple --grep options are given, only continue of ALL of them
match.

For --echo or --exec, $TAG or ${TAG} will expand into the files value
for that tag.  If the file doesn't have that tag, then it will passed
through unchanged.  In addition to file tags, the program defines:
_filename, _filepath, _filecount, _matchcount, _version.  
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
addition, the program defines: filename, filepath, filecount,
matchcount, version, and skip.  The skip variable defaults to 0.  If
the --eval sets skip to a non False value, further processing
(e.g. --grep, --ls, --print) will be skipped.

Examples:
  tagboy.py ./ --iname '*.jpg' --ls
  tagboy.py ./ --iname '*.jpg' --echo '$_filename_: ${Keywords}'
  tagboy.py ./ --iname '*.jpg' --grep '.' '*GPS*' --print'
  NOTE: that you need single quotes to keep the shell from expanding *.jpg
"""                             # NOTE: this is also the usage string in help

# This line must also be valid borne shell for Makefile extraction
VERSION='0.9'

#TODO: Field comparisons (more than --eval ?)
#TODO: Field assignments
#TODO: Thumbnail extraction
#TODO: Read/write image comments (separate from EXIF comments)
#TODO: Whitelist of interesting tags (others ignored)
#TODO: Write/read a sqlite3? database with ???
#TODO: Some kind of diff: show unique tags in dir, show differences from file
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
    VERSION    = 'version'    # version of tagboy
    FILECOUNT  = 'filecount'  # current count of files read
    MATCHCOUNT = 'matchcount' # current count of files read
    FILENAME   = 'filename'   # file base name
    FILEPATH   = 'filepath'   # full path
    SKIP       = 'skip'       # set this to end processing of this file
    TAGS       = 'tags'       # dictionary of all tags

    def __init__(self):
        self.file_count = 0       # number of files encountered
        self.match_count = 0      # number of files 'matched'
        self.global_vars = dict() # 'global' state passed to eval()
        self.global_vars[self.VERSION] = VERSION
        self.begin_code = list()  # list of compiled code for before any file
        self.eval_code = list()   # list of compiled code for each file
        self.end_code = list()    # list of compiled code for after all files
        self.echo_tmpl = list()   # list of echo statement templates
        self.exec_tmpl = list()   # list of exec statement templates
        self.iname_globs = list() # list of case converted name globs
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
            help="Maximum number of directories to descend. 0 means no decent",
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
            "-v",
            "--verbose", help="Show more detail",
            action="store_true", dest="verbose", default=False)
        parser.add_option(
            "-D",
            "--debug", help="Show internal details",
            action="count", dest="debug", default=0)

        (self.options, pos_args) = parser.parse_args(args)

        # process arguments
        if self.options.linkdir and not os.path.isdir(self.options.linkdir):
            self.Error("linkdir must be an existing directory: %s" %
                       self.options.linkdir)
            sys.exit(2)

        if self.options.symclear and not self.options.linkdir:
            self.Error(
                "Warning: --symclear is ignored if --symlink is not specified")

        for ss in self.options.echoStrings: # convert echo list into templates
            self.echo_tmpl.append(TagTemplate(ss))

        for ss in self.options.execStrings: # convert echo list into templates
            self.exec_tmpl.append(TagTemplate(ss))

        # Compile all code first to flush out any errors
        for ss in self.options.begin_files:
            self.begin_code.append(self._CompileFile(ss))
        for ss in self.options.do_begin:
            self.begin_code.append(self._Compile(ss))

        for ss in self.options.eval_files:
            self.eval_code.append(self._CompileFile(ss))
        for ss in self.options.do_eval:
            self.eval_code.append(self._Compile(ss))

        for ss in self.options.end_files:
            self.end_code.append(self._CompileFile(ss))
        for ss in self.options.do_end:
            self.end_code.append(self._Compile(ss))

        for chk in self.options.iGlobs: # make case insensitive
            self.iname_globs.append(chk.lower())

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

    def Debug(self, level, msg):
        """Output a message if debug is set."""
        if self.options.debug < level:
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

    def HumanStr(self, metadata, key):
        """Return the most human readable form of key's value."""
        try:
            if key in metadata.exif_keys:
                return metadata[key].human_value
            return metadata[key].raw_value
        except:
            self.Debug("Error getting value for: %s" % key)
            return ''

    def MakeKeyMap(self, metadata, revmap):
        """Convert all tag names to a name mapping dictionary.

        We store both the fully qualified name and the short name.
        For short names, XMP has precedence over IPTC over EXIF.
        """
        self._MakeKeyMap(metadata.exif_keys, revmap)
        self._MakeKeyMap(metadata.iptc_keys, revmap)
        self._MakeKeyMap(metadata.xmp_keys, revmap)

    def _MakeKeyMap(self, keys, revmap):
        """Insert name mapping into revmap: long->long and short->long."""
        for k in keys:
            revmap[k] = k
            if self.options.long:
                continue
            kwords = k.split('.')
            old_map = revmap.get(kwords[-1], None)
            if self.options.debug and old_map:
                self.Debug(1, "Revmap changed[%s]: %s -> %s"
                           % (kwords[-1], old_map, k))
            revmap[kwords[-1]] = k

    def PrintKeyValue(self, d):
        """Pretty print key-values."""
        max_tag = 0
        for k in sorted(d.keys()): # find longest tag name
            if len(k) > max_tag:
                max_tag = len(k)

        for k in sorted(d.keys()):
            if not self.options.verbose and k[0] == '_': # internal variable
                continue
            if (not self.options.long and
                not self.options.verbose and k.find('.') >= 0):
                continue            # skip the dotted names
            value = str(d[k])
            if self.options.maxstr > 0 and len(value) > self.options.maxstr:
                value = value[ : self.options.maxstr] + '...'
            print "%-*s %s" % (max_tag+1, k + ':', value)

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

        if abs_path == dest_path: # points to itself
            self.Error("Warning: symlink would point to itself: %s" % abs_path)
            return

        if os.path.exists(dest_path) and os.path.islink(dest_path):
            try:                # attempt to unlink
                os.unlink(dest_path)
            except:
                pass
        try:
            os.symlink(abs_path, dest_path)
            self.Verbose("ln -s %s %s" % (abs_path, self.options.linkdir))
        except OSError as inst:
            self.Errof("Unable to ln -s %s %s: %s" % (
                    abs_path, self.options.linkdir, inst))

    def Grep(self, fn, metadata, revmap):
        """Check if a pattern shows up in selected tags."""
        all_match = True
        for mpat, tag_glob in self.greps:
            keys = fnmatch.filter(revmap.keys(), tag_glob) # Expand tag glob
            self.Debug(2, "Matched keys: %s" % keys)
            matched = False
            for kk in keys:
                mk = revmap[kk]
                if mk in metadata.iptc_keys and metadata[mk].repeatable:
                    self.Debug(3, "[%s] = %s " % (mk, metadata[mk].value))
                    for vv in metadata[mk].value:
                        if self._SubGrep(mpat, fn, kk, str(vv)):
                            matched = True
                            if not self.options.verbose:
                                break
                else:
                    if self._SubGrep(mpat, fn, kk, self.HumanStr(metadata, mk)):
                        matched = True
                        if not self.options.verbose:
                            break
            if not matched:     # all grep options must match
                all_match = False
        return all_match

    def _SubGrep(self, mpat, fname, kk, targ):
        if targ is not None and mpat.search(targ):
            if self.options.verbose:
                if self.options.withname:
                    print '%s: %s: %s' % (fname, kk, targ)
                else:
                    print '%s: %s' % (kk, targ)
            return True
        else:
            return False

    def AllExec(self, var_list):
        """Run all --exec commands."""
        for et in self.exec_tmpl:
            cmd = et.safe_substitute(var_list)
            if self.options.verbose or self.options.noexec:
                print "Executing: %s" % (cmd)
            if self.options.noexec:
                continue
            p = subprocess.Popen(cmd, shell=True)
            sts = os.waitpid(p.pid, 0)[1]

    def _Compile(self, statements, source=None):
        """Our compile with error handling."""
        if not source:
            source = '<string>'
        try:
            code = compile(statements, source, 'exec')
            return code
        except Exception as inst:
            if len(statements) > 80:
                statements = statements[:80] + '...'
            self.Error("Compile failed <%s>: %s"
                       % (inst, statements))
            sys.exit(2)

    def _CompileFile(self, fd_or_path, source=None):
        """Read and compile python code from a file name or descriptor."""
        if isinstance(fd_or_path, basestring):
            try:
                fd = open(fd_or_path, 'r')
                if not source:
                    source = fd_or_path
            except IOError:
                self.Error("Unable to read: %s" % fd_or_path)
                sys.exit(2)
        else:
            fd = fd_or_path
        return self._Compile(fd.read(), source)

    def _Eval(self, code, local_vars):
        """Our eval with error handling."""
        try:
            eval(code, self.global_vars, local_vars)
        except Exception as inst:
            self.Error("Eval failed <%s>: %s" % (inst, code))

    def DoStart(self):
        """Do setup for first file."""
        if not self.begin_code:
            return
        self.global_vars[self.FILECOUNT] = self.file_count
        for cc in self.begin_code:
            self._Eval(cc, {})

    def CheckMatch(self, fname):
        """Check if path matches a command line match expression."""
        if not self.options.nameGlobs and not self.iname_globs:
            return True         # Nothing means match all
        # Note: fnmatch is only case insensitive if the filesystem is
        for chk in self.iname_globs: # First try case insensitive
            if fnmatch.fnmatchcase(fname.lower(), chk):
                return True
        for chk in self.options.nameGlobs: # always case sensitive
            if fnmatch.fnmatchcase(fname, chk):
                return True
        return False

    def EachDir(self, parg):
        """Handle directory walk."""
        if parg[-1] == os.sep: # trim final slash
            parg = parg[:-1]
        base_count = parg.count(os.sep)
        for root, dirs, files in os.walk(parg, followlinks=self.options.follow):
            depth = root.count(os.sep) - base_count
            if (self.options.maxdepth >= 0
                and depth >= self.options.maxdepth):
                self.Debug(2, "Hit maxdepth.  Trimming %s" % dirs)
                del dirs[:] # trim all sub directories
            else:        
                for d in dirs:
                    if d.startswith('.'): # ignore hidden directories
                        self.Debug(2, "Trimming hidden: %s" % (d))
                        dirs.remove(d)
            for fn in files:
                if not self.CheckMatch(fn):
                    continue
                self.EachFile(os.path.join(root, fn))

    def _MakeTagDict(self, meta, revmap, tags):
        """Convert remap and meta into tags[key] -> value."""
        for k in revmap.keys(): # clone tags as variables
            tags[k] = self.HumanStr(meta, revmap[k])

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
        revmap = dict()
        self.MakeKeyMap(meta, revmap)

        local_tags = dict()
        if self.eval_code:
            self.global_vars[self.FILECOUNT] = self.file_count
            self.global_vars[self.MATCHCOUNT] = self.match_count
            local_vars = dict()
            # TODO: eval should really be dealing with meta directly
            self._MakeTagDict(meta, revmap, local_tags)
            local_vars[self.TAGS] = local_tags
            local_vars[self.FILEPATH] = fn
            local_vars[self.FILENAME] = os.path.basename(fn)
            local_vars[self.SKIP] = 0

            for cc in self.eval_code:
                self._Eval(cc, local_vars)
                if local_vars[self.SKIP]:
                    return
            for k, v in local_tags.iteritems(): # look for changes
                if not revmap.has_key(k):
                    # TODO: create the tag (if possible)
                    self.Debug(0, "New tag '%s' is ignored")
                    continue
                if self.HumanStr(meta, revmap[k]) != v:
                    # TODO: write changes to meta
                    self.Debug(
                        0, "Oh look, %s changed: %s -> %s (no writes, yet)" % (
                            k, unified[k], v))
                    pass
        if self.greps and not self.Grep(fn, meta, revmap):
            return

        self.match_count += 1
        if not local_tags: # the following outputs need a tag-value map
            self._MakeTagDict(meta, revmap, local_tags)
        local_tags['_'+self.FILEPATH] = fn
        local_tags['_'+self.FILENAME] = os.path.basename(fn)
        local_tags['_'+self.FILECOUNT] = self.file_count
        local_tags['_'+self.MATCHCOUNT] = self.match_count
        local_tags['_'+self.VERSION] = VERSION

        if self.options.printpath:
            print fn

        if self.options.ls:
            print "==== %s ====" % (fn)
            self.PrintKeyValue(local_tags)

        for et in self.echo_tmpl:
            out = et.safe_substitute(local_tags)
            print out

        if self.exec_tmpl:
            self.AllExec(meta, local_tags)

        if self.options.linkdir:
            self.SymLink(fn)            

    def DoEnd(self):
        """Do final code block after last file.
        Returns: True if there were matches, else False
        """
        if self.file_count > 0 and self.end_code:
            self.global_vars[self.FILECOUNT] = self.file_count
            self.global_vars[self.MATCHCOUNT] = self.match_count
            for cc in self.end_code:
                self._Eval(cc, dict())
        return self.match_count > 0
        
def main():
    tb = TagBoy()
    args = tb.HandleArgs(sys.argv[1:])
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
