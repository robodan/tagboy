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

# Main tag management class

from __future__ import absolute_import
from __future__ import division
#from __future__ import print_function

import fnmatch
import optparse              # deprecated.  TODO:  convert to argparse
import os
try:
    import pyexiv2 as ex
except ImportError:
    print "Unable to import pyexiv2.  You may need: sudo apt install python-pyexiv2"
    sys.exit(1)

import re
import subprocess
import string
import sys

from tbutil import *


class TagTemplate(string.Template):
    """Sub-class string.Template to allow . in variable names."""
    idpattern = r'[_a-z][\._a-z0-9]*'


class TagBoy(object):
    """Class that implements tag mapulation."""
    # string constants defining the names of fields/variables
    ARG        = 'arg'        # name of command line argument (string)
    FILECOUNT  = 'filecount'  # name of current count of files read (int)
    FILENAME   = 'filename'   # name of file base name (string)
    FILEPATH   = 'filepath'   # name of full path (string)
    MATCHCOUNT = 'matchcount' # name of current count of files read (int)
    OBJS       = 'objs'       # name of dict of tag objects: name -> object
    OBJMAP     = 'objmap'     # name of dict of tag names: short -> long
    SELECTED   = 'selected'   # name of dict of --select tags short -> long
    SKIP       = 'skip'       # name of set True to end processing of this file
    TAGS       = 'tags'       # name of dict of all tags: name -> value
    VERSION    = 'version'    # name of version of tagboy (string)

                                        # parse degree, minutes, seconds.  e.g. 37deg 16' 25.870
    DMS_RE = re.compile("\s*(\d+)deg (\d+)' ([0-9.]+)\s*")

    def __init__(self, version="dev"):
        self.file_count = 0       # number of files encountered
        self.match_count = 0      # number of files 'matched'
        self.global_vars = dict() # 'global' state passed to eval()
        self.global_vars[self.VERSION] = version
        self.begin_code = list()  # list of compiled code for before any file
        self.eval_code = list()   # list of compiled code for each file
        self.end_code = list()    # list of compiled code for after all files
        self.echo_tmpl = list()   # list of echo statement templates
        self.exec_tmpl = list()   # list of exec statement templates
        self.iname_globs = list() # list of case converted name globs
        self.greps = list()       # list of search (RE, glob)
        self.selects = list()     # list of select globs
        self.near = list()        # list of places of interest

    def HandleArgs(self, options, pos_args):
        """Process argument parsing and return parsed arguments."""

        self.options = options

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

        for nn in self.options.near: # convert echo list into templates
            try:
                self.near.append(self._ParseLatLon(nn))
            except ValueError:
                self.Error("Unable to parse %r as (lat, lon).  IGNORED" % nn)

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

        self.options.near_dist = float(self.options.near_dist)

        compile_flags = re.IGNORECASE if self.options.igrep else 0
        for pat, targ in self.options.grep:
            rec = re.compile(pat, compile_flags)
            for tt in targ.split(';'):
                   self.greps.append((rec, tt))

        for targ in self.options.selects:
            for tt in targ.split(';'):
                self.selects.append(tt)

        self.global_vars[self.ARG] = self.options.argument

        if self.options.version:
            print "Version: %s" % VERSION
            sys.exit(0)

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
            self.Debug(1, "Error getting value for: %s" % key)
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

    def PrintKeyValue(self, d, select=[]):
        """Pretty print key-values.  If select is set, only show those keys"""
        max_tag = 0
        for k in sorted(d.keys()): # find longest tag name
            if select and not (k in select):
                continue
            if len(k) > max_tag:
                max_tag = len(k)

        for k in sorted(d.keys()):
            if not self.options.verbose and k[0] == '_': # internal variable
                continue
            if (not self.options.long and
                not self.options.verbose and k.find('.') >= 0):
                continue            # skip the dotted names
            if select and not (k in select):
                continue
            value = str(d[k])
            if self.options.maxstr > 0 and len(value) > self.options.maxstr:
                value = value[ : self.options.maxstr] + '...'
            print "%-*s %s" % (max_tag+1, k + ':', value)

    def List(self, fn, local_tags, meta, revmap, select_tags=[]):
        """Print tag info for a file."""
        print "==== %s ====" % (fn)
        if (select_tags is not None) and (not select_tags):
            return              # no selected tags in this file
        if self.options.human:
            hdict = dict()
            for kk , vv in local_tags.iteritems():
                if self.selects and not (kk in select_tags):
                    continue
                hname = None
                if kk[0] != '_': # not internal
                    if revmap[kk] in meta.exif_keys:
                        hname = meta[revmap[kk]].label
                    else:
                        hname = meta[revmap[kk]].title
                if not hname:
                    if not self.options.unknown:
                        continue # just skip it
                    hname = kk
                self.Debug(3, "tag to human: %s -> %s" % (kk, hname))
                hdict[hname] = vv
            self.PrintKeyValue(hdict)
        else:
            self.PrintKeyValue(local_tags, select_tags)

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

    def Grep(self, fname, metadata, revmap):
        """Check if all patterns match for this file."""
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
                        if self._SubGrep(mpat, fname, kk, str(vv)):
                            matched = True
                            if not self.options.verbose:
                                break
                else:
                    if self._SubGrep(mpat, fname, kk, self.HumanStr(metadata, mk)):
                        matched = True
                        if not self.options.verbose:
                            break
            if not matched:     # all grep options must match
                all_match = False
                # we could break the loop here, but the verbose/debug prints are often desired
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

    def _ParseLatLon(self, arg_str):
        """Parse command line lat, lon entry and return (lat, lon).

        Only supports signed decimal representation for now.
        Outer parentheses and whitespace is ignored
        """
        ss = arg_str
        if ss[0] == '(':
            ss = ss[1:]
        if ss[-1] == ')':
            ss = ss[:-1]
        lat, lon = ss.strip().split(',')
        lat = lat.strip()
        lon = lon.strip()
        return (float(lat), float(lon))

    def _ConvertDMS(self, dms):
        """Convert degree, minute, second string to decimal degrees."""
        # TODO: class method
        mo = self.DMS_RE.match(dms)
        if not mo:
            raise ValueError, "Error parsing %r as degree, minutes, seconds" % dms
        deg, min, sec = mo.groups()
        return float(deg) + float(min)/60.0 + float(sec)/3600.0

    def _GetDecimalLatLon(self, local_tags):
        """Convert exif GPS fields to a decimal lan-lon tuple.

        Returns (lat, lon)
        Returns None if the fields were missing or invalid
        """

        try:
            lat = local_tags["Exif.GPSInfo.GPSLatitude"]
            lat_ref = local_tags["Exif.GPSInfo.GPSLatitudeRef"]
            lon = local_tags["Exif.GPSInfo.GPSLongitude"]
            lon_ref = local_tags["Exif.GPSInfo.GPSLongitudeRef"]
            self.Debug(2, "lat: %r, lon: %r" % (lat, lon))   # DEBUG

            lat = self._ConvertDMS(lat)
            if lat_ref == "South":
                lat = -lat
            lon = self._ConvertDMS(lon)
            if lon_ref == "West":
                lon = -lon

            ret = (lat, lon)
            self.Debug(2, "GetDecimalLatLon: %r" % (ret, ))   # DEBUG
            return ret
        except (KeyError, ValueError), msg:  # missing fields or invalid values
            self.Debug(2, "GetDecimalLatLon: %s" % msg)   # DEBUG
            return None
        return None

    def Near(self, fname, local_tags):
        """Check if this file has position and is near any given point."""

        file_pos = self._GetDecimalLatLon(local_tags)
        if not file_pos:
            return False

        nearest = None
        closest = None
        for pos in self.near:
            dist = distance(pos, file_pos)
            if dist <= self.options.near_dist:
                if closest is None or dist < closest:   # find closest match
                    closest = dist
                    nearest = pos
            else:
                self.Debug(1, "%s: (%.6f, %.6f) is %.1fkm from (%.6f, %.6f)" % (
                    fname, file_pos[0], file_pos[1], dist, pos[0], pos[1]))

        if nearest:
            self.Verbose("%s: (%.6f, %.6f) is %.1fkm from (%.6f, %.6f)" % (
                fname, file_pos[0], file_pos[1], closest, nearest[0], nearest[1]))
            local_tags['_near'] = "(%.6f, %.6f)" % (nearest[0], nearest[1])
            local_tags['_distance'] = "%.1f" % closest
            return True

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

        if self.greps and not self.Grep(fn, meta, revmap):
            return

        local_tags = dict()
        select_tags = None
        if self.selects:
            select_tags = dict()
            for ss in self.selects:
                keys = fnmatch.filter(revmap.keys(), ss)
                for kk in keys:
                    select_tags[kk] = revmap[kk]
            self.Debug(2, "Matched keys: %s" % keys)
        if self.eval_code:
            self.global_vars[self.FILECOUNT] = self.file_count
            self.global_vars[self.MATCHCOUNT] = self.match_count
            local_vars = dict()
            self._MakeTagDict(meta, revmap, local_tags)
            # FIX??? why no leading _ here???
            local_vars[self.FILENAME] = os.path.basename(fn)
            local_vars[self.FILEPATH] = fn
            local_vars[self.OBJS] = meta # DOC
            local_vars[self.OBJMAP] = revmap # DOC
            local_vars[self.SELECTED] = select_tags # DOC
            local_vars[self.TAGS] = local_tags
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

        self.match_count += 1
        if not local_tags: # the following outputs need a tag-value map
            self._MakeTagDict(meta, revmap, local_tags)
        local_tags['_'+self.ARG] = self.options.argument
        local_tags['_'+self.FILECOUNT] = self.file_count
        local_tags['_'+self.FILENAME] = os.path.basename(fn)
        local_tags['_'+self.FILEPATH] = fn
        local_tags['_'+self.MATCHCOUNT] = self.match_count
        local_tags['_'+self.VERSION] = self.global_vars[self.VERSION]

        if self.near:
            local_tags['_near'] = ""      # clear any old values
            local_tags['_distance'] = ""
            if not self.Near(fn, local_tags):
                return

        if self.options.printpath:
            print fn

        for et in self.echo_tmpl:
            out = et.safe_substitute(local_tags)
            self.Debug(1, "%r -> %r" % (et, out))   # DEBUG
            print out

        if self.options.ls:
            self.List(fn, local_tags, meta, revmap, select_tags)

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
