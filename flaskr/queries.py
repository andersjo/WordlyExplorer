import requests
import pandas as pd
import numpy as np
from sys import stderr
from config import SOLR_QUERY_URL
from config import MIN_AGE, MAX_AGE

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

def simple_query_totals(user_query=None):
    compound_field = "nuts_3_and_gender_and_age"

    json_query = {
        "query": "*:*",
        "limit": 0,
        "facet": {
            compound_field: terms_facet(compound_field+"_s"),
        }
    }

    if user_query:
        json_query.update(user_query)


    resp = perform_query(json_query)
    print("Query took ", resp['responseHeader']['QTime'])
    count_dict_list = resp["facets"][compound_field]["buckets"]

    field_parts = compound_field.split("_and_")

    rows = []
    for count_dict in count_dict_list:
        value_parts = count_dict["val"].split(":")
        row = {"num_docs": count_dict["count"]}
        for field, value in zip(field_parts, value_parts):
            row[field] = value
        rows.append(row)

    D = pd.DataFrame(rows)

    # Sanity check. Verify that the totals match the total number of reviews in the DB.
    assert D['num_docs'].sum() == resp['response']['numFound'], \
        "Sum of counts must match total number of reviews in DB"

    # Convert age to a integer field

    # Convert missing values to native format
    D = D.replace("NA", np.nan)

    D.age_num = D.age.astype(float)
    D['country_code'] = D.nuts_3.str.slice(0, 2).str.lower()

    return D

def sort_and_filter_age(age_df):
    age_df.index = age_df.index.astype(int)
    ages_index = [age for age in sorted(age_df.index)
                  if age >= MIN_AGE and age <= MAX_AGE]
    return age_df.ix[ages_index]


def prepare_age_and_gender(df):
    age_gender_df = df.groupby(['age', 'gender']).num_docs.sum()
    age_gender_df = age_gender_df.unstack('gender')
    age_gender_df = sort_and_filter_age(age_gender_df)

    # Normalize
    return (age_gender_df / age_gender_df.sum())

if __name__ == '__main__':
    totals = simple_query_totals()
    # print(totals)
    # fields
    # age   count gender nuts_3 country_code
    print(totals[(totals['gender'] == 'M') & (totals['country_code'] == 'uk')]['num_docs'].sum())