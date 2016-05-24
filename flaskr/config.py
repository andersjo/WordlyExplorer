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

# list of language code, country code, language name, and country name
AVAILABLE_OPTIONS = [('da', 'dk', 'Danish', 'Denmark'), ('en', 'uk', 'English', 'UK')]#, ('fr', 'fr', 'French', 'France')]

# map info: latitude, longitude, zoom level
MAP_VIEWS = {
    'uk': ([54.5, -4], 5),
    'dk': ([56, 10.5], 6),
    }

NOT_AVAIL = "NA"

def terms_facet(name, **kwargs):
    facet = {"type": "terms",
             "field": name,
             "limit": -1}

    if len(kwargs):
        facet["facet"] = kwargs

    return facet

def age_facet():
    return {"type": "range",
            "field": "age_i",
            "start": MIN_AGE,
            "end": MAX_AGE,
            "gap": 1}

def perform_query(json_query):
    resp = requests.post(SOLR_QUERY_URL, json=json_query)
    if not resp.ok:
        print("Request failed: " + resp.text, file=stderr)
        resp.raise_for_status()
    return resp.json()

def query_totals():
    json_query = {
        "query": "*:*",
        "limit": 0,
        "facet": {
            "nuts_1": terms_facet("nuts_1_s"),
            "nuts_2": terms_facet("nuts_2_s"),
            "nuts_3": terms_facet("nuts_3_s",
                                  langid=terms_facet("langid_s"),
                                  gender=terms_facet("gender_s"),
                                  age=terms_facet("age_s")
                                  ),
            "country": terms_facet("country_s",
                                   langid=terms_facet("langid_s")),
            "gender": terms_facet("gender_s"),
            "age": terms_facet("age_s")
        }
    }

    resp = requests.post(SOLR_QUERY_URL, json=json_query)
    if not resp.ok:
        print("Request failed: " + resp.text)
        resp.raise_for_status()
    return resp.json()

def simple_query_totals():
    compound_field = "nuts_3_and_gender_and_age"

    json_query = {
        "query": "*:*",
        "limit": 0,
        "facet": {
            compound_field: terms_facet(compound_field+"_s"),
        }
    }

    resp = perform_query(json_query)
    count_dict_list = resp["facets"][compound_field]["buckets"]

    field_parts = compound_field.split("_and_")

    rows = []
    for count_dict in count_dict_list:
        value_parts = count_dict["val"].split(":")
        row = {"count": count_dict["count"]}
        for field, value in zip(field_parts, value_parts):
            row[field] = value
        rows.append(row)

    D = pd.DataFrame(rows)

    # Sanity check. Verify that the totals match the total number of reviews in the DB.
    assert D['count'].sum() == resp['response']['numFound'], \
        "Sum of counts must match total number of reviews in DB"

    # Convert age to a integer field

    # Convert missing values to native format
    D = D.replace("NA", np.nan)

    D.age_num = D.age.astype(float)
    D['country_code'] = D.nuts_3.str.slice(0, 2).str.lower()

    return D

TOTALS = simple_query_totals()