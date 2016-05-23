import json
from _bisect import bisect

import flask
import pandas as pd
import requests
from bokeh.charts import Bar
from bokeh.embed import components
from config import AVAILABLE_OPTIONS
from config import MAP_VIEWS
from config import MIN_AGE, MAX_AGE
from config import NOT_AVAIL
from config import SOLR_QUERY_URL
from config import TOTALS
from config import P_LEVELS
from flask import request
from scipy.stats import chi2_contingency, spearmanr

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
        return flask.render_template('index.html', map_views=MAP_VIEWS,
                                     available_options=AVAILABLE_OPTIONS,
                                     totals=TOTALS)


@HUMBOLDT_APP.route('/search', methods=['GET', 'POST'])
def search():
    """
    Displays the search page accessible at '/search'
    """
    if request.method == 'POST':
        if len(request.form) == 2:
            return do_single_search(request.form)
        elif len(request.form) == 3:
            return do_double_search(request.form)

    else:
        return flask.render_template('search.html',
                                     map_views=MAP_VIEWS,
                                     available_options=AVAILABLE_OPTIONS,
                                     totals=TOTALS)


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


@HUMBOLDT_APP.route('/comparisontest')
def comparisontest():
    if request.method == 'POST':
        return do_double_search(request.form)
    else:
        return flask.render_template('comparison_test.html',
                                     map_views=MAP_VIEWS,
                                     available_options=AVAILABLE_OPTIONS)


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

    if json_results['response']['numFound'] == 0:
        return flask.render_template('no_results.html', query=search_terms, available_options=AVAILABLE_OPTIONS, search_mode='single')

    country_total = TOTALS[TOTALS['country_code'] == country_var]['count'].sum()

    gender_buckets = buckets_to_series(json_results['facets']['genders']['buckets'])
    gender_buckets = gender_buckets[[val for val in gender_buckets.index if val != NOT_AVAIL]] / country_total
    age_buckets = buckets_to_series(json_results['facets']['ages']['buckets']) / country_total
    age_gender_buckets = compound_bucket_to_series(json_results['facets']['gender_and_age']['buckets'],
                                                   'gender_and_age')
    age_gender_buckets['count'] /= country_total
    age_gender_buckets = age_gender_buckets[
        (age_gender_buckets['age'] <= MAX_AGE) & (age_gender_buckets['age'] >= MIN_AGE) & (
        age_gender_buckets['gender'] != NOT_AVAIL)].sort('age')

    # TODO: get total count per region and normalize by that?
    nuts_buckets = buckets_to_series(json_results['facets']['nuts_3_regions']['buckets'])
    nuts_totals = TOTALS.groupby('nuts_3').sum()
    nuts_buckets = (nuts_buckets / nuts_totals.ix[nuts_buckets.index, :]['count'].fillna(1).values).to_json()

    # TODO move plotting to its own function
    gender_plot = Bar(gender_buckets,
                      title="Gender distribution",
                      logo=None,
                      toolbar_location="below",
                      width=300,
                      height=400, webgl=True)

    age_plot = Bar(age_buckets,
                   title="Age distribution",
                   logo=None,
                   toolbar_location="below",
                   width=800,
                   height=400, webgl=True)

    age_gender_plot = Bar(age_gender_buckets,
                          group='gender',
                          label='age',
                          values='count',
                          title="Age distribution by gender",
                          logo=None,
                          toolbar_location="below",
                          width=1200,
                          height=400,
                          legend='top_right',
                          color=['blue', 'green'], webgl=True)

    bokeh_script, (gender_plot_div, age_plot_div, age_gender_plot_div) = components(
        (gender_plot, age_plot, age_gender_plot))

    return flask.render_template('single_term_results.html',
                                 query=request_form["singleTermQuery"],
                                 bokeh_script=bokeh_script,
                                 gender_plot=gender_plot_div,
                                 age_plot=age_plot_div,
                                 age_gender_plot=age_gender_plot_div,
                                 json_results=json_results,
                                 country_code=country_var,
                                 map_views=MAP_VIEWS,
                                 nuts_buckets=nuts_buckets,
                                 country_total=country_total,
                                 available_options=AVAILABLE_OPTIONS
                                 )


def compound_bucket_to_series(count_dict_list, compound_field):
    """
    convert compound fields to pd.DataFrame
    :param count_dict_list:
    :param compound_field:
    :return:
    """
    field_parts = compound_field.split("_and_")

    rows = []
    for count_dict in count_dict_list:
        value_parts = count_dict["val"].split(":")
        row = {"count": count_dict["count"]}
        for field, value in zip(field_parts, value_parts):
            if field == 'age':
                try:
                    row[field] = int(value)
                except ValueError:
                    row[field] = -1
            else:
                row[field] = value

        rows.append(row)

    return pd.DataFrame(rows)


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
                "start": MIN_AGE,
                "end": MAX_AGE,
                "type": "range",
                "field": "age_i",
                "gap": 1
                # "facet": {
                #     "genders":{
                #     "type": "terms",
                #     "field": "gender_s"
                #     }
                # }

            },
            "nuts_3_regions": {
                "type": "terms",
                "field": "nuts_3_s",
                "limit": -1
            },
            "gender_and_age": {
                "type": "terms",
                "field": "gender_and_age_s",
                "limit": -1
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


def do_double_search(request_form):
    """
    search method called from both welcome() and search()
    :param request_form:
    :return:
    """
    search_term1 = request_form["doubleTermQuery1"]
    search_term2 = request_form["doubleTermQuery2"]
    language_var, country_var = request_form["languageAndRegion"].split(':', 1)
    json_results1 = single_term_to_JSON(search_term1,
                                        language_code=language_var,
                                        country_code=country_var)
    json_results2 = single_term_to_JSON(search_term2,
                                        language_code=language_var,
                                        country_code=country_var)

    if json_results1['response']['numFound'] == 0:
        return flask.render_template('no_results.html', query=search_term1, available_options=AVAILABLE_OPTIONS, search_mode='double')
    elif json_results2['response']['numFound'] == 0:
        return flask.render_template('no_results.html', query=search_term2, available_options=AVAILABLE_OPTIONS, search_mode='double')


    total_found = TOTALS[TOTALS['country_code'] == country_var]['count'].sum()

    gender_buckets1 = buckets_to_series(json_results1['facets']['genders']['buckets'])
    gender_buckets2 = buckets_to_series(json_results2['facets']['genders']['buckets'])
    gender_buckets1 = gender_buckets1[[val for val in gender_buckets1.index if val != NOT_AVAIL]]
    gender_buckets2 = gender_buckets2[[val for val in gender_buckets2.index if val != NOT_AVAIL]]

    gender_comparison = pd.DataFrame(data={search_term1:gender_buckets1.values, search_term2:gender_buckets2.values}, index=gender_buckets1.index)
    chi2, pvalue, dof, expected = chi2_contingency(gender_comparison)
    gender_stats_level = bisect(P_LEVELS, pvalue)

    if gender_stats_level == len(P_LEVELS):
        gender_stats_msg = "Gender difference is <em>not</em> statistically significant (p > %s)" % (P_LEVELS[-1])
    else:
        gender_stats_msg = "Gender difference is statistically significant at p < %s" % (P_LEVELS[gender_stats_level])


    age_buckets1 = buckets_to_series(json_results1['facets']['ages']['buckets'])
    age_buckets2 = buckets_to_series(json_results2['facets']['ages']['buckets'])

    print(age_buckets1, age_buckets2)
    age_comparison = pd.DataFrame(data={search_term1:age_buckets1.values, search_term2:age_buckets2.values}, index=age_buckets1.index)
    r, pvalue = spearmanr(age_comparison)
    age_stats_level = bisect(P_LEVELS, pvalue)

    if age_stats_level == len(P_LEVELS):
        age_stats_msg = "Age difference is <em>not</em> statistically significant (p > %s)" % (P_LEVELS[-1])
    else:
        age_stats_msg = "Age difference is statistically significant at p < %s" % (P_LEVELS[age_stats_level])


    return flask.render_template('comparison_term_results.html',
                                 query1=request_form["doubleTermQuery1"],
                                 query2=request_form["doubleTermQuery2"],
                                 gender_comparison=gender_comparison.to_html(),
                                 gender_stats_msg=gender_stats_msg,
                                 age_comparison=age_comparison.to_html(),
                                 age_stats_msg=age_stats_msg,
                                 # bokeh_script=bokeh_script,
                                 # gender_plot=gender_plot_div,
                                 # age_plot=age_plot_div,
                                 json_results1=json_results1,
                                 json_results2=json_results2,
                                 country_code=country_var,
                                 map_views=MAP_VIEWS,
                                 available_options=AVAILABLE_OPTIONS
                                 )


if __name__ == '__main__':
    HUMBOLDT_APP.run(debug=True)
    # DebuggedApplication(HUMBOLDT_APP, evalex=True)
    # .run(debug=True)
