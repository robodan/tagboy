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

import os
import StringIO
import sys
import unittest
try:
    import tagboy
except ImportError:
    print "Unable to load tagboy.  You may need: PYTHONPATH=.. tagboytest.py"
    sys.exit(1)

class RegressTests(unittest.TestCase):
    files = ['DSCF2132.jpg', 'DSCN0443.JPG', 'IMAG0154.jpg', 'IMAG0160.jpg', 
             'IMAG0166.jpg']
    gps_files = 'DSCN0443.JPG', 'IMAG0160.jpg', 'IMAG0166.jpg'

    def setUp(self):
        if os.path.isdir('testdata'):
            self.testdata = 'testdata'
        elif os.path.isdir(os.path.join('tests', 'testdata')):
            self.testdata = os.path.join('tests', 'testdata')
        else:
            print "Unable to locate testdata/ or tests/testdata/"
            sys.exit(1)
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        self.tb = tagboy.TagBoy()

    def tearDown(self):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        self.tb = None

    # NOTE: Can't test '-h' because it calls sys.exit()

    def testPrint(self):
        """Simple test of file read and name print."""
        sys.stdout = StringIO.StringIO() # redirect stdout
        fpath = os.path.join(self.testdata, self.files[0])
        args = self.tb.HandleArgs([fpath, '--print'])
        self.tb.EachFile(fpath)
        output = sys.stdout.getvalue()
        sys.stdout.close()      # free memory
        sys.stdout = self.old_stdout

        self.assert_(fpath in output,
                     "Expected '%s' in output: %s" % (fpath, output))
        self.assertEqual(self.tb.file_count, 1,
                         "file_count %d != 1" % self.tb.file_count)

    def testWalk(self):
        """Simple test of directory walk and print."""
        sys.stdout = StringIO.StringIO() # redirect stdout
        args = self.tb.HandleArgs([self.testdata,
                                   '--iname', '*.jpg', '--print'])
        self.tb.EachDir(self.testdata)
        output = sys.stdout.getvalue()
        sys.stdout.close()      # free memory
        sys.stdout = self.old_stdout

        self.assert_(self.tb.file_count >= len(self.files),
                     "Expected file_count %d >= %d"
                     % (self.tb.file_count, len(self.files)))
        for fn in self.files:
            self.assert_(fn in output,
                         "Expected '%s' in output: %s" % (fn, output))

    def testGrep(self):
        """Simple test of grep and print."""
        sys.stdout = StringIO.StringIO() # redirect stdout
        args = self.tb.HandleArgs([self.testdata, '--iname', '*.jpg',
                                   '--grep', '.', '*GPS*', '--print'])
        self.tb.EachDir(self.testdata)
        output = sys.stdout.getvalue()
        sys.stdout.close()      # free memory
        sys.stdout = self.old_stdout

        self.assert_(self.tb.file_count >= len(self.files),
                     "Expected file_count %d >= %d"
                     % (self.tb.file_count, len(self.files)))
        for fn in self.gps_files:
            self.assert_(fn in output,
                         "Expected '%s' in output: %s" % (fn, output))

    def testGrepEcho(self):
        """Simple test of grep and echo."""
        sys.stdout = StringIO.StringIO() # redirect stdout
        args = self.tb.HandleArgs([self.testdata, '--iname', '*.jpg',
                                   '--grep', '.', '*GPS*',
                                   '--echo', '$_filepath'])
        self.tb.EachDir(self.testdata)
        output = sys.stdout.getvalue()
        sys.stdout.close()      # free memory
        sys.stdout = self.old_stdout

        self.assert_(self.tb.file_count >= len(self.files),
                     "Expected file_count %d >= %d"
                     % (self.tb.file_count, len(self.files)))
        for fn in self.gps_files:
            self.assert_(fn in output,
                         "Expected '%s' in output: %s" % (fn, output))

    def testGrepFilename(self):
        """Simple test of grep -v -H."""
        sys.stdout = StringIO.StringIO() # redirect stdout
        args = self.tb.HandleArgs([self.testdata, '--iname', '*.jpg',
                                   '--grep', '.', '*GPS*', '-v', '-H'])
        self.tb.EachDir(self.testdata)
        output = sys.stdout.getvalue()
        sys.stdout.close()      # free memory
        sys.stdout = self.old_stdout

        self.assert_(self.tb.file_count >= len(self.files),
                     "Expected file_count %d >= %d"
                     % (self.tb.file_count, len(self.files)))
        for fn in self.gps_files:
            self.assert_(fn in output,
                         "Expected '%s' in output: %s" % (fn, output))

    def testLsShort(self):
        """Test of short tag print."""
        sys.stdout = StringIO.StringIO() # redirect stdout
        fpath = os.path.join(self.testdata, self.files[0])
        args = self.tb.HandleArgs([fpath, '--ls'])
        self.tb.EachFile(fpath)
        output = sys.stdout.getvalue()
        sys.stdout.close()      # free memory
        sys.stdout = self.old_stdout

        self.assert_(fpath in output, # check for header
                     "Expected '%s' in output: %s" % (fpath, output))
        count = len(output.splitlines())
        self.assert_(count > 100,
                         "expected line count %d > 100" % count)

    def testLsLong(self):
        """Test of long tag print."""
        sys.stdout = StringIO.StringIO() # redirect stdout
        fpath = os.path.join(self.testdata, self.files[0])
        args = self.tb.HandleArgs([fpath, '--ls', '--long'])
        self.tb.EachFile(fpath)
        output = sys.stdout.getvalue()
        sys.stdout.close()      # free memory
        sys.stdout = self.old_stdout

        self.assert_(fpath in output, # check for header
                     "Expected '%s' in output: %s" % (fpath, output))
        count = len(output.splitlines())
        self.assert_(count > 150,
                         "expected line count %d > 150" % count)

    def testLsVerbose(self):
        """Test of verbose tag print."""
        sys.stdout = StringIO.StringIO() # redirect stdout
        fpath = os.path.join(self.testdata, self.files[0])
        args = self.tb.HandleArgs([fpath, '--ls', '-v'])
        self.tb.EachFile(fpath)
        output = sys.stdout.getvalue()
        sys.stdout.close()      # free memory
        sys.stdout = self.old_stdout

        self.assert_(fpath in output, # check for header
                     "Expected '%s' in output: %s" % (fpath, output))
        count = len(output.splitlines())
        self.assert_(count > 270,
                         "expected line count %d > 270" % count)

    def testBeginEvalEnd(self):
        """Simple test of --begin/eval/end."""
        sys.stdout = StringIO.StringIO() # redirect stdout
        fpath = os.path.join(self.testdata, self.files[0])
        args = self.tb.HandleArgs([fpath,
                                   '--begin', 'print "HELLO"',
                                   '--eval', 'print filepath',
                                   '--end', 'print "BYE"'])
        self.tb.EachFile(fpath)
        self.tb.DoEnd()
        output = sys.stdout.getvalue()
        sys.stdout.close()      # free memory
        sys.stdout = self.old_stdout
        self.assertEqual(self.tb.file_count, 1,
                         "file_count %d != 1" % self.tb.file_count)
        self.assert_("HELLO" in output,
                     "Expected HELLO in output: %s" % output)
        self.assert_(fpath in output,
                     "Expected '%s' in output: %s" % (fpath, output))
        self.assert_("BYE" in output,
                     "Expected BYE in output: %s" % output)


if __name__ == "__main__":
    unittest.main()  
