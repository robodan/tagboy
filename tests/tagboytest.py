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
    file1 = 'DSCF2132.jpg'
    file2 = 'DSCN0443.JPG'
    file3 = 'IMAG0154.jpg'
    file4 = 'IMAG0160.jpg'
    file5 = 'IMAG0166.jpg'

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

    def testSimplePrint(self):
        """Simple test of file read and name print."""
        sys.stdout = StringIO.StringIO() # redirect stdout
        fpath = os.path.join(self.testdata, self.file1)
        args = self.tb.HandleArgs([fpath, '--print'])
        self.tb.EachFile(fpath)
        self.assert_(fpath in sys.stdout.getvalue(),
                     "Expected '%s' in output: %s"
                     % (fpath, sys.stdout.getvalue()))
        self.assertEqual(self.tb.file_count, 1,
                         "file_count %d != 1" % self.tb.file_count)
        sys.stdout.close()      # free memory

    def tearDown(self):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        self.tb = None

if __name__ == "__main__":
    unittest.main()  
