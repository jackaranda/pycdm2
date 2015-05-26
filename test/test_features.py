import sys
sys.path.append('../')
import pycdm


ds = pycdm.open('data/south_africa_2006-2012.95pct.tasmax.nc')
print ds
field = pycdm.Field(ds.root.variables['tasmax'])
print field.coordinates_mapping
print field.realtimes

geojson = field.asJSON()

#print geojson

with open('test_features.json', 'w') as outfile:
	outfile.write(geojson)
