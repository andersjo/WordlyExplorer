import requests
import pandas as pd
import numpy as np
from sys import stderr
SOLR_URL = "http://localhost:8983/solr/humboldt"
SOLR_SELECT_URL = SOLR_URL + "/select?wt=json"
SOLR_QUERY_URL = SOLR_URL + "/query"

MIN_AGE = 16
MAX_AGE = 81
P_LEVELS = [0.01, 0.05, 0.1]
ROLLING_MEAN_FRAME = 2

# list of language code, country code, language name, and country name
AVAILABLE_OPTIONS = [('da', 'dk', 'Danish', 'Denmark'), ('en', 'uk', 'English', 'UK')]#, ('fr', 'fr', 'French', 'France')]

# map info: latitude, longitude, zoom level
MAP_VIEWS = {
    'uk': ([54.5, -4], 5),
    'dk': ([56, 10.5], 6),
    }

NOT_AVAIL = "NA"
