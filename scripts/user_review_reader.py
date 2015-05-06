import argparse
import codecs
from collections import namedtuple, Counter
from itertools import islice
from collections import defaultdict
import sys

# "1       Alpha   _       NOUN    NOUN    _       2       compmod"
DepToken = namedtuple('DepToken', 'id form lemma cpos pos feat head rel')


def read_tokens(conll_file):
    rows = []
    while True:
        conll_line = conll_file.readline()
        row = conll_line.strip().split("\t")
        if len(row) < 7:
            break

        # Use zero indexing instead of one
        row[0] = int(row[0]) - 1
        row[6] = int(row[6]) - 1
        rows.append(DepToken(*row))

    return rows

def extract_tokens(reviews, attr='lemma'):
    return [getattr(token, attr)
            for review in reviews
            for sent in review
            for token in sent]


def read_user_reviews(filename, n=None, require_age=False, require_gender=False):
    meta_file = codecs.open(filename + ".meta", encoding='utf-8')
    conll_file = codecs.open(filename + ".conll", encoding='utf-8')

    prev_user_id = None
    prev_review_index = None
    user = {'reviews': [[]]}
    for meta_line in islice(meta_file, n):
        user_id, review_index, gender, age = meta_line.strip("\n").split("\t")
        review_index = int(review_index)

        if prev_user_id and prev_user_id != user_id:
            if (require_age and not user.get('age')) or (require_gender and not user.get('gender')):
                pass
            else:
                yield user

            user = {'reviews': [[]]}
        elif prev_review_index != review_index:
            user['reviews'].append([])

        review = user['reviews'][-1]

        user['user_id'] = user_id
        user['gender'] = gender
        if gender == 'None':
            user['gender'] = None

        if age:
            user['age'] = int(age)

        tokens = read_tokens(conll_file)
        review.append(tokens)

        prev_user_id = user_id
        prev_review_index = review_index


