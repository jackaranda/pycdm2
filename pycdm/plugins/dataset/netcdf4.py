"""
Implements the netCDF4 Variable and Dataset subclasses.  Draws strongly on the netCDF4
python module
"""

import copy
from collections import OrderedDict

import netCDF4
import numpy

from pycdm import Group
from pycdm import Variable
from pycdm import Field
from pycdm import Dataset
from pycdm import Dimension

		
class netCDF4Variable(Variable):
	"""
	A subclass of the CDM Variable class that implements netcdf4 variable access
	"""
	
	def __init__(self, name, group, **kwargs):
		"""
		Creates a new netCDF4Variable instance by creating a basic variable instance and adding in the netCDF4 varobj instance
		"""
		super(netCDF4Variable, self).__init__(name, group, **kwargs)
		self.data = group.dataset.ncfile.variables[name]
	
	def __getitem__(self, slice):
		"""
		Implements the get item array slicing method.  Delegates to the netCDF4 modules
		variable __getitem__ method.
		
		>>> ds = netCDF4Dataset(uri='test/data/RegCM_4-3_SampleOutput.nc')
		>>> print ds.root.variables['tasmax'][0,0,0,0]
		300.771
		"""
		
		return self.data[slice]
		

class netCDF4Dataset(Dataset):
	"""
	A subclass of the CDM Dataset class that implements netcdf4 dataset format
	
	Currently only reading is implemented.  Only a single group (root) is supported.
	"""
	
	def __init__(self, name=None, uri=None):
		"""
		Creates a new netCDFDataset instance by trying to open the file at location and building the CDM Dataset
		structure
		
		The class can be called explicitely with the uri referencing a netcdf format 
		data file:
		>>> ds = netCDF4Dataset(uri='test/data/RegCM_4-3_SampleOutput.nc')
		>>> print ds
		<netCDF4Dataset: test/data/RegCM_4-3_SampleOutput.nc>
		
		A dataset name can optionally be based to aid identification of datasets
		>>> ds = netCDF4Dataset(name='RegCM', uri='test/data/RegCM_4-3_SampleOutput.nc')
		>>> print ds
		<netCDF4Dataset: RegCM>
		
		The returned datasets instance as a default root group as per the CDM schema
		>>> print ds.root
		<CDM Group: [root]>
		
		Global group attributes are extracted from the netcdf file
		>>> print ds.root.attributes.keys()[0]
		title
		>>> print ds.root.attributes['title']
		ICTP Regional Climatic model V4
		
		Group dimensions are populated as Dimension instances
		>>> print ds.root.get_dimension('time')
		<CDM Dimension: time (12)>
		 
		Variables are populated from the netcdf file.  All dimensions are shared so 
		variable dimenion lists are all string references to global dimension names
		>>> print ds.root.variables['tasmax'].dimensions
		[u'time', u'm2', u'iy', u'jx']
		"""
		
		# Call the super constructor
		super(netCDF4Dataset, self).__init__(name=name, uri=uri)
		
		# Open the NetCDF4 file
		try:
			self.ncfile = netCDF4.Dataset(self.uri, 'r')
		except:
			raise IOError('Cannot open NetCDF file')
		
		# Creat the global attributes dictionary
		attributes = copy.deepcopy(self.ncfile.__dict__)
		
		# Create the dimensions OrderedDict
		dimensions = OrderedDict()
		for name, dimobj in self.ncfile.dimensions.items():
			dimensions[name] = Dimension(name, len(dimobj))
	
		# Create the group
		self.root = Group(name='', dataset=self, attributes=attributes, dimensions=dimensions)

		# Create the variables
		variables = {}
		for varname, varobj in self.ncfile.variables.items():
			# Create the dimensions list
			vardims = [unicode(name) for name in varobj.dimensions]
			varattrs = copy.copy(varobj.__dict__)
			variables[varname] = netCDF4Variable(varname, group=self.root, dimensions=vardims, attributes=varattrs)
			
		self.root.variables = variables

	@classmethod
	def copy(cls, dataset, filename, include=None, exclude=None, start=None, end=None):
		"""
		The copy method takes an existing pycdm.Dataset instance and (a) writes it to a NetCDF 
		before (b) returning a NetCDF4Dataset instance reflecting the new file
		"""

		# Figure out the full set of coordinates variables
		coordinates_variables = set([])
		for name, variable in dataset.root.variables.items():
			field = Field(variable)
			names = [v.name for v in field.coordinates_variables]
			coordinates_variables = coordinates_variables.union(names)
		
		#print "coordinates variables are ", coordinates_variables

		outfile = netCDF4.Dataset(filename, 'w')
		outfile.set_fill_off()

		outfile.setncatts(dataset.root.attributes)

		# Create the dimensions
		for key, dim in dataset.root.dimensions.items():
		#	print "creating dimension ", dim
			outfile.createDimension(key, dim.length)

		# Create and write the variables
		#print "creating and writing variables"
		for name, variable in dataset.root.variables.items():

		#	print name, variable

			field = Field(variable)

			# Sort out time subsetting
			realtimes = field.realtimes

			if type(realtimes) == numpy.ndarray:
				if start == None or start < realtimes[0]:
					start = realtimes[0]
				if end == None or end > realtimes[-1]:
					end = realtimes[-1]

				time_select = numpy.where(numpy.logical_and(realtimes >= start,realtimes <= end))[0]
				#print time_select

				data_slice = [slice(None)]*len(variable.shape)
				data_slice[field.time_dim] = slice(time_select[0], time_select[-1])
				data_slice = tuple(data_slice)
		#		print data_slice

				variable.group.dimensions['time'] = Dimension('time', len(time_select))

			if include and ((name not in include) and (name not in coordinates_variables)):
			#	print "skipping because of include"
				continue

			if exclude and ((name in exclude) and (name not in coordinates_variables)):
			#	print "skipping because of exclude"
				continue

			dims = variable.dimensions
			datatype = variable.data.dtype

			if datatype == type(object):
				datatype = type('str')
			if datatype == numpy.float32:
				datatype = 'f4'

			#print "creating ", name, variable, datatype, variable.dimensions, variable.attributes.items()

			if '_FillValue' in variable.attributes.keys():
				fill_value = variable.attributes['_FillValue']
			else:
				fill_value = False

			fill_value = False
			outfile.createVariable(name, datatype, dims, fill_value=fill_value, zlib=True)
			#print "new variable has shape ", outfile.variables[name].shape
			#print "original variable has shape ", variable[:].shape
			outfile.variables[name].setncatts(variable.attributes)

			#print "Assigning variable"
			#print outfile.variables[name][:].shape
			#print variable[:].shape

			outfile.variables[name][:] = variable[:]

		outfile.close()
		
	
		
		
