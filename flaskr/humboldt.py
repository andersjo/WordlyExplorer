"""
This is the central file, generating the homepage
"""
import flask

# Create the application.
APP = flask.Flask(__name__)
SOLR_URL = "http://localhost:8983/solr/humboldt"


# Create connection to solr database
# s = solr.SolrConnection(SOLR_URL)

@APP.route('/')
def index():
    """
    Displays the index page accessible at '/'
    """
    # TODO: integrate layout
    return flask.render_template('humboldt.html', queries=[])


def single_query(search_term, country, language):
    q = "facet.field=gender_s\
    &facet.field=nuts_2_s\
    &facet.field=country_s\
    &facet.field=langid_s\
    &facet=on\
    &indent=on\
    &q=body_text_ws:%s\
    &rows=0\
    &start=0\
    &wt=json" % (search_term)


if __name__ == '__main__':
    APP.debug = True
    APP.run()




# TODO: include queries
