"""
read in a twitter file and extract the data to various JSON files with TP format
"""
import argparse
import codecs
import glob
import json
import os
import sys
import langid
from itertools import islice
import numpy as np
import pandas as pd
import re

parser = argparse.ArgumentParser(description='parse out the relevant infor from Twitter and output a JSON')
parser.add_argument('directory', help='directory with input files', type=str)
parser.add_argument('--output', help='output directory', type=str, required=True)
parser.add_argument('--names', help='file with names', type=str, required=True)
parser.add_argument('--user_info', help='file with user info', type=str, required=True)

args = parser.parse_args()


MIN_SUPPORT = 3
PREVALENCE = 0.85
NUMBERS = re.compile(r"[0123456789]")
NAMES = re.compile(r"@[^ ]*")
URLS = re.compile(r"http[^ ]*")


def get_JSON_dict(user_id, location=None, gender=None, profile_text=None, name=None, nuts3=None):
    """
    get basic TP user-frame
    :param user_id:
    :param location:
    :param gender:
    :param profile_text:
    :param name:
    :param nuts3:
    :return:
    """
    d = {"location": location,
         "reviews": [],
         "gender": gender,
         "item_type": "user",
         "profile_text": [profile_text],
         "name": name,
         "birth_year": None,
         "user_id": user_id,
         "NUTS-1": nuts3[:3],
         "NUTS-2": nuts3[:4],
         "NUTS-3": nuts3
         }
    return d


def get_review(date=None, user_id=None, lang_id=None, text=None):
    """
    basic frame for a TP review
    :param date:
    :param user_id:
    :param lang_id:
    :param text:
    :return:
    """
    review = {"date": date, "text": [text], "title": None, "rating": None, "item_type": 'tweet', "company_id": None,
              "user_id": user_id, "langid": lang_id}
    return review


def get_gender(info):
    """
    get most likely gender, if available
    :param info:
    :return: F, M, or None
    """
    [country, male, female, support] = info
    male = float(male)
    female = float(female)
    if support < MIN_SUPPORT:
        return None
    if female < PREVALENCE <= male:
        return "M"
    elif male < PREVALENCE <= female:
        return "F"
    else:
        return None

names = pd.read_csv(args.names,
                          names=['country', 'ID', 'male', 'female', 'support'], sep='\t', index_col=1,
                          dtype={'ID': str})

author_info = pd.read_csv(args.user_info,
                          names=['ID', 'lng', 'lat', 'nuts3'], sep=' ', dtype=str)
author_info = author_info.set_index('ID')

authors = {}

open_files = {}

for doc in glob.iglob("%s/*.json" % args.directory):
    file_name = os.path.basename(doc)

    print(file_name, file=sys.stderr)

    with codecs.open(doc, "r",encoding='utf-8', errors='ignore') as fdata:

        for line_no, line in enumerate(islice(fdata, None)):
            try:
                tweet = json.loads(line)
            except ValueError:
                continue

            try:
                # user info
                user_id = tweet['user']['id_str']
                if user_id not in author_info.index:
                    continue

                name = tweet['user']['name']
                first_name = name.lower().split(' ')[0]
                location = tweet['user'].get('location', None)
                nuts3 = author_info.ix[user_id]['nuts3']
                try:
                    gender = get_gender(names[names.country == nuts3[:2]].ix[first_name].tolist())
                except AttributeError as ae:
                    print(names[names.country == nuts3[:2]].ix[first_name], file=sys.stderr)

                profile_text = tweet['user'].get('description', None)

                # tweet info
                date = tweet['created_at']
                text = tweet['text']
                # TODO: sort out pure URL tweets and retweets here already?
                lang_id = langid.classify(re.sub(NAMES, '@', re.sub(NUMBERS, '0', re.sub(URLS, 'URL', text.lower()))))[0]

                # if user_id not in authors:
                author = get_JSON_dict(user_id, location=location, gender=gender, profile_text=profile_text, name=name, nuts3=nuts3)

                new_review = get_review(date=date, user_id=user_id, lang_id=lang_id, text=text)
                author['reviews'].append(new_review)

                file_name = '%s.%s' % (nuts3[:2], lang_id)

                if file_name not in open_files:
                    open_files[file_name] = open('%s/%s.json' % (args.output, file_name), 'w')

                open_files[file_name].write("%s\n" % json.dumps(author, ensure_ascii=False))

            except KeyError as ke:
                pass
                # print(ke)

for file_name, file_handle in open_files.items():
    file_handle.close()

# for author, entry in authors.items():
#     print(json.dumps(entry, ensure_ascii=False))
