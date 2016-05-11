# coding:utf-8
import argparse
import json
from itertools import islice
from pathlib import Path

import numpy as np
import requests

SOLR_URL = "http://localhost:8983/solr/humboldt"

def retrieve_field_types():
    r = requests.get(SOLR_URL + "/schema/fieldtypes")
    r.raise_for_status()
    response_doc = r.json()

    return {field_type['name']: field_type
            for field_type in response_doc['fieldTypes']}

field_types = retrieve_field_types()
print(json.dumps(field_types))

