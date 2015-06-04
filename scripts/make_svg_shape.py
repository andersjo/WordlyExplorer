from kartograph import Kartograph
from shapefile import *
from collections import defaultdict

sf = Reader("../data/NUTS_RG_03M_2010.shp")

country = defaultdict(list)

for record in sf.records():
    if record[0] == 3:
        country[record[1][:2]].append(record[1])

def create_map(cc):
    cfg = {
        "layers": {
            "nutsregions": {
                "src": "../data/NUTS_RG_03M_2010.shp",
                "attributes": "all",
                "filter": {
                    "NUTS_ID": country[cc]
                }
            }
        },
        "proj": {
            "id": "satellite",
            "lon0": "auto",
            "lat0": "auto"
        }
    }

    K = Kartograph()
    K.generate(cfg, outfile=cc+'.svg')

for c in country:
    print country[c]

for c in country:
    print 'Creating map for:', c
    if c != 'FR':
        create_map(c)
