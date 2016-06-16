"""
collect tweet Point coordinates (lng, lat) and aggregate per user in defaultdict, output as JSON
"""
import json
from collections import defaultdict
import argparse
from itertools import islice

import sys

parser = argparse.ArgumentParser()
parser.add_argument('input', help="input file")

args = parser.parse_args()

locations = defaultdict(lambda: defaultdict(int))
for line_no, line in enumerate(islice(open(args.input), None)):
    if line_no > 0:
        if line_no%1000 == 0:
            print("%s" % (line_no), file=sys.stderr)
        elif line_no%100 == 0:
            print('.', end=' ', file=sys.stderr)

    try:
        tweet = json.loads(line)
    except ValueError:
        continue

    try:
        user = tweet['user']['id_str']
        lng, lat = tweet['coordinates']['coordinates']
        locations[user]['%.1f,%.1f' % (lng, lat)] += 1
    except KeyError:
        continue

# freeze it
for uid, locs in locations.items():
    print('{"%s": %s}' % (uid, json.dumps(locs, ensure_ascii=False)))
