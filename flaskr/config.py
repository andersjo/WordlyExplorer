SOLR_URL = "http://localhost:8983/solr/humboldt"
SOLR_SELECT_URL = SOLR_URL + "/select?wt=json"
SOLR_QUERY_URL = SOLR_URL + "/query"

# list of language code, country code, language name, and country name
AVAILABLE_OPTIONS = [('da', 'dk', 'Danish', 'Denmark'), ('en', 'Uk', 'English', 'UK')]

# map info: latitude, longitude, zoom level
MAP_VIEWS = {
    'uk': ([54.5, -4], 5),
    'dk': ([56, 10.5], 6),
    }