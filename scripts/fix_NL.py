import json
from itertools import islice
import langid
import sys

langid.set_languages(['nl', 'en'])
for line_no, line in enumerate(islice(open(sys.argv[1]), None)):
    if line_no > 0:
        if line_no%1000 == 0:
            print("%s" % (line_no), file=sys.stderr)
        elif line_no%100 == 0:
            print('.', end=' ', file=sys.stderr)

    try:
        user = json.loads(line)
    except ValueError:
        continue

    uid = user.get('user_id', None)

    reviews = user.get('reviews', [])

    if reviews:
        counter = 0
        for rn, review in enumerate(reviews, 1):
            text = " ".join(["".join(sent) for sent in review.get('text', [])])
            review["langid"] = langid.classify(text)[0]
            print(text)


    print(json.dumps(user, ensure_ascii=False))