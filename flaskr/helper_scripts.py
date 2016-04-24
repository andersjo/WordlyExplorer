import codecs

def make_country_codes():
    codes = {}
    reverse_cc = {}
    ccfile = open('../data/iso_country_codes.csv')
    next(ccfile)
    for line in ccfile:
        cc, country = line.replace('"', '').strip('\r\n').strip().split(',')
        codes[country] = cc
        reverse_cc[cc] = country

    return codes, reverse_cc

country_codes, _ = make_country_codes()

