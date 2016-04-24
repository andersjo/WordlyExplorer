# coding:utf-8
import argparse
import json
from itertools import islice
from pathlib import Path

import numpy as np
import requests

parser = argparse.ArgumentParser(description="Import reviews into solr database")
parser.add_argument('file', type=Path)
parser.add_argument('--locations', type=Path, required=True)
parser.add_argument('--country-codes', type=Path, required=True)
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


country_codes, _ = make_country_codes()


def read_json_line(line):
    user = json.loads(line)

    reviews = []
    for review_index, org_review in enumerate(user['reviews']):
        if 'text' not in org_review:
            continue

        new_review = {'text': " ".join(org_review.get('text', [])),
                      'title': org_review.get('title'),
                      'user_id': user['user_id'],
                      'id': user['user_id'] + '_' + str(review_index),
                      'gender': user.get('gender', 'NA')
                      }

        if user.get('birth_year') and user.get('date'):
            new_review['age'] = int(org_review['date'][:4]) - int(user['birth_year'])

        locations = user['location'].split(",")
        new_review['country'] = locations[
            -1].strip()  # last entry is always the country, but strip whitespaces before/after name
        if len(locations) > 1:
            city = locations[0]
            new_review['city'] = city.replace(" Municipality", "")

            country_code = country_codes.get(new_review['country'])
            lookup_key = (country_code, city)

            coords = locdata.get(lookup_key)
            if coords:
                new_review['location'] = coords
                new_review['location_rpt'] = coords
                if 'NUTS-1' in user:
                    new_review['nuts-1'] = user['NUTS-1']
                    new_review['nuts-2'] = user['NUTS-2']
                    new_review['nuts-3'] = user['NUTS-3']

        reviews.append(new_review)
    return reviews


locdata = location_data(args.locations)

for line in islice(args.file.open(), 100):
    reviews = read_json_line(line)
    r = requests.post(SOLR_UPDATE_URL, json=reviews)
    print(r, r.text)

r = requests.get(SOLR_UPDATE_URL + "?commit=true")
