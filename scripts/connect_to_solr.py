import requests
import json

SOLR_URL = "http://localhost:8983/solr/humboldt"
SOLR_UPDATE_URL = SOLR_URL + "/update"
SOLR_SELECT_URL = SOLR_URL + "/select?wt=json"

resp = requests.post(SOLR_SELECT_URL, json={
  "query": "memory",
  "filter": "inStock_b:true"
})

print(resp)
print(json.dumps(resp.json(), indent=True))


print()



