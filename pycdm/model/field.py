"""
Implements the Field class
"""
import numpy
import calendar
import datetime
import json

import netCDF4

from dimension import Dimension
from error import CDMError

from ..timefunctions import time_slices, time_aggregation

cf_dimensions = {'degree_east': 'longitude',
'degree east': 'longitude',
'degrees_east': 'longitude',
'degree_north': 'latitude',
'degrees_north': 'latitude',
'degree north': 'latitude'}

def cf_units2coordinates(units):
	
	# For spatial coordinates
	if units in cf_dimensions:
		return cf_dimensions[units]
	
	# Time coordinates
	try:
		netCDF4.num2date(0,units)
	except:
		return None
	
	return 'time'
	

class Field(object):
	"""
	The Field class encapsulates a Variable instance along with its coordinate system
	mapping.  Coordinate system mapping at the moment is based on teh COORDS/CF 
	conventions
	"""
	
	def __init__(self, variable):
		"""
		Initialise an instance using an existing variable
		
		The Variable instance needs to be part of a Group instance in order to gain access
		to other related variables and dimensions that are required for the coordinates
		mapping
		
		A Field can actually have multiple variables associated with it.  While it is 
		initialised with a single variable, new variables can be added.  When a variable
		is added it is checked to make sure that the coordinates mapping is identical.
		"""
		#print 'generating field for ', variable, variable.dimensions
		self.variables = [variable]
		
		self.coordinates_variables = []
		self.coordinates_mapping = {}
		
		# Cache features
		self._features = None
		
		# We need to keep track of which dimensions we can map
		mapped = []
		
		# First lets check for standard 1D coordinate variables.  These are variables
		# that have the same name as one of the variables dimensions or 1D variables
		# sharing a dimension with the variable 
		#print self.variables[0].group.variables.keys()
		for di in range (0,len(self.variables[0].dimensions)):

			dimension = self.variables[0].dimensions[di]
			#print "Field.__init__  looking at dimension ", dimension

			if isinstance(dimension, Dimension):
				dim_name = dimension.name
			else:
				dim_name = dimension
			

			#print "Field.__init__  searching for coordinate variable: ", self.variables[0].group.variables.keys()
			# Find variables with same name as the dimension
			if dim_name in self.variables[0].group.variables.keys():

				coord_variable = self.variables[0].group.variables[dim_name]
				self.coordinates_variables.append(coord_variable)
				mapped.append(dim_name)
				
				# See if we can use the units to find out what spatial/temporal variable this is from 
				# the CF conventions
				coordinate_name = cf_units2coordinates(coord_variable.get_attribute('units'))
				
				# If we can't we just default to the dimension name
				if not coordinate_name:
					coordinate_name = dim_name
				
				self.coordinates_mapping[coordinate_name] = {'variable':dim_name, 'map':[di]}
			
			# If previous failed then try find 1D "loose" coordinate variables
			#else:
			#	for name, variable in self.variables[0].group.variables.items():
			#		#print 'checking ', variable
			#		# Must be 1D
			#		if len(variable.dimensions) == 1:
			#			
			#			# Must use the same dimension
			#			if (dim_name in variable.dimensions):
			#				self.coordinates_variables.append(variable)
			#				mapped.append(dim_name)
			#				
			#				# See if we can use the units to find out what spatial/temporal variable this is from 
			#				# the CF conventions
			#				coordinate_name = cf_units2coordinates(variable.get_attribute('units'))
			#
			#				# If we can't we just default to the dimension name
			#				if not coordinate_name:
			#					coordinate_name = dim_name
			#	
			#				self.coordinates_mapping[coordinate_name] = {'variable':dim_name, 'map':[di]}
			
				
		# Next lets see if we have a coordinates attribute we can use (CF1.6 convention)
		if self.variables[0].get_attribute('coordinates'):
			
			self.coordinates_names = self.variables[0].get_attribute('coordinates').split()
						
			# Find each associated variable
			for name in self.coordinates_names:
				
				if name in self.variables[0].group.variables.keys():
					
					coord_variable = self.variables[0].group.variables[name]
					self.coordinates_variables.append(coord_variable)

					#print 'got coordinate variable ', coord_variable, coord_variable.dimensions
					# See if we can find out what spatial/temporal variable this is
					try:
						coordinate_name = cf_dimensions[self.variables[0].group.variables[name].get_attribute('units')]
					except:
						coordinate_name = name

					# Create the coordinates_mapping entry but with an empty dimensions map for now
					self.coordinates_mapping[coordinate_name] = {'variable':name, 'map':[], 'coordinates': self.coordinates_names}
						
					# Add each coordinates variable dimension to the mappable list and generate the map
					#print 'generating dimensions map for ', coord_variable.dimensions
					for dimension in coord_variable.dimensions:
						#print dimension, coord_variable.dimensions
						self.coordinates_mapping[coordinate_name]['map'].append(self.variables[0].dimensions.index(dimension))
						if not dimension in mapped:
							mapped.append(dimension)
							
		# Setup shortcut to identify time coordinate variable
		try:
			self.time_variable = self.variables[0].group.variables[self.coordinates_mapping['time']['variable']]
		except:
			self.time_variable = None
			
		# Shortcuts for latitude and longitude coordinate variables
		try:
			self.latitude_variable = self.variables[0].group.variables[self.coordinates_mapping['latitude']['variable']]
		except:
			self.latitude_variable = None

		try:
			self.longitude_variable = self.variables[0].group.variables[self.coordinates_mapping['longitude']['variable']]
		except:
			self.longitude_variable = None
			
		
	def add_variable(self, variable):
		"""
		Add a variable to this field.  This requires that the coordinates_mapping of 
		the new variable is exactly the same as the coordinates mapping of this field.
		"""
		
		new_field = Field(variable)
		
		if new_field.coordinates_mapping == self.coordinates_mapping:
			self.variables.append(variable)
			return True
		else:
			return False
		
		
	@property
	def shape(self):
		return self.variables[0].shape
		
	@property
	def featuretype(self):
		"""
		Returns the type of features represented by this variable.  Can be one of:
		
		Point: Values defined at discrete points for a single time
		PointSeries: Values defined at discrete points over a number of time steps
		Grid:  Values defined on a rectangular grid for a single time (may also include multiple vertical levels) 
		GridSeries: Values define on a rectangular grid over a number of time steps (may also include multiple vertical levels)
		"""

		# If we have a time coordinate system then we have a Series
		if self.coordinates_mapping.has_key('time'):
			series_string = 'Series'
		else:
			series_string = ''


		# We need latitude and longitude mappings as a starting point
		if self.coordinates_mapping.has_key('latitude') and self.coordinates_mapping.has_key('longitude'):
			
			lat_map = self.coordinates_mapping['latitude']
			lon_map = self.coordinates_mapping['longitude']
		
			# For Point and Cartesian grid features latitude and longitude corodinate variables must be 1D
			if len(lat_map['map']) == 1 and len(lon_map['map']) == 1:
				
				# For Point features lat/lon must be accessed through the coordinates attribute
				if lat_map.has_key('coordinates') and lon_map.has_key('coordinates'):				
					return 'Point%s' % (series_string)
				
				# else we have a cartesian grid
				else:
					return 'Grid%s' % (series_string)
							
			# For non cartesian grids we need at least a 2D latitude and longitude coordinate variables
			if len(lat_map['map']) >= 2 and len(lon_map['map']) >= 2:
				return 'Grid%s' % (series_string)
				
		# If we don't have latitude and longitude mappings then we are stuck
		else:
			return None
			
	def latlons(self):
		"""
		Returns a 2D numpy array of latitudes.  If the latitude coordinate variable is 1D then 
		it is extended to 2D.
		"""
		
		# First check we have a grid feature type
		if self.featuretype in ['Grid', 'GridSeries']:
			
			latvar = self.latitude_variable
			lonvar = self.longitude_variable
			
			# Then check if latitude and longitude variables are 1D
			if len(latvar.shape) == 1 and len(lonvar.shape) == 1:
				latvar_2d = latvar[:].reshape((-1,1)).repeat(lonvar.shape[0], axis=1)
				lonvar_2d = lonvar[:].reshape((-1,1)).transpose().repeat(latvar.shape[0], axis=0)
				return (latvar_2d, lonvar_2d)
			
			# for 2D variables its easy, just return the variable data
			elif len(latvar.shape) >= 2 and len(lonvar.shape) >= 2:
				
				# Handle the WRF case where lat/lon variables are 3D with time as first dimension
				if len(latvar.shape) == 3 and len(lonvar.shape) == 3:
					return (latvar[0,:], lonvar[0,:])
				else:
					return (latvar[:], lonvar[:])
			
			# otherwise, we can't do it!
			else:
				return (None, None)
		
		elif self.featuretype == 'PointSeries':
			return (self.latitude_variable[:], self.longitude_variable[:])
	
	@property
	def latitudes(self):
		return self.latlons()[0]
		
	@property
	def longitudes(self):
		return self.latlons()[1]
		
	def coordinates(self, indices):
		"""
		Map dimension indices to coordinate variable values
		"""
		
		# We expect a tuple
		if not type(indices) == tuple:
			indices = tuple((indices,))

		# Check we have the same number of indices in the argument as in the mapping
		#if len(indices) != len(self.coordinates_mapping):
		#	raise CDMError("Field is %d dimensional, %d indices provided" % (len(self.coordinates_mapping), len(indices)))

		coordinates = {}
		
		for coordinate in self.coordinates_mapping.keys():
			coordinate_variable = self.variables[0].group.variables[self.coordinates_mapping[coordinate]['variable']]
			coordinate_mapping = self.coordinates_mapping[coordinate]['map']
			

			slice_list = []
			failed = False
			for index in coordinate_mapping:
				
				# Skip an None indices
				if indices[index] == None:
					failed = True
					break
					
				slice_list.append(slice(indices[index], indices[index]+1))
			
			# Only get coordinates where we had valid indices
			if not failed:
				coordinates[coordinate] = (coordinate_variable[slice_list].flatten()[0], coordinate_variable.get_attribute('units'))

		# Try and convert time coordinates to real datetimes
		for name, coordinate in coordinates.items():

			if name == 'time':
				try:
					date = netCDF4.num2date(*coordinate)
				except:
					pass
				else:
					coordinates[name] = (date,'')	
		
		return coordinates
		
	def reversemap(self, method='nearest', min_distance=1e50, **kwargs):
		"""
		Reverse mapping involves determining the data array indices associated with the coordinates provided.  Clearly there is 
		not always a direct mapping as data is defined at discrete positions with the coordinate space.  Various methods could be 
		implemented to determine the indices.  Finding the nearest indices is probably the most commong.  Returning bounding indices
		with distance weights would also be useful.  For some coordinate spaces exact matches are required (eg. station names) but most
		likely these are only for string based coordinates.
		
		Nearest match is done by building up an n-dimensional distance(squared) array and then searching for indices of the minimum.  This
		generalises nicely from 1 to n dimensions.
		
		The index returned is either an integer in the range of the dimension length, numpy.nan if there was no coordinate constraint(s)
		available for the dimension.  What currently isn't checked is is whether the target coordinate value is within the bounds of the
		coordinate space because its not clear how to define those bounds generically. One possibility is to allow a min_distance parameter
		to be passed and so avoid figuring out what this should be.  But min_distance could depend on which coordinate variable you are
		searching.  We could allow coordinate target values to be tuples consisting of a target value and a minimum distance?
		
		However we end up doing this, a return value of -1 is expected for out of bounds responses.
		
		For string based coordinate variables, a -1 should be returned if no string match was found.
				
		
		>>> import pyCDM.handlers.netcdf4 as netcdf4
		>>> import pyCDM.handlers.csag2 as csag2
		
		>>> ds = netcdf4.netCDF4Dataset('testdata/gfs.nc')
		>>> tmax = ds.root.variables['TMAX_2maboveground']
		>>> tmax_field = Field(tmax)
		>>> tmax_field.reversemap(time=1332892800.0, longitude=204.545196, latitude=0.3, method='nearest')
		[0, 441, 1000]
		
		>>> ds = netcdf4.netCDF4Dataset('testdata/wrfout_d01_2010-05-28_12.nc')
		>>> q2 = ds.root.variables['Q2']
		>>> q2_field = Field(q2)
		>>> q2_field.reversemap(latitude=-30.89, longitude=22.115)
		[nan, 45, 60]

		>>> ds = netcdf4.netCDF4Dataset('testdata/pr_AFR-44_CCCMA-CanESM2_historical_r1i1p1_SMHI-RCA4_v0_mon_200101_200512.nc')
		>>> pr = ds.root.variables['pr']
		>>> pr_field = Field(pr)
		>>> pr_field.reversemap(latitude=-23.7599999, longitude=-2.640000, time=19282)
		[20, 50, 50]
		>>> pr_field.reversemap(latitude=-23.7599999, longitude=-2.640000)
		[nan, 50, 50]
		>>> pr_field.reversemap(latitude=-23.7599999, time=19282)
		[20, nan, nan]
		
		>>> ds = csag2.csag2Dataset('testdata/csag2/ghcnd.2.afr/ppt')
		>>> ppt = ds.root.variables['PPT']
		>>> ppt_field = Field(ppt)		
		>>> ppt_field.reversemap(latitude=-27.5, longitude=22.6299)
		[1062, nan]
		>>> ppt_field.reversemap(latitude=-27.5)
		[1059, nan]
		>>> ppt_field.reversemap(time=5001)
		[nan, 5000]
		
		"""
		
		restricted = ['min_distance', 'method']
		indices = []
		
		# remove restricted arguments
		kwargs_filtered = {key: value for key, value in kwargs.items() if value not in restricted}
		
		# We need to find each dimension index in order
		for dim_index in range(len(self.variables[0].dimensions)):
			
			#print "indices: ", indices
			#print "dim_index: ", dim_index
			
			# Find all coordinate mapping keys that relate to this index
			map_keys = []
			fail = False
			for map_key in self.coordinates_mapping:
								
				# Check if the index is in this map and we have a constraint argument for the variable
				if dim_index in self.coordinates_mapping[map_key]['map'] and map_key in kwargs_filtered:
					
					# All the maps should be identical so lets keep a copy for later
					mapping = self.coordinates_mapping[map_key]['map']
					map_keys.append(map_key)

					#print "mapping: ", mapping
									
			# If we have no map_keys then we have to abort
			if not map_keys:
				indices.append(numpy.nan)
				continue
			
			#print 'map_keys: ', map_keys			
			#print 'reversemap: map_keys(dim_index=%d) = ' % (dim_index), map_keys
					
			# Check all the coordinate variables are the same shape!
			first = True
			shape = None
			for map_key in map_keys:
				coord_variable = self.variables[0].group.variables[self.coordinates_mapping[map_key]['variable']]
				#print coord_variable.shape
				if first:
					shape = coord_variable.shape
				else:
					if coord_variable.shape() != shape:
						raise CDMError("Linked coordinate variables must all be the same shape")
						
			# We need at least as many map keys as the dimensionality of the coordinate variables
			if len(map_keys) < len(shape):
				indices.append(numpy.nan)
				continue
	
			# Now we search the coordinate space for the closest feature
			# Find the associated coordinate variables			
			coordinate_variables = []
			for key in map_keys:
			#	print "adding coordinate variable: ", self.variables[0].group.variables[self.coordinates_mapping[key]['variable']]
				coordinate_variables.append(self.variables[0].group.variables[self.coordinates_mapping[key]['variable']])
				
			#print 'reversemap: coordinate_variables(dim_index=%d) = ' % (dim_index), coordinate_variables
			
			# Get the target arguments for each coordinate variable
			try:
				target_args = [kwargs_filtered[key] for key in map_keys]
			except:
				indices.append(numpy.nan)
				continue
				
			# See if we can coerce target arguments to floats, otherwise assume they are strings...
			targets = []
			#print "target_args: ", target_args
			for arg in target_args:
								
				# Check if we have a datetime argument, convert to dataset time coordinate
				if type(arg) == datetime.datetime:
					try:
						timevar = self.variables[0].group.variables[self.coordinates_mapping['time']['variable']]
						timeunits = timevar.get_attribute('units')
						calendar = timevar.get_attribute('calendar')
						if not calendar:
							calendar = 'standard'
						target = netCDF4.date2num(arg, timeunits, calendar=calendar)
					except:
						raise CDMError("Cannot coerce datetime argument into time value")
				
				else:
					try:
						target = numpy.float32(arg)
					except:
						target = "%s" % (repr(arg))
					
				# Check target type agrees with coordinate variables
				#for coordinate_variable in coordinate_variables:
				#	if type(target) != coordinate_variable.dtype:
				#		raise CDMError("Mismatched target type %s and coordinate variable type %s" % (type(target),coordinate_variable.dtype) )
						
				targets.append(target)
			
			# For float targets and coordinate variables
			#print "targets: ", targets
			for target in targets:
				if type(target) == numpy.float32 or type(target) == float:
					# Intialiase our distance array
					d2 = numpy.zeros(shape)					
					for k in range(0,len(map_keys)):
						d2 += numpy.power(coordinate_variables[k][:] - targets[k], 2)
											
			closest = numpy.unravel_index(d2.argmin(),shape)
			indices.append(closest[mapping.index(dim_index)])
		
			#print "indices: ", indices
		
		# Convert to slices
		slice_list = []
		for index in indices:
			if numpy.isnan(index):
				slice_list.append(slice(None))
			else:
				slice_list.append(slice(index,index+1))
		
		return tuple(slice_list)
		
	@property
	def time_dim(self):
		return self.coordinates_mapping['time']['map'][0]

	@property
	def times(self):
		
		if self.time_variable:
			return self.time_variable[:]
		else:
			return []
			
	@property
	def realtimes(self):
		
		if self.time_variable:
			return netCDF4.num2date(self.time_variable[:], self.time_variable.get_attribute('units'))
			
	def time_slices(self, start={}, length='1 month'):
		
		return time_slices(self.times, self.time_variable.get_attribute('units'), start, length)
		
	def time_aggregation(self, func, start={}, length='1 month', mask_less=numpy.nan, mask_greater=numpy.nan):
		
		times = self.times
		slices = time_slices(times, self.time_variable.get_attribute('units'), start, length)
		
		shape = self.shape
		
		time_dim = self.coordinates_mapping['time']['map'][0]

		new_shape = list(shape)
		new_shape[time_dim] = len(slices)
		new_shape = tuple(new_shape)
		
		source = self.variables[0][:]
		result = numpy.ma.empty(new_shape, dtype=numpy.float32)

		result_selection = []
		source_selection = []
		for d in shape:
			source_selection.append(slice(None))
			result_selection.append(slice(None))
		
		for i in range(len(slices)):
			source_selection[time_dim] = slices[i]
			result_selection[time_dim] = i
			#print source_selection, result_selection
			#print self.variables[0][source_selection].shape
			
	#		tmp = numpy.ma.masked_array(self.variables[0][source_selection])
			tmp = source[source_selection]
			#print type(tmp)
			#print numpy.ma.min(tmp), numpy.ma.max(tmp)
			
			if not numpy.isnan(mask_less):
				tmp = numpy.ma.masked_less(tmp, mask_less)

			if not numpy.isnan(mask_greater):
				tmp = numpy.ma.masked_greater(tmp, mask_greater)
			
			
			result[tuple(result_selection)] = func(tmp, axis=time_dim)
			#print i, source[source_selection][:,77], result[tuple(result_selection)][77]

			
		result_times = [times[s.stop-1] for s in slices]

		return result, netCDF4.num2date(result_times, self.time_variable.get_attribute('units'))

	def features(self, mask=None, propnames=None):
		"""
		Produces a geoJSON structured dict that represents the feature collection of the field.  At the moment the following assumptions
		are made:
		Point type feature collections are represented as unconnected collections of points.
		Rectangular/cartesian grid feature collections are represented as a collection of rectangular polygons centered on the
		lat/lon location of a the grid point.
		Rectangular/non-cartesian grids are presented as rectangles centered on the lat/lon location.  Corners are interpolated from
		diagonal grid point locations and extrapolated on the edges.  This may not be perfect but is a good working start.
		
		The optional mask parameter specifies a masking field that needn't be congruent as the mask values will be extracted based on
		the nearest lat/lon search.
		
		The optional propnames parameter specifies a list of property labels that correspond to data values.  This allows multiple
		properties to be added to each feature if the field has other dimensions such as time.  Each property name corresponds to successive data values
		after the grid point data array has been flattened.
		"""
		
		# See if we have a cached result
		if self._features:
			return self._features
		
		result = {'type': 'FeatureCollection', 'features':[]}
		features = []
										
		# We can dealt with grid type collections first
		if self.featuretype in ['Grid', 'GridSeries']:
			
			# Get center point latitudes and longitudes
			latitudes = self.latitudes
			longitudes = self.longitudes
			shape = latitudes.shape
			
			# How do we slice the data to get grid point values?
			index = 0
			for dim_name in self.variables[0].dimensions:
				print dim_name
				dim = self.variables[0].group.get_dimension(dim_name)
				print dim
				if dim.length == shape[0]:
					y_index = index
				if dim.length == shape[1]:
					x_index = index
				if dim.length == len(self.times):
					t_index = index
				index += 1
			
			
			# Create the initial slices with indices defaulting to 0
			slices = [0]*len(self.variables[0].dimensions)
			slices[t_index] = slice(0,len(self.times))

						
			# Create corner point latitude longitude arrays
			corner_lats = numpy.zeros((shape[0]+1, shape[1]+1))
			corner_lons = numpy.zeros((shape[0]+1, shape[1]+1))
						
			# Step through all the interior grid points
			for y in range(1, shape[0]):
				for x in range(1, shape[1]):
					corner_lats[y,x] = (latitudes[y, x-1] + latitudes[y,x] + latitudes[y-1,x-1] + latitudes[y-1,x])/4
					corner_lons[y,x] = (longitudes[y, x-1] + longitudes[y,x] + longitudes[y-1,x-1] + longitudes[y-1,x])/4
					
			# Left boundary
			x = 0
			for y in range(1,shape[0]):
				tmp_lat = (latitudes[y,x] + latitudes[y-1,x])/2
				tmp_lon = (longitudes[y,x] + longitudes[y-1,x])/2
				corner_lats[y,x] = tmp_lat - (corner_lats[y,x+1] - tmp_lat)
				corner_lons[y,x] = tmp_lon - (corner_lons[y,x+1] - tmp_lon)


			# Right boundary
			x = shape[1]
			for y in range(1,shape[0]):
				tmp_lat = (latitudes[y,x-1] + latitudes[y-1,x-1])/2
				tmp_lon = (longitudes[y,x-1] + longitudes[y-1,x-1])/2
				corner_lats[y,x] = tmp_lat - (corner_lats[y,x-1] - tmp_lat)
				corner_lons[y,x] = tmp_lon - (corner_lons[y,x-1] - tmp_lon)


			# Bottom boundary
			y = 0
			for x in range(1,shape[1]):
				tmp_lat = (latitudes[y,x] + latitudes[y,x-1])/2
				tmp_lon = (longitudes[y,x] + longitudes[y,x-1])/2
				corner_lats[y,x] = tmp_lat - (corner_lats[y+1,x] - tmp_lat)
				corner_lons[y,x] = tmp_lon - (corner_lons[y+1,x] - tmp_lon)

			# Top boundary
			y = shape[0]
			for x in range(1,shape[1]):
				tmp_lat = (latitudes[y-1,x] + latitudes[y-1,x-1])/2
				tmp_lon = (longitudes[y-1,x] + longitudes[y-1,x-1])/2
				corner_lats[y,x] = tmp_lat - (corner_lats[y-1,x] - tmp_lat)
				corner_lons[y,x] = tmp_lon - (corner_lons[y-1,x] - tmp_lon)
			
			# Corners
			corner_lats[0,0] = latitudes[0,0] - (corner_lats[1,1] - latitudes[0,0])
			corner_lats[0,shape[1]] = latitudes[0,shape[1]-1] - (corner_lats[1,shape[1]-1] - latitudes[0,shape[1]-1])
			corner_lats[shape[0],0] = latitudes[shape[0]-1,0] + (latitudes[shape[0]-1,0] - corner_lats[shape[0]-1,1])
			corner_lats[shape[0],shape[1]] = latitudes[shape[0]-1,shape[1]-1] + (latitudes[shape[0]-1,shape[1]-1] - corner_lats[shape[0]-1,shape[1]-1])

			corner_lons[0,0] = longitudes[0,0] - (corner_lons[1,1] - longitudes[0,0])
			corner_lons[0,shape[1]] = longitudes[0,shape[1]-1] + (longitudes[0,shape[1]-1] - corner_lons[1,shape[1]-1])
			corner_lons[shape[0],0] = longitudes[shape[0]-1,0] - (corner_lons[shape[0]-1,1] - longitudes[shape[0]-1,0])
			corner_lons[shape[0],shape[1]] = longitudes[shape[0]-1,shape[1]-1] + (longitudes[shape[0]-1,shape[1]-1] - corner_lons[shape[0]-1,shape[1]-1])


#			print corner_lats

			# Now create all polygons
			for y in range(0, shape[0]):
				for x in range(0, shape[1]):
					
					# Configure the slices
					slices[x_index] = slice(x,x+1)
					slices[y_index] = slice(y,y+1)

					# Check if we are masking and if this point is masked
					masked = False

					if mask:
						if mask[y, x] < 0.5:
							masked = True
											
					if not masked:

						vertices = []
						vertices.append([corner_lons[y, x], corner_lats[y,x]])
						vertices.append([corner_lons[y+1, x], corner_lats[y+1,x]])
						vertices.append([corner_lons[y+1, x+1], corner_lats[y+1,x+1]])
						vertices.append([corner_lons[y, x+1], corner_lats[y,x+1]])
						vertices.append([corner_lons[y, x], corner_lats[y,x]])				

						# Create the basic feature
						feature = {'type': 'Feature', 'properties':{'id':x + y * shape[1]}, 'geometry': {'type': 'Polygon', 'coordinates': [vertices]}}
						
						# Now add the data					
						data = self.variables[0][slices].flatten()
						
						
						# If we have property names then extract data for each name
						if propnames:
							for name in propnames:
								
								feature['properties']['value'] = self.variables[0][slices].flatten()[1]
	#							print self.variables[0][slices]
								#feature['properties']['value'] = self.variables[0][slices].flatten()[propnames.index(name)]
						
						# else just set property 'value' to the first value of the flattened data array
						else:
								feature['properties']['value'] = float(self.variables[0][slices].flatten()[1])
						
						#print feature['properties']
						#, 'value':float(values[y,x])
						features.append(feature)
					
			result['features'] = features
						
#			outfile = open('test.json', 'w')
#			outfile.write(simplejson.dumps(result))
#			outfile.close()
			
		
		# Point type feature sets next
		elif self.featuretype in ['Point', 'PointSeries']:
			
			result = {'type': 'FeatureCollection', 'features':[]}
			features = []
			
			longitudes = self.longitudes
			latitudes = self.latitudes
			
			count = len(longitudes)
			for fid in range(0,count):
				feature = {'type':'Feature', 'properties':{'_id':fid}, 'geometry': {'type':'Point', 'coordinates': [float(longitudes[fid]), float(latitudes[fid])]}}

				# Add related variables to properties
				for key in self.coordinates_mapping:
					if key in self.variables[0].group.variables and key not in ['latitude', 'longitude']:
						if self.coordinates_mapping[key]['map'] == self.coordinates_mapping['latitude']['map']:
							feature['properties'][key] = self.variables[0].group.variables[key][fid]
							
				features.append(feature)
				
			result['features'] = features

			
		else:
			return None

		# Cache result
		if not self._features:
			self._features = result
			
		return result


	def asJSON(self):
		print self.features()
		return json.dumps(self.features())

	
