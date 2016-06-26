import json
import os

import nltk
import pandas as pd
import glob
import argparse

import sys

parser = argparse.ArgumentParser(description='parse out the relevant infor from CSI and output a JSON, a txt, and a meta file')
parser.add_argument('directory', help='directory with input files', type=str)
parser.add_argument('--type', help='input type', type=str)
args = parser.parse_args()

sentence_tokenizer = nltk.data.load('tokenizers/punkt/dutch.pickle')

def get_JSON_dict(user_id, location=None, gender=None, birth_year=None):
    d = {"location": location,
         "reviews": [],
         "gender": gender,
         "item_type": "user",
         "profile_text": [],
         "name": None,
         "birth_year": birth_year,
         "user_id": user_id
         }
    return d

def get_review(date=None, title=None, rating=None, item_type=None, company_id=None, user_id=None):
    review = {"date": date, "text": [], "title": title, "rating": rating, "item_type": item_type, "company_id": company_id,
                      "user_id": user_id, "langid": "nl"}
    return review

doc_info = pd.read_csv("data/csicorpus/List.CSI.DocumentData.1.4.0.BV.2016-02-08.txt",
                       names=['FileName', 'AuthorID', 'Timestamp', 'Genre', 'Grade', 'Sentiment', 'Veracity',
                              'Category', 'Product', 'Subject'], sep='\t', index_col=0, dtype={'AuthorID': '|S8'})
author_info = pd.read_csv("data/csicorpus/List.CSI.AuthorData.1.4.0.BV.2016-02-08.txt",
                          names=['AuthorID', 'DateOfBirth', 'Gender', 'SexualPreference', 'Region', 'Country',
                                 'BigFive', 'MBTI'], sep='\t', index_col=0, dtype={'AuthorID': '|S8'}, mangle_dupe_cols=False)

authors = {}

for doc in glob.iglob("%s/*.txt" % args.directory):
    file_name = os.path.basename(doc)

    if file_name not in doc_info.index:
        print("%s is not in DB!" % file_name, file=sys.stderr, flush=True)
        file_name = file_name.replace('-06-01.', '-01-06.')
        # print(file_name in doc_info.index, file=sys.stderr, flush=True)
        # continue

    # tokenize
    text = ' '.join(map(str.strip, open(doc).readlines()))
    sentences = sentence_tokenizer.tokenize(text)

    # author info
    uid = doc_info.ix[file_name].AuthorID
    str_uid = uid.decode('utf-8')

    if type(author_info.ix[uid]) == pd.core.frame.DataFrame:
        the_author = author_info.ix[uid].ix[0]
    else:
        the_author = author_info.ix[uid]

    location = "%s, %s" % (the_author.Region, the_author.Country)
    try:
        gender = the_author.Gender[0]
    except IndexError:
        gender = None

    birth_year = the_author.DateOfBirth[:4]

    if uid not in authors:
        authors[uid] = get_JSON_dict(str_uid, location=location, gender=gender, birth_year=birth_year)

    # doc info
    date = doc_info.ix[file_name].Timestamp[:4]

    new_review = get_review(date=date, title=None, rating=None, item_type=args.type, company_id=None, user_id=str_uid)
    new_review['text'].extend(sentences)
    authors[uid]['reviews'].append(new_review)

for author, entry in authors.items():
    print(json.dumps(entry, ensure_ascii=False))
