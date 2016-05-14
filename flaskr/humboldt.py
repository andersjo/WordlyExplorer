"""
This is the central file, generating the homepage
"""
import json

import flask
from flask import request

# Create the application.
import requests
from werkzeug.debug import DebuggedApplication

HUMBOLDT_APP = flask.Flask(__name__)

# TODO move to separate file
SOLR_URL = "http://localhost:8983/solr/humboldt"
SOLR_SELECT_URL = SOLR_URL + "/select?wt=json"
SOLR_QUERY_URL = SOLR_URL + "/query"


# Create connection to solr database
# s = solr.SolrConnection(SOLR_URL)

@HUMBOLDT_APP.route('/search', methods=['GET', 'POST'])
def index():
    """
    Displays the index page accessible at '/'
    """
    if request.method == 'POST':
        # print(request.form['query'])
        # result = request.form['query']
        search_terms = request.form["singleTermQuery"]

        json_results = search_single_term(search_terms, "missing", "missing")


        print(request.json)
        return flask.render_template('single_term.html',
                                     query=request.form["singleTermQuery"],
                                     jsonResults=json.dumps(json_results, indent=True)
                                     )
    else:
        return flask.render_template('single_term.html')





def search_single_term(search_term, country, language):
    """
    search for a single term in a country and language
    :param search_term:
    :param country:
    :param language:
    :return:
    """
    json_query = {
        "query": "body_text_ws:{}".format(search_term),
        # "facet.field": ["nuts_2_s", "country_s", "langid_s"],
        # "facet": "on",
        "limit": 0
    }

    resp = requests.post(SOLR_QUERY_URL, json=json_query)
    print("Making query", json_query)
    resp.raise_for_status()
    return resp.json()


if __name__ == '__main__':
    HUMBOLDT_APP.run(debug=True)
    # DebuggedApplication(HUMBOLDT_APP, evalex=True)
    # .run(debug=True)




# TODO: include queries
