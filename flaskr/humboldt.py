import json
from _bisect import bisect

import flask
import pandas as pd
import requests
from bokeh.charts import Bar, Line
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
from numpy import sign, arange

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
    # nuts_totals = TOTALS.groupby('nuts_3').sum()
    nuts_buckets_norm = nuts_buckets[[val for val in nuts_buckets.index if val.lower().startswith(country_var)]]
    nuts_buckets_norm /= nuts_buckets_norm.sum()
    nuts_buckets = nuts_buckets_norm.to_json()#nuts_totals.ix[nuts_buckets.index, :]['count'].fillna(1).values).to_json()
    # is a term more prevalent in on region, i.e., more frequent than the median?
    special_regions = nuts_buckets_norm > nuts_buckets_norm.median()
    outliers = ', '.join(sorted([x for x in special_regions.index if special_regions.ix[x].any() == True]))

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
                                 outliers=outliers,
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


    country_total = TOTALS[TOTALS['country_code'] == country_var]['count'].sum()

    gender_buckets1 = buckets_to_series(json_results1['facets']['genders']['buckets'])
    gender_buckets2 = buckets_to_series(json_results2['facets']['genders']['buckets'])
    gender_buckets1 = gender_buckets1[[val for val in gender_buckets1.index if val != NOT_AVAIL]]
    gender_buckets2 = gender_buckets2[[val for val in gender_buckets2.index if val != NOT_AVAIL]]

    gender_comparison = pd.DataFrame(data={search_term1:gender_buckets1.values, search_term2:gender_buckets2.values}, index=gender_buckets1.index).T
    del gender_comparison.index.name
    chi2, pvalue, dof, expected = chi2_contingency(gender_comparison)
    gender_stats_level = bisect(P_LEVELS, pvalue)

    if gender_stats_level == len(P_LEVELS):
        gender_stats_msg = "Gender difference is <em>not</em> statistically significant (Chi-squared contingency test with p > %s)" % (P_LEVELS[-1])
    else:
        gender_stats_msg = "Gender difference is statistically significant at p < %s (p = %s with Chi-squared contingency test)" % (P_LEVELS[gender_stats_level], pvalue)

    age_buckets1 = buckets_to_series(json_results1['facets']['ages']['buckets'])
    age_buckets2 = buckets_to_series(json_results2['facets']['ages']['buckets'])

    age_comparison = pd.DataFrame(data={search_term1:age_buckets1.values, search_term2:age_buckets2.values}, index=age_buckets1.index)
    r, pvalue = spearmanr(age_comparison)
    age_stats_level = bisect(P_LEVELS, pvalue)

    if age_stats_level == len(P_LEVELS):
        age_stats_msg = "Age difference is <em>not</em> statistically significant (p > %s)" % (P_LEVELS[-1])
    else:
        age_stats_msg = "Age difference is <em>statistically significant</em> at p < %s (p = %s)" % (P_LEVELS[age_stats_level], pvalue)

    J = pd.DataFrame(gender_comparison.unstack())
    L = pd.DataFrame(data={'variable':[J.index.levels[1][x] for x in J.index.labels[1]], 'gender':[J.index.levels[0][x] for x in J.index.labels[0]], 'count':(J/country_total).values.T[0].tolist()})

    gender_plot = Bar(L,
                          group='gender',
                          label='variable',
                          values='count',
                          title="Distribution by gender",
                          logo=None,
                          toolbar_location="below",
                          width=600,
                          height=400,
                          legend='top_right',
                          color=['blue', 'green'],
                          webgl=True)


    nuts_totals = TOTALS.groupby('nuts_3').sum()
    regions = [x for x in nuts_totals.index if x.lower().startswith(country_var)]
    country_nuts_total = float(nuts_totals.ix[regions].sum())

    # get the info by the bucket
    nuts_buckets1 = buckets_to_series(json_results1['facets']['nuts_3_regions']['buckets'])
    nuts_buckets2 = buckets_to_series(json_results2['facets']['nuts_3_regions']['buckets'])
    nuts_buckets1 = nuts_buckets1[[val for val in nuts_buckets1.index if val.lower().startswith(country_var)]]/ country_nuts_total
    nuts_buckets2 = nuts_buckets2[[val for val in nuts_buckets2.index if val.lower().startswith(country_var)]]/ country_nuts_total

    # compute the differences between the two terms
    # TODO: there is probably a better way
    nutsdiff = pd.DataFrame(0, index=regions, columns=arange(1))
    for region in regions:
        if region in nuts_buckets1.index:
            if region in nuts_buckets2.index:
                nutsdiff.ix[region] = nuts_buckets1.ix[region] - nuts_buckets2.ix[region]
            else:
                nutsdiff.ix[region] = nuts_buckets1.ix[region]
        else:
            if region in nuts_buckets2.index:
                nutsdiff.ix[region] = -nuts_buckets2.ix[region]
    # compute which term sticks out
    nutsdiff['G2'] = abs(nutsdiff[0]) > nutsdiff[0].abs().mean()

    outliers = sorted([x for x in regions if nutsdiff['G2'].ix[x].any() == True])
    is_it_term2 = nutsdiff[0].ix[outliers] < 0
    outliers1 = ', '.join(sorted([x for x in is_it_term2.index if is_it_term2[x] == False]))
    outliers2 = ', '.join(sorted([x for x in is_it_term2.index if is_it_term2[x] == True]))
    print(nutsdiff, is_it_term2)
    outlier_description = []
    if outliers1:
        outlier_description.append('<em>%s</em> is more prevalent than <em>%s</em> in regions %s' % (search_term1, search_term2, outliers1))
    if outliers2:
        if outlier_description:
            outlier_description.append(', while ')
        outlier_description.append('<em>%s</em> is more prevalent than <em>%s</em> in regions %s' % (search_term2, search_term1, outliers2))
    outlier_description = ''.join(outlier_description)

    bokeh_script, (gender_plot_div) = components((gender_plot))


    return flask.render_template('comparison_term_results.html',
                                 query1=request_form["doubleTermQuery1"],
                                 query2=request_form["doubleTermQuery2"],
                                 gender_comparison=gender_comparison.to_html(justify='right'),
                                 gender_stats_msg=gender_stats_msg,
                                 age_comparison=age_comparison.T.to_html(justify='right'),
                                 age_stats_msg=age_stats_msg,
                                 bokeh_script=bokeh_script,
                                 gender_plot=gender_plot_div,
                                 # age_plot=age_plot_div,
                                 json_results1=json_results1,
                                 json_results2=json_results2,
                                 country_code=country_var,
                                 map_views=MAP_VIEWS,
                                 country_total=country_total,
                                 outlier_description=outlier_description,
                                 available_options=AVAILABLE_OPTIONS
                                 )


if __name__ == '__main__':
    HUMBOLDT_APP.run(debug=True)
    # DebuggedApplication(HUMBOLDT_APP, evalex=True)
    # .run(debug=True)
