from shapefile import *

sf = Reader("../data/NUTS_RG_03M_2010.shp")

for shape in sf.records():
    print shape

for field in sf.fields:
    print field
