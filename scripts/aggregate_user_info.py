"""
read in user info files and combine
"""
import json
import sys
import glob
from collections import defaultdict, Counter

userinfo = defaultdict(Counter)

for filename in glob.glob("%s/*.json" % sys.argv[1]):
    for line in open(filename):
        for key, value in json.loads(line.strip()).items():
            userinfo[key].update(value)

print(json.dumps(userinfo, ensure_ascii=False, indent=1))

