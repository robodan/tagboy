from __future__ import absolute_import

if __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.abspath(__file__)))

from tbcmd import ArgParser, main
from tbcore import TagBoy
from tbutil import distance
