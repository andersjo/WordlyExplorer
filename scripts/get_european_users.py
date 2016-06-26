"""
read in the aggregated file, find all users in EU, and add their NUTS3
"""

import json
import sys
from collections import Counter
import argparse

import fiona
from itertools import islice
from shapely.geometry import shape, Point

__author__ = 'dirkhovy'


parser = argparse.ArgumentParser(description="add NUTS regions to places")
parser.add_argument('--json', help='JSON input file', required=True)
parser.add_argument('--nuts', help='NUTS shape (.shp) input file')

args = parser.parse_args()

MIN_TWEETS = 3
MIN_LAT = 36.
MAX_LAT = 70.
MIN_LNG = -11.
MAX_LNG = 40.


print("Reading NUTS data", file=sys.stderr)
fiona_shapes = fiona.open(args.nuts)
nuts2loc = {}

nuts2_shapes = {}
for item in islice(fiona_shapes, None):
    level = int(item['properties']['STAT_LEVL_'])
    if level == 3:
        nuts_id = item['properties']['NUTS_ID']
        nuts2_shapes[nuts_id] = shape(item['geometry'])


def get_NUTS3(lng, lat):
    try:
        nutsy = nuts2loc[(lng, lat)]
        return nutsy
    except KeyError:
        point = Point(lng, lat)

        for nuts_id, nuts_shape in nuts2_shapes.items():
            if nuts_shape.contains(point):
                nuts2loc[(lng, lat)] = nuts_id
                return nuts_id
        return None

users = json.load(open(args.json))

for user, coordinates in users.items():
    if sum(coordinates.values()) < MIN_TWEETS:
        continue

    top = Counter(coordinates).most_common(1)[0][0]
    # TODO: handle ties?

    lng, lat = list(map(float, top.split(',')))

    if MIN_LNG <= lng <= MAX_LNG and MIN_LAT <= lat <= MAX_LAT:
        nuts3 = get_NUTS3(lng, lat)

        print(user, lng, lat, nuts3)
