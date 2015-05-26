"""
Implements the "Claris" ASCII data format Variable and Dataset subclasses.

NOTE: The current implementation holds the file contents in memory on opening!
"""

import copy
from collections import OrderedDict

import netCDF4
import numpy
from dateutil import parser

from pycdm import Group
from pycdm import Variable
from pycdm import Dataset
from pycdm import Dimension

class clarisVariable(Variable):
	"""
	A subclass of the CDM Variable class that implements Claris variable access
	"""
	
	def __init__(self, name, group, data, **kwargs):
		"""
		Creates a new clarisVariable instance
		"""
		super(clarisVariable, self).__init__(name, group=group, **kwargs)
		self._data = data
	
	def __getitem__(self, slice):
		"""
		Implements the get item array slicing method.  		
		"""
		
		return self._data[slice]

class clarisDataset(Dataset):

	def __init__(self, name=None, uri=None):
		
		# Call the super constructor
		super(clarisDataset, self).__init__(name=name, uri=uri)
		
		# Open the file
		try:
			file = open(self.uri, 'r')
		except:
			raise IOError('Cannot open file file: {}'.format(file))

		# Read contents and split
		file_data = [line.split() for line in file.readlines()]
		file.close()

		# Try and see if we have a header line
		if ('date' in file_data[0]):
			header = 1
			header_fields = file_data[0]
		else:
			header = False
			header_fields = ['']*len(file_data[0])
			header_fields[-3:] = ['pr', 'tmax', 'tmin']

		# Convert to lower case to avoid case problems
		header_fields = [field.lower() for field in header_fields]

		# Try and figure out the station id.  It is either a labelled column, or the first column
		id = None
		
		# See if we can find a named column
		for name in ['id', 'station_id']:
			try:
				id = file_data[header][header_fields.index(name)]
			except:
				pass

		# if that didn't work then it might still be the first column
		if header_fields[0].lower() == '':
			id = repr(file_data[header][0])
		
		# If not then we are stuck!
		if not id:
			raise IOError("Cannot determine station id, giving up")


		# Try and figure out which are/is the date column(s)
		# first we try a single column
		date_colum = None
		for col in range(0,len(header_fields)):
			try:
				test = parser.parse(file_data[1][col])
			except:
				pass
			else:
				date_column = col
				break

		# if that fails we try a three column scheme
		if not date_column:
			for col in range(0, len(header_fields) - 3):
				
				merged = ""
				for part in file_data[1][col:col+3]:
					merged += part

				try:
					test = parser.parse(merged)
				except:
					pass
				else:
					date_column = slice(col,col+3)

		# If still no success then we have a problem
		if not date_column:
			raise IOError("Cannot determine date column")

		# Create the time data array
		times_list = []
		try:
			for row in file_data[header:]:

				if type(date_column) == 'slice':
					merged = ""
					for part in row[col:col+3]:
						merged += part

					times_list.append(parser.parse(merged))

				else:
					times_list.append(parser.parse(row[date_column]))

		except:
			raise IOError("Cannot parse dates, problem on row {}".format(row))

		time_units = "days since {}".format(times_list[0].isoformat())
		times = numpy.array([netCDF4.date2num(date, time_units) for date in times_list])


		# Create the dimensions
		dimensions = OrderedDict()
		dimensions['time'] = Dimension('time', len(file_data)-header)
		dimensions['latitude'] = Dimension('latitude', 1)
		dimensions['longitude'] = Dimension('longitude', 1)
		dimensions['feature'] = Dimension('id', 1)

		# Create any global attributes
		attributes = {}
		attributes['history'] = "Created by pycdm.plugins.dataset.claris_ascii from {}\n".format(uri)
	
		# Create the group
		self.root = Group(name='', dataset=self, attributes=attributes, dimensions=dimensions)

		# Create the variables
		variables = {}
#		for varname, varobj in self.ncfile.variables.items():
#			# Create the dimensions list
#			vardims = [unicode(name) for name in varobj.dimensions]
#			varattrs = copy.copy(varobj.__dict__)
#			variables[varname] = netCDF4Variable(varname, group=self.root, dimensions=vardims, attributes=varattrs)

		variables['time'] = clarisVariable('time', self.root, times, dimensions=[u'time'], attributes={'units':time_units})
		variables['id'] = clarisVariable('id', self.root, numpy.array([id]), dimensions=[u'feature'])

		for col in range(0,len(header_fields)):

			if header_fields[col] not in ['date', 'station_id', 'id']:

				# Try and create a numerical array
				try:
					data = numpy.array([float(record[col]) for record in file_data[header:]], dtype=numpy.float32)
					numeric = True
				except:
					numeric = False

				# If numerical not possible then character array
				if not numeric:
					try:
						data = numpy.array(file_data[header:][col])
					except:
						raise IOError("Can't convert values to float or string!")

				variables[header_fields[col]] = clarisVariable(header_fields[col], self.root, data, dimensions=[u'time', u'feature'])
			
		self.root.variables = variables
