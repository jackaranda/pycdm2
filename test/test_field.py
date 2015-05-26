
import numpy as np

import sys
sys.path.append('../')
import pycdm

print pycdm.Dataset.__subclasses__()

#ds = pycdm.open('RegCM_4-3_SampleOutput.nc')
ds = pycdm.open('data/gfs.subset.nc')

print ds
#ds = pycdm.plugins.dataset.netcdf4.netCDF4Dataset(uri='RegCM_4-3_SampleOutput.nc')

print ds.root
print ds.root.dimensions

variable = ds.root.variables['PRATE_surface']
print variable, variable.dimensions


field = pycdm.Field(ds.root.variables['PRATE_surface'])

print field.coordinates_variables
#print
print field.coordinates_mapping
#print
#print field.featuretype
#print
print field.latitudes.shape
print field.longitudes.shape
print field.shape
print field.coordinates((0,0,0))

print field.realtimes

slices = field.reversemap(latitude=-34.5, longitude=18.5)
print slices
indices = tuple([s.start for s in slices])
print indices
print field.coordinates(indices)

print field.time_slices(start=[{'year':2012, 'hour':12}], length='1 day')
daysum, times = field.time_aggregation(np.sum, start=[{'year':2012, 'hour':12}], length='1 day')



