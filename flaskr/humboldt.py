from _bisect import bisect
from requests.exceptions import HTTPError
import flask
import pandas as pd
import sys
from bokeh.charts import Bar, Line
from bokeh.embed import components
from bokeh.models import Range1d
from config import AVAILABLE_OPTIONS
from config import MAP_VIEWS
from config import MIN_AGE, MAX_AGE
from config import NUTS_NAMES
from config import P_LEVELS
from config import ROLLING_MEAN_FRAME
from flask import request
from numpy import arange
from queries import simple_query_totals, sort_and_filter_age, prepare_age_and_gender, perform_query, terms_facet
from scipy.stats import chi2_contingency, spearmanr

# Create the application.
app = flask.Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def welcome():
    """
    landing page with welcome message
    :return:
    """
    if request.method == 'POST':
        if len(request.form) == 2:
            return do_single_search(request.form)
        elif len(request.form) == 3:
            return do_double_search(request.form)

    else:
        totals = perform_query({"query": "*:*",
                          "facet": {"country": terms_facet("country_s")}})["facets"]['country']["buckets"]
        country_totals = {country_info['val']: country_info['count'] for country_info in totals}
        # country_totals = {country_info[1]: totals[totals.country_code == country_info[1]].sum()['num_docs'].sum() for
        #                   country_info in AVAILABLE_OPTIONS}

        return flask.render_template('index.html', map_views=MAP_VIEWS,
                                     available_options=AVAILABLE_OPTIONS,
                                     totals=country_totals)


@app.route('/search', methods=['GET', 'POST'])
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
        totals = perform_query({"query": "*:*",
                          "facet": {"country": terms_facet("country_s")}})["facets"]['country']["buckets"]
        country_totals = {country_info['val']: country_info['count'] for country_info in totals}
        # totals = simple_query_totals()
        # country_totals = {country_info[1]: totals[totals.country_code == country_info[1]].sum()['num_docs'].sum() for
        #                   country_info in AVAILABLE_OPTIONS}

        return flask.render_template('search.html',
                                     map_views=MAP_VIEWS,
                                     available_options=AVAILABLE_OPTIONS,
                                     totals=country_totals)


@app.route('/about')
def about():
    """
    the page about us
    :return:
    """
    return flask.render_template('about.html')


@app.route('/contact')
def contact():
    """
    the contact info
    :return:
    """
    return flask.render_template('contact.html')


def do_single_search(request_form):
    """
    search method called from both welcome() and search()
    :param request_form:
    :return:
    """
    search_terms = request_form["singleTermQuery"].lower()
    language_var, country_var = request_form["languageAndRegion"].split(':', 1)
    try:
        specific_query = simple_query_totals({"query": "body_text_ws:%s" % search_terms,
                                              "filter": ["country_s:%s" % country_var, "langid_s:%s" % language_var]})
    except (KeyError, HTTPError):
        return flask.render_template('no_results.html', query=search_terms, available_options=AVAILABLE_OPTIONS,
                                     search_mode='single')

    matches = specific_query['num_docs'].sum()

    #############################
    # GET TOTALS FOR EVERYTHING #
    #############################
    totals = simple_query_totals({"query": "*:*",
                                        "filter": ["country_s:%s" % country_var, "langid_s:%s" % language_var]})

    gender_totals = totals.groupby('gender').num_docs.sum()

    age_totals = totals.groupby('age').num_docs.sum()
    age_totals = sort_and_filter_age(age_totals)
    age_totals_norm = age_totals / age_totals.sum()

    age_and_gender_totals = prepare_age_and_gender(totals)

    nuts_total = totals.groupby('nuts_3').num_docs.sum()

    ###########
    #  GENDER #
    ###########
    gender_specific_query = specific_query.groupby('gender').num_docs.sum()
    abs_percentages = gender_specific_query / gender_totals
    try:
        renormalizer = 1.0 / abs_percentages.sum()
    except ZeroDivisionError:
        return flask.render_template('no_results.html', query=search_terms, available_options=AVAILABLE_OPTIONS,
                             search_mode='single')

    gender_query_adjusted = abs_percentages * renormalizer

    #######
    # AGE #
    #######
    age_specific_query = specific_query.groupby('age').num_docs.sum()
    age_specific_query = sort_and_filter_age(age_specific_query)
    age_specific_query_norm = age_specific_query / age_specific_query.sum()
    compare_age_df = pd.DataFrame({'background distribution': age_totals_norm,
                                   'query': pd.rolling_mean(age_specific_query_norm, ROLLING_MEAN_FRAME)})
    compare_age_df['i'] = compare_age_df.index

    ##################
    # AGE AND GENDER #
    ##################
    age_and_gender_specific_query = prepare_age_and_gender(specific_query)

    try:
        age_specific_male_totals = gender_specific_query['M'].sum()
        compare_male_df = pd.DataFrame({'background distribution': age_and_gender_totals['M'],
                                        'query': pd.rolling_mean(age_and_gender_specific_query['M'],
                                                                 ROLLING_MEAN_FRAME)})
    except KeyError:
        age_specific_male_totals = 0
        compare_male_df = pd.DataFrame({'background distribution': age_and_gender_totals['M']})
    compare_male_df['i'] = compare_male_df.index

    try:
        age_specific_female_totals = gender_specific_query['F']
        compare_female_df = pd.DataFrame({'background distribution': age_and_gender_totals['F'],
                                          'query': pd.rolling_mean(age_and_gender_specific_query['F'],
                                                                   ROLLING_MEAN_FRAME)})
    except KeyError:
        age_specific_female_totals = 0
        compare_female_df = pd.DataFrame({'background distribution': age_and_gender_totals['F']})
    compare_female_df['i'] = compare_female_df.index

    ########
    # NUTS #
    ########
    nuts_query = specific_query.groupby('nuts_3').num_docs.sum()
    nuts_query_norm = nuts_query / nuts_total
    special_regions = nuts_query_norm > nuts_query_norm.median()

    outliers = ', '.join(
        sorted(['%s (%s)' % (NUTS_NAMES[x], x) for x in special_regions.index if special_regions.ix[x].any() == True]))

    # TODO move plotting to its own function
    gender_plot = Bar(gender_query_adjusted,
                      title="Gender distribution",
                      ylabel="percentage",
                      logo=None,
                      toolbar_location="below",
                      # width=300,
                      # height=400,
                      webgl=False)

    age_plot = Line(compare_age_df,
                    x='i',
                    title="Age distribution",
                    x_range=Range1d(start=MIN_AGE, end=MAX_AGE),
                    xlabel='age',
                    ylabel="percentage",
                    logo=None,
                    toolbar_location="below",
                    # width=800,
                    # height=400,
                    legend='top_right',
                    color=['silver', 'red'],
                    webgl=False)

    age_gender_plot_M = Line(compare_male_df,
                             x='i',
                             title="Age distribution for men",
                             xlabel='age',
                             ylabel="percentage",
                             x_range=Range1d(start=MIN_AGE, end=MAX_AGE),
                             logo=None,
                             toolbar_location="below",
                             # width=600,
                             # height=400,
                             legend='top_right',
                             color=['silver', 'green'],
                             webgl=False)
    age_gender_plot_F = Line(compare_female_df,
                             x='i',
                             title="Age distribution for women",
                             xlabel='age',
                             x_range=Range1d(start=MIN_AGE, end=MAX_AGE),
                             logo=None,
                             toolbar_location="below",
                             # width=600,
                             # height=400,
                             legend='top_right',
                             color=['silver', 'blue'],
                             webgl=False)

    bokeh_script, (gender_plot_div, age_plot_div, age_gender_plot_F_div, age_gender_plot_M_div) = components(
        (gender_plot, age_plot, age_gender_plot_F, age_gender_plot_M))

    return flask.render_template('single_term_results.html',
                                 query=search_terms,
                                 matches=matches,
                                 bokeh_script=bokeh_script,
                                 gender_query_adjusted=gender_query_adjusted,
                                 gender_plot=gender_plot_div,
                                 age_plot=age_plot_div,
                                 age_gender_plot_F=age_gender_plot_F_div,
                                 age_gender_plot_M=age_gender_plot_M_div,
                                 country_code=country_var,
                                 map_views=MAP_VIEWS,
                                 nuts_query=nuts_query_norm.to_json(),
                                 outliers=outliers,
                                 gender_total=gender_specific_query.sum(),
                                 age_total=age_specific_query.sum(),
                                 age_total_M=age_specific_male_totals,
                                 age_total_F=age_specific_female_totals,
                                 nuts_total=nuts_query.sum(),
                                 available_options=AVAILABLE_OPTIONS)


def do_double_search(request_form):
    """
    search method called from both welcome() and search()
    :param request_form:
    :return:
    """
    search_term1 = request_form["doubleTermQuery1"].lower()
    search_term2 = request_form["doubleTermQuery2"].lower()
    language_var, country_var = request_form["languageAndRegion"].split(':', 1)

    try:
        specific_query1 = simple_query_totals({"query": "body_text_ws:%s" % search_term1,
                                               "filter": ["country_s:%s" % country_var, "langid_s:%s" % language_var]})
    except (KeyError, HTTPError):
        return flask.render_template('no_results.html', query=search_term1, available_options=AVAILABLE_OPTIONS,
                                     search_mode='double')

    try:
        specific_query2 = simple_query_totals({"query": "body_text_ws:%s" % search_term2,
                                               "filter": ["country_s:%s" % country_var, "langid_s:%s" % language_var]})
    except (KeyError, HTTPError):
        return flask.render_template('no_results.html', query=search_term2, available_options=AVAILABLE_OPTIONS,
                                     search_mode='double')

    # need to check country again for some reason
    matches = [specific_query1['num_docs'].sum(), specific_query2['num_docs'].sum()]

    #############################
    # GET TOTALS FOR EVERYTHING #
    #############################
    totals = simple_query_totals({"query": "*:*",
                                        "filter": ["country_s:%s" % country_var, "langid_s:%s" % language_var]})

    gender_totals = totals.groupby('gender').num_docs.sum()

    age_totals = totals.groupby('age').num_docs.sum()
    age_totals = sort_and_filter_age(age_totals)
    age_totals_norm = age_totals / age_totals.sum()

    ###########
    #  GENDER #
    ###########
    gender_specific_query1 = specific_query1.groupby('gender').num_docs.sum()
    gender_specific_query2 = specific_query2.groupby('gender').num_docs.sum()
    abs_percentages1 = gender_specific_query1 / gender_totals
    abs_percentages2 = gender_specific_query2 / gender_totals
    try:
        renormalizer1 = 1.0 / abs_percentages1.sum()
    except ZeroDivisionError:
        return flask.render_template('no_results.html', query=search_term1, available_options=AVAILABLE_OPTIONS,
                             search_mode='double')
    try:
        renormalizer2 = 1.0 / abs_percentages2.sum()
    except ZeroDivisionError:
        return flask.render_template('no_results.html', query=search_term2, available_options=AVAILABLE_OPTIONS,
                             search_mode='double')

    gender_query_adjusted1 = abs_percentages1 * renormalizer1
    gender_query_adjusted2 = abs_percentages2 * renormalizer2

    gender_comparison = pd.DataFrame(data={search_term1: gender_specific_query1.values, search_term2: gender_specific_query2.values},
                                     index=gender_specific_query1.index).T
    gender_comparison_adjusted = pd.DataFrame(
        data={search_term1: gender_query_adjusted1.values, search_term2: gender_query_adjusted2.values},
        index=gender_specific_query1.index).T

    del gender_comparison.index.name
    chi2, pvalue, dof, expected = chi2_contingency(gender_comparison)
    gender_stats_level = bisect(P_LEVELS, pvalue)

    if gender_stats_level == len(P_LEVELS):
        gender_stats_msg = "Gender difference is <em>not</em> statistically significant (Chi-squared contingency test with p > %.4f)" % (
            P_LEVELS[-1])
    else:
        gender_stats_msg = "Gender difference is statistically significant at p < %s (p = %.4f with Chi-squared contingency test)" % (
            P_LEVELS[gender_stats_level], pvalue)

    J = pd.DataFrame(gender_comparison_adjusted.unstack())
    L = pd.DataFrame(data={'variable': [J.index.levels[1][x] for x in J.index.labels[1]],
                           'gender': [J.index.levels[0][x] for x in J.index.labels[0]],
                           'count': J.values.T[0].tolist()})

    gender_plot = Bar(L,
                      ylabel="percentage",
                      group='gender',
                      label='variable',
                      values='count',
                      title="Distribution by gender",
                      logo=None,
                      toolbar_location="below",
                      # width=600,
                      # height=400,
                      legend='top_right',
                      color=['blue', 'green'],
                      webgl=False)

    #######
    # AGE #
    #######
    age_specific_query1 = specific_query1.groupby('age').num_docs.sum()
    age_specific_query1 = sort_and_filter_age(age_specific_query1)
    age_specific_query_norm1 = age_specific_query1 / age_specific_query1.sum()
    age_specific_query2 = specific_query2.groupby('age').num_docs.sum()
    age_specific_query2 = sort_and_filter_age(age_specific_query2)
    age_specific_query_norm2 = age_specific_query2 / age_specific_query2.sum()

    compare_age_df = pd.DataFrame({'background distribution': age_totals_norm,
                                   'first term': pd.rolling_mean(age_specific_query_norm1, ROLLING_MEAN_FRAME),
                                   'second term': pd.rolling_mean(age_specific_query_norm2, ROLLING_MEAN_FRAME)
                                   })

    r, pvalue = spearmanr(compare_age_df['first term'], compare_age_df['second term'])
    age_stats_level = bisect(P_LEVELS, pvalue)

    if age_stats_level == len(P_LEVELS):
        age_stats_msg = "Age difference is <em>not</em> statistically significant (p > %s)" % (P_LEVELS[-1])
    else:
        age_stats_msg = "Age difference is <em>statistically significant</em> at p < %s (p = %s)" % (
            P_LEVELS[age_stats_level], pvalue)

    compare_age_df['i'] = compare_age_df.index
    age_plot = Line(compare_age_df,
                    x='i',
                    title="Age distribution",
                    ylabel="percentage",
                    xlabel='age',
                    logo=None,
                    toolbar_location="below",
                    legend='top_right',
                    color=['silver', 'blue', 'green'],
                    # width=1000,
                    # height=400,
                    webgl=False)

    ########
    # NUTS #
    ########
    # TODO: what about missing regions?
    nuts_specific_query1 = specific_query1.groupby('nuts_3').num_docs.sum()
    nuts_specific_query2 = specific_query2.groupby('nuts_3').num_docs.sum()
    nuts_query_norm1 = nuts_specific_query1 / nuts_specific_query1.sum()
    nuts_query_norm2 = nuts_specific_query2 / nuts_specific_query2.sum()

    regions = list(sorted(set(nuts_specific_query1.index).union(set(nuts_specific_query2.index))))
    nutsdiff = pd.DataFrame(0, index=regions, columns=arange(1))
    nutsdiff[0] = nuts_query_norm1 - nuts_query_norm2
    nutsdiff['G2'] = abs(nutsdiff[0]) > nutsdiff[0].abs().mean()

    outliers = sorted([x for x in regions if nutsdiff['G2'].ix[x].any() == True])
    is_it_term2 = nutsdiff[0].ix[outliers] < 0
    outliers1 = ', '.join(
        sorted(['%s (%s)' % (NUTS_NAMES[x], x) for x in is_it_term2.index if is_it_term2[x] == False]))
    outliers2 = ', '.join(sorted(['%s (%s)' % (NUTS_NAMES[x], x) for x in is_it_term2.index if is_it_term2[x] == True]))

    outlier_description = []
    if outliers1:
        outlier_description.append(
            '<em>%s</em> is more prevalent than <em>%s</em> in regions %s' % (search_term1, search_term2, outliers1))
    if outliers2:
        if outlier_description:
            outlier_description.append(', while <br />')
        outlier_description.append(
            '<em>%s</em> is more prevalent than <em>%s</em> in regions %s' % (search_term2, search_term1, outliers2))
    outlier_description = ''.join(outlier_description)

    bokeh_script, (gender_plot_div, age_plot_div) = components((gender_plot, age_plot))

    return flask.render_template('comparison_term_results.html',
                                 query1=search_term1,
                                 query2=search_term2,
                                 matches=matches,
                                 gender_comparison=gender_comparison.to_html(justify='right'),
                                 gender_stats_msg=gender_stats_msg,
                                 bokeh_script=bokeh_script,
                                 gender_plot=gender_plot_div,
                                 age_plot=age_plot_div,
                                 country_code=country_var,
                                 outlier_description=outlier_description,
                                 gender_total1=gender_specific_query1.sum(),
                                 gender_total2=gender_specific_query2.sum(),
                                 age_total1=age_specific_query1.sum(),
                                 age_total2=age_specific_query2.sum(),
                                 # age_total_M=age_specific_male_totals,
                                 # age_total_F=age_specific_female_totals,
                                 nuts_total1=nuts_specific_query1.sum(),
                                 nuts_total2=nuts_specific_query2.sum(),
                                 available_options=AVAILABLE_OPTIONS
                                 )


# def compound_bucket_to_series(count_dict_list, compound_field):
#     """
#     convert compound fields to pd.DataFrame
#     :param count_dict_list:
#     :param compound_field:
#     :return:
#     """
#     field_parts = compound_field.split("_and_")
#
#     rows = []
#     for count_dict in count_dict_list:
#         value_parts = count_dict["val"].split(":")
#         row = {"count": count_dict["count"]}
#         for field, value in zip(field_parts, value_parts):
#             if field == 'age':
#                 try:
#                     row[field] = int(value)
#                 except ValueError:
#                     row[field] = -1
#             else:
#                 row[field] = value
#
#         rows.append(row)
#
#     return pd.DataFrame(rows)
#
#
# def buckets_to_series(bucket_dict):
#     """
#     Converts a a list of buckets to a pd.Series.
#     Buckets are given as a list of JSON dicts, following the Solr buckets format.
#     """
#     return pd.DataFrame(bucket_dict).set_index('val')['count']
#
#
# def single_term_to_JSON(search_term, country_code, language_code):
#     """
#     search for a single term in a country and language
#     """
#     json_query = {
#         "query": "body_text_ws:{}".format(search_term),
#         "facet": {
#             "genders": {
#                 "type": "terms",
#                 "field": "gender_s",
#                 "facet": {
#                     "mean_age": "min(age_i)"
#                 }
#             },
#             "ages": {
#                 "start": MIN_AGE,
#                 "end": MAX_AGE,
#                 "type": "range",
#                 "field": "age_i",
#                 "gap": 1
#
#             },
#             "nuts_3_regions": {
#                 "type": "terms",
#                 "field": "nuts_3_s",
#                 "limit": -1
#             },
#             "gender_and_age": {
#                 "type": "terms",
#                 "field": "gender_and_age_s",
#                 "limit": -1
#             },
#             "mean_age": "avg(age_i)",
#             "percentiles_age": "percentile(age_i, 25, 50, 75)"
#         },
#         "filter": ["country_s:{}".format(country_code),
#                    "langid_s:{}".format(language_code)
#                    ],
#
#         "limit": 2
#     }
#
#     resp = requests.post(SOLR_QUERY_URL, json=json_query)
#     if not resp.ok:
#         print("Request failed: " + resp.text)
#         resp.raise_for_status()
#     return resp.json()


if __name__ == '__main__':
    app.run(debug=True)
