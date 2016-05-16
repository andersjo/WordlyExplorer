import json
import flask
from flask import request
import pandas as pd
import requests
import bokeh
from bokeh.charts import Bar
from bokeh.plotting import figure
from bokeh.embed import components

# Create the application.
HUMBOLDT_APP = flask.Flask(__name__)

# TODO move to separate file, and include map info
SOLR_URL = "http://localhost:8983/solr/humboldt"
SOLR_SELECT_URL = SOLR_URL + "/select?wt=json"
SOLR_QUERY_URL = SOLR_URL + "/query"

#TODO: add a pandas DataFrame with totals

#TODO: side-by-side comparison

#TODO: index page


@HUMBOLDT_APP.route('/')
def welcome():
    return flask.render_template('index.html')



@HUMBOLDT_APP.route('/maptest')
def maptest():
    return flask.render_template('maptest.html')


@HUMBOLDT_APP.route('/search', methods=['GET', 'POST'])
def index():
    """
    Displays the index page accessible at '/'
    """
    if request.method == 'POST':
        # print(request.form['query'])
        # result = request.form['query']
        search_terms = request.form["singleTermQuery"]

        language_var, country_var = request.form["languageAndRegion"].split(':', 1)
        json_results = search_single_term(search_terms,
                                          language_code=language_var,
                                          country_code=country_var)

        # TODO move plotting to its own function
        gender_buckets = buckets_to_series(json_results['facets']['genders']['buckets'])
        print(gender_buckets)

        plot = Bar(gender_buckets,
                   title="Gender distribution",
                   logo=None,
                   toolbar_location="below")

        bokeh_script, gender_plot_div = components(plot)

        return flask.render_template('single_term.html',
                                     query=request.form["singleTermQuery"],
                                     bokeh_script=bokeh_script,
                                     gender_plot=gender_plot_div,
                                     json_results=json.dumps(json_results, indent=True)
                                     )
    else:
        return flask.render_template('single_term.html')



@HUMBOLDT_APP.route('/about')
def about():
    return flask.render_template('about.html')


@HUMBOLDT_APP.route('/contact')
def contact():
    return flask.render_template('contact.html')


def buckets_to_series(bucket_dict):
    """Converts a a list of buckets to a pd.Series.

    Buckets are given as a list of JSON dicts, following the Solr buckets format.
    """
    return pd.DataFrame(bucket_dict).set_index('val')['count']


def search_single_term(search_term, country_code, language_code):
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
                    "mean_age": "avg(age_i)"
                }
            },
            "nuts_2_regions": {
                "type": "terms",
                "field": "nuts_2_s"},
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

