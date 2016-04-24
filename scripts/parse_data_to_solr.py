#coding:utf-8
import argparse
import sys
import solr
import json
import numpy as np
from collections import defaultdict
from itertools import chain, islice
import codecs
from user_review_reader import read_user_reviews

parser = argparse.ArgumentParser(description='Process trustpilot input data')
parser.add_argument('string', metavar='S', type=str, nargs='+',
                    help='a general name with either \'.conll\' or \'.jsonl\' or no ending for the files to be parsed')


def get_reviews(some_user):
    reviews = []
    for review in some_user['reviews']:
        sentence = " ".join([word.form for word in chain(*review)])
        if len(sentence):
            reviews.append(sentence)
    #print reviews
    return reviews


def read_reviews(filename, n=None):
    meta_file = codecs.open(filename + ".meta", encoding='utf-8')
    review_file = codecs.open(filename, encoding='utf-8')

    prev_user_id = None
    prev_review_index = None
    review = {'text': None, 'user_id': None, 'review_id': None}
    for meta_line in islice(meta_file, n):
        review_line = review_file.readline().strip("\n")
        user_id, review_index, gender, age = meta_line.strip("\n").split("\t")
        review_id = user_id + '00' + review_index
        review_id = int(review_id)
        user_id = int(user_id)

        if (prev_review_index and prev_review_index != review_index) or (prev_user_id and prev_user_id != user_id):
            yield review
            review = {'text': None, 'user_id': None, 'review_id': None}
        elif prev_review_index == review_index and prev_user_id == user_id:
            review['text'] = review['text'] + review_line

        review['user_id'] = user_id
        review['review_id'] = review_id

        if not review['text']:
            review['text'] = review_line

        if gender == 'None':
            review['gender'] = None
        else:
            review['gender'] = gender
        if age:
            review['age'] = int(age)

        prev_user_id = user_id
        prev_review_index = review_index

    if review['text']:
        yield review

def arguments():
    print('Must specify wether on a per \'user\' basis or per \'review\' basis')

def locationData(filename):
    data = defaultdict(lambda: defaultdict(list))
    locfile = codecs.open(filename, encoding='utf-8')
    for line in locfile:
        Country_code, city, _, location = line.strip("\n").split("\t")
        # print 'befor location: ', location
        if location:
            location = location.replace('[', '').replace(']', '').split(',')
            location = [float(loc) for loc in location]
            # print 'this location: ', location
            best_loc = 3*np.argmax(np.array([location[i] for i in range(2, len(location), 3)]))
            data[Country_code][city] = str(location[best_loc]) + ', ' +  str(location[best_loc+1])
            # print data
    return data


locdata = locationData('mapped_locations.tsv')

def make_country_codes():
    codes = {}
    reverse_cc = {}
    ccfile = codecs.open('iso_country_codes.csv', encoding='utf-8')
    next(ccfile)
    for line in ccfile:
        cc, country = line.replace('"', '').strip('\r\n').strip().split(',')
        codes[country] = cc
        reverse_cc[cc] = country

    return codes, reverse_cc

country_codes, _ = make_country_codes()
#print country_codes

def read_json_line(line):
    data = json.loads(line)

    reviews = []
    for re_id, review in enumerate(data['reviews']):
        rev = {'text': None, 'user_id': None, 'review_id': None}
        title = review['title']
        if title:
            if title[-1] != '.':
                title = title + '. '
            if 'text' in review and review['text'] != []:
                text = " ".join(review['text'])
                rev['text'] = title + text
            else:
                rev['text'] = title
        elif 'text' in review and review['text'] != []:
            text = " ".join(review['text'])
            rev['text'] = text
        else:
            #print 'no text'
            rev = {'text': None, 'user_id': None, 'review_id': None}
            continue
        if 'birth_year' in data and data['birth_year']:
            rev['age'] = int(review['date'][:4]) - int(data['birth_year'])

        rev['review_id'] = data['user_id'] + '00' + str(re_id)
        rev['user_id'] = data['user_id']
        if 'gender' in data:
            rev['gender'] = data['gender']

        locations = data['location'].split(",")
        rev['country'] = locations[-1].strip() # last entry is always the country, but strip whitespaces before/after name
        if len(locations) > 1:
            city = locations[0]
            rev['city'] = city.replace(" Municipality", "")
#            print rev['country'], type(rev['country'])
            try:
                # print 'USER ID', rev['user_id']
                cc = country_codes[rev['country']]
                rev['location'] = locdata[cc][rev['city']]
                rev['location_rpt'] = locdata[cc][rev['city']]
                rev['nuts-1'] = data['NUTS-1']
                rev['nuts-2'] = data['NUTS-2']
                rev['nuts-3'] = data['NUTS-3']
            except KeyError as e:
                print('KeyError using ', e)
                print('USER ID', rev['user_id'])
                # print 'country: ', rev['country']
                print('city: ', rev['city'])
                # cc = rev['country']
                # rev['location'] = locdata[cc][rev['city']]
#            print 'only 1 loc', rev['country']

        reviews.append(rev)
    return reviews



#i= 0
if len(sys.argv) == 3:
    if sys.argv[2] == 'user':
        s = solr.SolrConnection('http://localhost:8983/solr/trustpilot_users')
        if sys.argv[1][-6:] == '.conll':
            for user in read_user_reviews(sys.argv[1][:-6]):
                user['reviews'] = get_reviews(user)
                #s.add_many([user])
                print([user])
                break
        else:
            pass
    elif sys.argv[2] == 'review':
        s = solr.SolrConnection('http://localhost:8983/solr/trustpilot_reviews')
        if sys.argv[1][-6:] == '.conll':
            pass
        elif sys.argv[1][-6:] == '.jsonl':
            jfile = open(sys.argv[1])
            for line in jfile:
                reviews = read_json_line(line)
                # print reviews
                # break
                # print "THIS   ########################### "
                # print "Marks  ###                     ### "
                # print "New    ###                     ### "
                # print "Review ###########################"
                # print reviews
                s.add_many(reviews)
        else:
            #i = 1
            for review in read_reviews(sys.argv[1]):
                s.add_many([review])
                #print [review]
                #i += 1
                #if i > 20: break

    else: arguments()
else:
    arguments()

if s: # We have established a connection
    s.commit()

