# coding:utf-8
import argparse
import json
from itertools import islice
from pathlib import Path

import numpy as np
import requests
import sys

NOT_AVAIL = "NA"

parser = argparse.ArgumentParser(description="Import reviews into solr database")
parser.add_argument('file', type=Path)
parser.add_argument('--locations', type=Path, required=True)
# parser.add_argument('--country-codes', type=Path, required=True)
parser.add_argument('--country-code', type=str, required=True)
parser.add_argument('--source', type=str, required=True)
args = parser.parse_args()

SOLR_URL = "http://localhost:8983/solr/humboldt"
SOLR_UPDATE_URL = SOLR_URL + "/update"

EARTH_RADIUS = 6371


def get_shortest_in(needle, haystack):
    '''
    :param needle: single (lat,long) tuple.
    :param haystack: numpy array to find the point in that has the shortest distance to needle
    :return:
    '''
    dlat = np.radians(haystack[:, 0]) - np.radians(needle[0])
    dlon = np.radians(haystack[:, 1]) - np.radians(needle[1])
    a = np.square(np.sin(dlat / 2.0)) + np.cos(np.radians(needle[0])) * np.cos(np.radians(haystack[:, 0])) * np.square(
        np.sin(dlon / 2.0))
    great_circle_distance = 2 * np.arcsin(np.minimum(np.sqrt(a), np.repeat(1, len(a))))
    d = EARTH_RADIUS * great_circle_distance
    return d.tolist()


def location_data(file):
    coords_by_country_and_city = {}

    # location_by= defaultdict(lambda: defaultdict(list))

    for line in file.open():
        country, place, hits, info_str = line.strip("\n").split('\t')
        if not info_str:
            continue

        info = json.loads(info_str)

        lat = ''
        lng = ''
        population = 0

        # Merge coords that are close enough together to be one city
        if len(info) > 1:
            candidates = np.array([[c[0] for c in info], [c[1] for c in info]]).T
            distances = np.array([get_shortest_in(x, candidates) for x in candidates])
            np.fill_diagonal(distances, float('inf'))

            same_place = np.where(distances <= 11)
            same_place = set([tuple(sorted(list(x)))[-1] for x in zip(same_place[0], same_place[1])])
            if same_place:
                new_info = [hub for i, hub in enumerate(info) if i not in same_place]
                info = new_info

        # Select the biggest city
        for candidate_lat, candidate_lng, candidate_pop in info:
            if candidate_pop >= population:
                population = candidate_pop
                lat = float('%.2f' % candidate_lat)
                lng = float('%.2f' % candidate_lng)

        # If there are more than one candidate and neither has population info, skip
        if len(info) > 1 and population == 0:
            continue

        # Otherwise, if coords are available, use them
        if lat and lng:
            coords_by_country_and_city[(country, place)] = "{},{}".format(lat, lng)

    return coords_by_country_and_city

def map_solr_fields(review):
    """Create a new review document where all fields are mapped to compatible Solr auto types"""
    MAPPING = {
        'id': 'id',
        'body_text': 'body_text_ws',
        'title_text': 'title_text_ws',
        'gender': 'gender_s',
        'age': 'age_i',
        'review_year': 'review_year_i',
        'reviewer_id': 'reviewer_id_s',
        'location': 'location_rpt',
        'country': 'country_s',
        'nuts_1': 'nuts_1_s',
        'nuts_2': 'nuts_2_s',
        'nuts_3': 'nuts_3_s',
        'company_id': 'company_id_s',
        'langid': 'langid_s',
        'age_s': 'age_s',
        'review_year_s': 'review_year_s',
        'nuts_3_and_age': 'nuts_3_and_age_s',
        'nuts_3_and_gender': 'nuts_3_and_gender_s',
        'nuts_3_and_gender': 'nuts_3_and_gender_s',
        'nuts_3_and_gender_and_age': 'nuts_3_and_gender_and_age_s',
        'gender_and_age': 'gender_and_age_s',
        'source': 'source_s'
    }

    return {MAPPING[key]: val
            for key, val in review.items()
            if key in MAPPING}

def make_country_codes():
    codes = {}
    reverse_cc = {}
    ccfile = args.country_codes.open()
    next(ccfile)
    for line in ccfile:
        cc, country = line.replace('"', '').strip('\r\n').strip().split(',')
        codes[country] = cc
        reverse_cc[cc] = country

    return codes, reverse_cc

# country_codes, _ = make_country_codes()


def read_json_line(line):
    user = json.loads(line)

    for review_index, org_review in enumerate(user['reviews']):
        # if 'text' not in org_review:
        #     continue

        body_text = " ".join([" ".join(sent) for sent in org_review.get('tokenized_text', [])])
        title_text = " ".join([" ".join(sent) for sent in org_review.get('title_tokenized', [])])

        new_review = {'body_text': body_text.lower(),
                      'title_text': title_text.lower(),
                      'company_id': org_review['company_id'],
                      'reviewer_id': user['user_id'],
                      'id': user['user_id'] + '_' + str(review_index),
                      'gender': user.get('gender', NOT_AVAIL),
                      'langid': org_review['langid'],
                      'source': args.source
                      }

        # take care of None values
        if new_review['gender'] is None:
                new_review['gender'] = NOT_AVAIL

        if user.get('birth_year') and org_review.get('date'):
            new_review['age'] = int(org_review['date'][:4]) - int(user['birth_year'])
            new_review['review_year'] = int(org_review['date'][:4])

        new_review['age_s'] = str(new_review.get('age', NOT_AVAIL))
        new_review['review_year_s'] = str(new_review.get('review_year', NOT_AVAIL))

        locations = user['location'].split(",")
        country_code = args.country_code#country_codes.get(new_review['country'])
        new_review['country'] = country_code
        #locations[-1].strip()  # last entry is always the country, but strip whitespaces before/after name
        if len(locations) >= 1:
            city = locations[0]
            new_review['city'] = city.replace(" Municipality", "")

            lookup_key = (country_code, city)

            coords = locdata.get(lookup_key)
            if coords:
                new_review['location'] = coords
                new_review['location_rpt'] = coords
        else:
            new_review['city'] = NOT_AVAIL

        new_review['nuts_1'] = user.get('NUTS-1', NOT_AVAIL)
        new_review['nuts_2'] = user.get('NUTS-2', NOT_AVAIL)
        new_review['nuts_3'] = user.get('NUTS-3', NOT_AVAIL)

        # Combination fields
        new_review['nuts_3_and_age'] = ":".join([new_review['nuts_3'], new_review['age_s']])
        new_review['nuts_3_and_gender'] = ":".join([new_review['nuts_3'], new_review['gender']])
        new_review['nuts_3_and_gender_and_age'] = ":".join([new_review['nuts_3'],
                                                            new_review['gender'],
                                                            new_review['age_s']])
        new_review['gender_and_age'] = ":".join([new_review['gender'], new_review['age_s']])

        yield new_review

locdata = location_data(args.locations)

BATCH_SIZE = 25
batch = []
for line_no, line in enumerate(islice(args.file.open(), None)):
    if line_no > 0:
        if line_no%1000 == 0:
            print(line_no, file=sys.stderr, flush=True)
        elif line_no%100 == 0:
            print('.', end='', file=sys.stderr, flush=True)

    for review in read_json_line(line):
        batch.append(map_solr_fields(review))

    if len(batch) >= BATCH_SIZE:
        r = requests.post(SOLR_UPDATE_URL, json=batch)
        r.raise_for_status()
        batch = []

if len(batch):
    # Submit final batch
    r = requests.post(SOLR_UPDATE_URL, json=batch)
    r.raise_for_status()

r = requests.get(SOLR_UPDATE_URL + "?commit=true")
r.raise_for_status()
