"""
Implements the "Claris" ASCII data format Variable and Dataset subclasses.  The constructor uri
argument can be either a directory path pointing to a list of files, or a single file path.  For 
a directory path all files in the directory are opened in turn and if in claris format are added
to the dataset.  For a single file path only the single file is used.

If 

NOTE: The current implementation holds the file contents in memory on opening!
"""

import copy
from collections import OrderedDict
import os, os.path

import netCDF4
import numpy
from dateutil import parser

from pycdm import Group
from pycdm import Variable
from pycdm import Dataset
from pycdm import Dimension
import datetime

default_date = datetime.datetime(1900,1,1,12)

class clarisVariable(Variable):
	"""
	A subclass of the CDM Variable class that implements Claris variable access
	"""
	
	def __init__(self, name, group, data, **kwargs):
		"""
		Creates a new clarisVariable instance
		"""
		super(clarisVariable, self).__init__(name, group=group, **kwargs)
		self.data = data
	
	def __getitem__(self, slice):
		"""
		Implements the get item array slicing method.  		
		"""
		#print "In __getitem__(self, {})".format(slice)
		#print self.data.shape
		return self.data[slice]

class clarisDataset(Dataset):

	def __init__(self, name=None, uri=None):
		"""
		A dataset is initialised by providing a uri to the list of files to open
		"""
		# Call the super constructor
		super(clarisDataset, self).__init__(name=name, uri=uri)
		
		# See if we have a directory or a file
		if os.path.isdir(uri):
			allfilenames = os.listdir(uri)
		else:
			allfilenames = [uri]

		# Sort the filenames... this is an attempt to keep ensemble member ordering consistent... 
		# but its not guarenteed
		allfilenames.sort()

		# Now try and open each file in turn
		all_data = []
		for filename in allfilenames:
			fullpath = "{}/{}".format(uri, filename)

			try:
				all_data.append(readsingle(fullpath))
			except:
				pass

		print "Found {} claris files".format(len(all_data))

		# Check if we have anything
		if len(all_data) == 0:
			raise IOError("Cannot open claris dataset at {}".format(uri))


		# Group
		grouped = {}
		max_groups = 1
		for s in all_data:
			id = s['id']

			# Check if we already have something for this ID
			if id in grouped.keys():

				print "already have data for {}, grouping...".format(id)

				# Check if the new samples times are the same
				if s['times'][0] == grouped[id]['times'][0] and s['times'][-1] == grouped[id]['times'][-1]:

					# Create ensemble list of numpy arrays
					#print grouped[id]['variables']
					for varname, data in grouped[id]['variables'].items():
						print varname, type(data)
					
						if type(data) != list:
							grouped[id]['variables'][varname] = list([data])

						grouped[id]['variables'][varname].append(s['variables'][varname])

						max_groups = max(max_groups, len(grouped[id]['variables'][varname]))
						print "max_groups = ", max_groups

				# Else time periods might be sequential
				#elif

			else:
				grouped[s['id']] = s


		print "Found {} groups".format(max_groups)

		# Use times list from first file (should handle different times lists at some point!)
		times_list = all_data[0]['times']
		time_units = "days since {}".format(times_list[0].isoformat())
		times = numpy.array([netCDF4.date2num(date, time_units) for date in times_list])

		# Get ids
		ids = grouped.keys()
		print "ids = ", ids

		# Create the dimensions
		dimensions = OrderedDict()
		dimensions['time'] = Dimension('time', len(times_list))
		#dimensions['latitude'] = Dimension('latitude', len(ids))
		#dimensions['longitude'] = Dimension('longitude', len(ids))
		dimensions['feature'] = Dimension('id', len(ids))

		# Create group dimension if we have groups
		if max_groups > 1:
			dimensions['group'] = Dimension('group', max_groups)

		# Create any global attributes
		attributes = {}
		attributes['history'] = "Created by pycdm.plugins.dataset.claris_ascii from {};".format(uri)
	
		# Create the group
		self.root = Group(name='', dataset=self, attributes=attributes, dimensions=dimensions)

		# Create "empty" latlonelev array as space filler
		latlonelev = numpy.empty((len(ids)), dtype=numpy.float32)
		latlonelev[:] = 1e10
		latlonelev = numpy.ma.masked_greater(latlonelev, 1e9)
		#print "dummy coordinate variable ", len(ids), latlonelev.shape

		# Create the variables
		variables = {}
		variables['time'] = clarisVariable('time', self.root, times, dimensions=[u'time'], attributes={'units':time_units})
		variables['id'] = clarisVariable('id', self.root, numpy.array(ids), dimensions=[u'feature'])
		variables['latitude'] = clarisVariable('latitude', self.root, numpy.copy(latlonelev), dimensions=[u'feature'], attributes={'units':'degrees north'})
		variables['longitude'] = clarisVariable('longitude', self.root, numpy.copy(latlonelev), dimensions=[u'feature'], attributes={'units':'degrees east'})
		variables['elevation'] = clarisVariable('elevation', self.root, numpy.copy(latlonelev), dimensions=[u'feature'], attributes={'units':'m'})

		# Create the data variables
		for varname in grouped[ids[0]]['variables'].keys():
			print 'creating ', varname
			# Create placeholder array
			if max_groups > 1:
				tmp = numpy.empty((len(times_list), max_groups, len(ids)), dtype=numpy.float32)
				dim_list = [u'time', u'group', u'feature']
			else:
				tmp = numpy.empty((len(times_list), len(ids)), dtype=numpy.float32)
				dim_list = [u'time', u'feature']

			tmp[:] = 1e10

			column = 0
			for id in ids:
				#print grouped[id]['variables'][varname]
				#print numpy.array(grouped[id]['variables'][varname]).T.shape

				if max_groups > 1:
					tmp[:,:,column] = numpy.array(grouped[id]['variables'][varname]).T
					print tmp[:,:,column]
				else:
					tmp[:,column] = numpy.array(grouped[id]['variables'][varname])

				#print s['id'], s['variables'][varname]
				#tmp[:,column] = s['variables'][varname]
				column += 1
			
			print "variable[{}].shape {}".format(varname, tmp.shape)
			#print numpy.ma.masked_greater(tmp, 1e9)

			attributes = {"coordinates": "latitude longitude"}

			variables[varname] = clarisVariable(varname, self.root, numpy.ma.masked_greater(tmp, 1e9), dimensions=dim_list, attributes=attributes)
			print variables[varname].shape
		# Assign the variables to the root group and we are done!
		self.root.variables = variables

	def metadata(cls, path):
		"""
		Try and read a file as a claris metadata file.  Metadata file format is tab delimited as follows:
		ID LATITUDE LONGITUDE ELEVATION NAME COUNTRY PROVINCE INSTITUTION
		"""

		metafile = open(path)

		metalines = [line.split('\t') for line in metafile.readlines()]

		# Should have 8 columns
		if len(metalines)[0] != 8:
			raise IOError("Expected 8 columns in meta data file")

		# May have a header
		if "latitude" in [field.lower() for field in metalines[0]]:
			header = 1
		else:
			header = 0

		metadata = {}
		for line in metalines[header]:
			meta = {}
			meta['latitude'] = float(line[1])
			meta['longitude'] = float(line[2])
			meta['elevation'] = float(line[3])
			meta['name'] = unicode(line[4])
			meta['country'] = unicode(line[5])
			meta['province'] = unicode(line[6])
			meta['institution'] = unicode(line[7])
			metadata[line[0]] = meta

		return metadata


def readsingle(path):
	"""
	Read a single claris station file, raise IOError if it fails.  Returns a dict with the 
	structure:
	{
		'id':STATION_ID,
		'times':TIMES_LIST,
		'variables':{
			'pr':[numpy.Array]
			'tmax':[numpy.Array]
			'tmin':[numpy.Array]
		}	
	}

	raises an IOError if it fails to read the file in any way.
	"""

	# Open the file
	try:
		print "opening {}".format(path)
		file = open(path, 'r')
	except:
		raise IOError("Error opening file {}".format(path))
	#else:
	#	print "opened file"

	# Read contents and split
	file_data = [line.split() for line in file.readlines()]
	file.close()
	#print file_data[0]

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

	# Try and figure out the station id column.  It is either a labelled column, or the first column
	id = None
	
	# See if we can find a named column
	for name in ['id', 'station_id']:
		try:
			id = unicode(file_data[header][header_fields.index(name)])
		except:
			pass

	# if that didn't work then it might still be the first column
	if header_fields[0] == '':
		id = unicode(file_data[header][0])
		header_fields[0] ='id'
	
	# If not then we are stuck!
	if not id:
		raise IOError("Cannot determine station id, giving up")


	# Try and figure out which are/is the date column(s)
	# first we try a 3 column date because this will fail for 1 column dates
	date_column = None
	for col in range(0, len(header_fields) - 3):
		
		s = file_data[1][col:col+3]
		merged = "{}-{}-{}".format(s[0], s[1], s[2])
		try:
			test = parser.parse(merged)
		except:
			pass
		else:
			date_column = slice(col,col+3)
			header_fields[date_column] = ['year', 'month', 'day']
			break

	# Second we try a one column date because this wouldn't fail for 3 column dates
	if not date_column:
		for col in range(0,len(header_fields)):
			try:
				test = parser.parse(file_data[1][col])
			except:
				pass
			else:
				date_column = col
				break

	# If still no success then we have a problem
	if not date_column:
		raise IOError("Cannot determine date column")

	#print "header = {}".format(header)
	print "id = {} ".format(id), 
	#print "date column = {}".format(date_column)

	# Create the time data array
	times_list = []
	try:
		for row in file_data[header:]:

			if type(date_column) == slice:
				s = row[date_column]
				merged = "{}-{}-{}".format(s[0], s[1], s[2])
				#print "merged date = ", merged
				times_list.append(parser.parse(merged, default=default_date))

			else:
				times_list.append(parser.parse(row[date_column], default=default_date))

	except:
		raise IOError("Cannot parse dates, problem on row {}".format(row))

	print "first date = {}".format(times_list[0])

	# Now read all data columns
	variables = {}
	print 'header_fields = ', header_fields
	for col in range(0,len(header_fields)):

		if header_fields[col] not in ['date', 'year', 'month', 'day', 'station_id', 'id']:

			#print "[val[col] for val in file_data[header:] ", [val[col] for val in file_data[header:]]

			# Replace NA with 1e9
			for record in file_data[header:]:
				if record[col] == 'NA':
					record[col] = 1e10

			# Try and create a numerical array
			try:
				data = numpy.array([float(record[col]) for record in file_data[header:]], dtype=numpy.float32)
				numeric = True
			except:
				numeric = False

			# If numerical not possible then character array
			if not numeric:
				try:
					data = numpy.array([val[col] for val in file_data[header:]])
				except:
					raise IOError("Can't convert values to float or string!")

			#print data.shape
			variables[header_fields[col]] = data

	print "returning ", variables.keys()
	return {'id':id, 'times':times_list, 'variables':variables}
