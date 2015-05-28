import codecs
import numpy as np
from collections import defaultdict


def locationData(filename):
    data = defaultdict(lambda: defaultdict(list))
    locfile = codecs.open(filename, encoding='utf-8')
    for line in locfile:
        Country_code, city, _, location = line.strip("\n").split("\t")
        # print 'befor location: ', location
        if len(location)<5:
            continue
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
    ccfile.next()
    for line in ccfile:
        cc, country = line.replace('"', '').strip('\r\n').strip().split(',')
        codes[country] = cc
        reverse_cc[cc] = country

    return codes, reverse_cc

country_codes, _ = make_country_codes()

