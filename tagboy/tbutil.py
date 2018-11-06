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

# Utility routines

from math import cos, asin, sqrt


def distance(latlon1, latlon2):
    """Distance in km between two lat/lon positions using haversine."""
    # Note: will blow up if positions are half way around the world
    # assumes a spherical world
    # https://stackoverflow.com/questions/27928/calculate-distance-between-two-latitude-longitude-points-haversine-formula
    lat1, lon1 = latlon1
    lat2, lon2 = latlon2
    p = 0.017453292519943295     #Pi/180
    a = 0.5 - cos((lat2 - lat1) * p)/2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2
    return 12742 * asin(sqrt(a)) #2*R*asin...
