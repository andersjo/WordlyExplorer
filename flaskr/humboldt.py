import json
import flask
import pandas as pd
import requests
from bokeh.charts import Bar
from bokeh.embed import components
from flask import request
from config import *

# Create the application.
HUMBOLDT_APP = flask.Flask(__name__)

# TODO: add a pandas DataFrame with totals

# TODO: side-by-side comparison


@HUMBOLDT_APP.route('/', methods=['GET', 'POST'])
def welcome():
    """
    landing page with welcome message
    :return:
    """
    if request.method == 'POST':
        return do_single_search(request.form)

    else:
        return flask.render_template('index.html', map_views=MAP_VIEWS, available_options=AVAILABLE_OPTIONS)


@HUMBOLDT_APP.route('/search', methods=['GET', 'POST'])
def search():
    """
    Displays the search page accessible at '/search'
    """
    if request.method == 'POST':
        return do_single_search(request.form)

    else:
        return flask.render_template('search.html',
                                     map_views=MAP_VIEWS,
                                     available_options=AVAILABLE_OPTIONS)


@HUMBOLDT_APP.route('/about')
def about():
    """
    the page about us
    :return:
    """
    return flask.render_template('about.html')


@HUMBOLDT_APP.route('/contact')
def contact():
    """
    the contact info
    :return:
    """
    return flask.render_template('contact.html')


@HUMBOLDT_APP.route('/maptest')
def maptest():
    return flask.render_template('maptest.html')


def do_single_search(request_form):
    """
    search method called from both welcome() and search()
    :param request_form:
    :return:
    """
    search_terms = request_form["singleTermQuery"]
    language_var, country_var = request_form["languageAndRegion"].split(':', 1)
    json_results = single_term_to_JSON(search_terms,
                                       language_code=language_var,
                                       country_code=country_var)

    # TODO move plotting to its own function
    gender_buckets = buckets_to_series(json_results['facets']['genders']['buckets'])
    print(gender_buckets)

    # TODO the indices are off
    age_buckets = buckets_to_series(json_results['facets']['ages']['buckets'])
    print(age_buckets)

    gender_plot = Bar(gender_buckets,
               title="Gender distribution",
               logo=None,
               toolbar_location="below")

    age_plot = Bar(age_buckets,
               title="Age distribution",
               logo=None,
               toolbar_location="below")


    bokeh_script, (gender_plot_div, age_plot_div) = components((gender_plot, age_plot))

    return flask.render_template('single_term_results.html',
                                 query=request_form["singleTermQuery"],
                                 bokeh_script=bokeh_script,
                                 gender_plot=gender_plot_div,
                                 age_plot=age_plot_div,
                                 json_results=json.dumps(json_results, indent=True),
                                 country_code=country_var,
                                 map_views=MAP_VIEWS,
                                 available_options=AVAILABLE_OPTIONS
                                 )



def buckets_to_series(bucket_dict):
    """
    Converts a a list of buckets to a pd.Series.
    Buckets are given as a list of JSON dicts, following the Solr buckets format.
    """
    return pd.DataFrame(bucket_dict).set_index('val')['count']


def single_term_to_JSON(search_term, country_code, language_code):
    """
    search for a single term in a country and language
    """
    json_query = {
        "query": "body_text_ws:{}".format(search_term),
        "facet": {
            "genders": {
                "type": "terms",
                "field": "gender_s",
                "facet": {
                    "mean_age": "min(age_i)"
                }
            },
            "ages": {
                "start" : MIN_AGE,
                "end" : MAX_AGE,
                "type": "range",
                "field": "age_i",
                "gap": 1,
                "facet": {
                    "genders":{
                    "type": "terms",
                    "field": "gender_s"
                    }
                }

            },
            "nuts_3_regions": {
                "type": "terms",
                "field": "nuts_3_s",
                "limit": 1000
            },
            "mean_age": "avg(age_i)",
            "percentiles_age": "percentile(age_i, 25, 50, 75)"
        },
        "filter": ["country_s:{}".format(country_code),
                   "langid_s:{}".format(language_code)
                   ],

        "limit": 2
    }

    resp = requests.post(SOLR_QUERY_URL, json=json_query)
    if not resp.ok:
        print("Request failed: " + resp.text)
        resp.raise_for_status()
    return resp.json()


if __name__ == '__main__':
    HUMBOLDT_APP.run(debug=True)
    # DebuggedApplication(HUMBOLDT_APP, evalex=True)
    # .run(debug=True)
