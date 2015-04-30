#!/usr/bin/env python2

import flask
import solr
import cgi, cgitb
import vincent
import matplotlib.pyplot as plt
import numpy as np
import cStringIO
import seaborn as sns
import codecs
import helper_scripts

from itertools import islice
from flask import request

# Create the application.
APP = flask.Flask(__name__)

# Create connection to solr database
s = solr.SolrConnection('http://localhost:8983/solr/trustpilot_reviews')

# Use seaborn
sns.set()
#sns.set_context("talk")
# sns.palplot(sns.color_palette()) # This causes a bunch of error messages to be displayed...QPixmap: It is not safe to use pixmaps outside the GUI thread

def make_country_codes():
    codes = {}
    reverse_cc = {}
    ccfile = codecs.open('../data/iso_country_codes.csv', encoding='utf-8')
    ccfile.next()
    for line in ccfile:
        cc, country = line.replace('"', '').strip('\r\n').strip().split(',')
        codes[country] = cc
        reverse_cc[cc] = country

    return codes, reverse_cc

country_codes, reverse_cc = make_country_codes()


def make_age_bars():
    return


def hist_ages_gender(term, ages_men, ages_women, total_men, total_women, min_age=10, max_age=90, num_bins=9):

    fig = plt.figure() # Fig name just to be able to close it again
    plt.title('Age and gender distribution for:     ' + term + '')
    plt.xlabel('Age range')
    plt.ylabel('Number of people')

    male_sorted = np.array([value for (key, value) in sorted(ages_men.items())])
    female_sorted = np.array([value for (key, value) in sorted(ages_women.items())])
    total_male_sorted = np.array([float(value) for (key, value) in sorted(total_men.items())])
    total_female_sorted = np.array([float(value) for (key, value) in sorted(total_women.items())])

#    print male_sorted
#    print total_male_sorted
#    print male_sorted/total_male_sorted

    bar_width = 0.35
    displace = bar_width/2
    plt.bar(np.array(range(len(ages_men))) + displace, male_sorted/total_male_sorted, bar_width, align='edge', label='Male', color='b')
    plt.bar(np.array(range(len(ages_women))) + displace + bar_width, female_sorted/total_female_sorted, bar_width, align='edge', label='Female', color='g')
    plt.xticks(range(len(ages_men)), sorted(ages_men))

    plt.legend()
    plt.tight_layout()
    sio = cStringIO.StringIO()
    plt.savefig(sio, format="jpg")
    plt.close(fig) # Close figures to save mem
    return sio



# def make_bars(distribution, labels, term = ''):
#     fig = plt.figure()
#     plt.title('# of hits for \"' + labels[0] + '\" and \"' + labels[1] + '\"')
#     if len(term):
#         plt.title('# of hits for \"' + labels[0] + '\" and \"' + labels[1] + '\" for \"' + term + '\"')
#     plt.bar([1,2],distribution)
#     plt.xticks([1.4,2.4], labels)
#     sio = cStringIO.StringIO()
#     plt.savefig(sio, format="jpg")
#     plt.close(fig)
#     return sio

def get_stats(responses, responsesM, responsesF):

    genders = responses.facet_counts[u'facet_fields'][u'gender']
    ages = responses.facet_counts[u'facet_ranges'][u'age'][u'counts']
    agesM = responsesM.facet_counts[u'facet_ranges'][u'age'][u'counts']
    agesF = responsesF.facet_counts[u'facet_ranges'][u'age'][u'counts']
    return ages, genders, agesM, agesF

def do_query(query):
    frstart = 10
    frend = 89
    frgap = 10
    country = reverse_cc[request.form['country'][-2:]]
    facet_fields=['gender', 'location']
    geofcph = '{!geofilt pt=55.676,12.568 sfield=location d=25}'
    geofaarhus = '{!geofilt pt=56.157,10.21 sfield=location d=25}'
    filterq = ['country:\"' + country + '\"']
    filterqM = ['country:\"' + country + '\"', 'gender:M']
    filterqF = ['country:\"' + country + '\"', 'gender:F']
    print request.form['region']
    if request.form['region'] == 'cph':
        filterq.append(geofcph)
        filterqM.append(geofcph)
        filterqF.append(geofcph)
    elif request.form['region'] == 'aarhus':
        filterq.append(geofaarhus)
        filterqM.append(geofaarhus)
        filterqF.append(geofaarhus)
    response = s.query(query, rows=5, facet='true', facet_range=['age'], facet_range_start=frstart, facet_range_end=frend, facet_range_gap=frgap, facet_field=facet_fields, fq=filterq)
    responseM = s.query(query, rows=5, facet='true', facet_range=['age'], facet_range_start=frstart, facet_range_end=frend, facet_range_gap=frgap, facet_field=facet_fields, fq=filterqM)
    responseF = s.query(query, rows=5, facet='true', facet_range=['age'], facet_range_start=frstart, facet_range_end=frend, facet_range_gap=frgap, facet_field=facet_fields, fq=filterqF)
    response_texts = [response_t['text'] for response_t in response]
    return (response_texts, response, responseM, responseF)


def term_to_query(term):
    return "text:" + term  # Remember to set which field to query on (text for review-centric, review for user-centric)

@APP.route('/')
def index():
    """ Displays the index page accessible at '/'
    """
    return flask.render_template('trustpilot.html', queries = [])

@APP.route('/results', methods=['POST'])
def show_results():
    """ Displays the results of our query at '/results'
    """
    query = "text:*" # Remember to set which field to query on (text for review-centric, review for user-centric)

    _, data, dataM, dataF = do_query(query)

    total_ages, total_gender, total_ageM, total_ageF = get_stats(data, dataM, dataF)

    num_responses = [0,0]
    response_texts = [[],[]]
    response_full = []
    responseM = []
    responseF = []
    term = ["", ""]
    # get searches
    if request.method == 'POST':
        for i in range(2):
            box = 'searchbox' + str(i+1)
            if request.form[box]:
                term[i] = request.form[box]
                response_texts[i], response, respM, respF = do_query(term_to_query(term[i]))
                response_full.append(response)
                responseM.append(respM)
                responseF.append(respF)
                num_responses[i] = response.numFound

        print 'num_responses: ', num_responses
        ages = [0,0]
        genders = [dict, dict]
        agesM = [dict, dict]
        agesF = [dict, dict]
        for i in range(len(response_full)):
            ages[i], genders[i], agesM[i], agesF[i] = get_stats(response_full[i], responseM[i], responseF[i])


        # ages, genders = zip(get_stats(response_full[0]), get_stats(response_full[1]))

        age_gen_hist = []
        for i in range(len(response_full)):
            age_gen_hist.append(hist_ages_gender(term[i], agesM[i], agesF[i], total_ageM, total_ageF))
        while len(age_gen_hist) < 2:
            age_gen_hist.append(cStringIO.StringIO())

        genders = [[genders[i][u''], genders[i][u'M'], genders[i][u'F']] for i in range(len(response_full))]
        while len(genders) < 2:
            genders.append([0,0,0])
#        print 'genders:', genders
        # gen_bars = [make_bars(genders[0], ['Male', 'Female'], term1), make_bars(genders[1], ['Male', 'Female'], term2)]
        # distribution = make_bars(num_responses, [term1, term2])

        #select = solr.SearchHandler(s, "/select")

        # print 'this is a select: ', s.query('text:*', facet='true', facet_fields=['gender', 'age', 'location'], fq='gender:M')
        # print 'this is a select: ', s.query('text:*', facet='true', facet_fields=['gender', 'age', 'location'], fq='gender:F').numFound
        # print s.query('*:*', facet='true', facet_field=['gender', 'age', 'location']).facet_counts[u'facet_fields'][u'gender']

        cities = s.query('text:det er', facet='true', facet_limit=-1, facet_field=['gender', 'age','city'], fq=['country:Denmark']).facet_counts[u'facet_fields'][u'city']
        hitslist = [[city, val] for city, val in cities.iteritems() if val > 0]
        print len(hitslist)

#        print helper_scripts.locdata
#        for line in hitslist:
#            print line



        return flask.render_template('show_results.html', responses = [response_texts[0], response_texts[1]],
                                     queries = [term[0], term[1]], distribution = num_responses,
                                     agegenhist0 = age_gen_hist[0], agegenhist1 = age_gen_hist[1],
                                     genders = genders, country = request.form['country'],
                                     region = request.form['region'])
    else:
        return flask.render_template('trustpilot.html', queries = [])

if __name__ == '__main__':
    APP.debug=True
    APP.run()
