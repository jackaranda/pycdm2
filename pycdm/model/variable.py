from collections import OrderedDict

import numpy

from attribute import AttributeList
from group import Group
from dimension import Dimension
from field import Field
from error import CDMError


class Variable(object):
	"""
	A Variable is a container for data. It has a DataType, a set of Dimensions that define its array 
	shape, and optionally a set of Attributes. Any shared Dimension it uses must be in the same Group 
	or a parent Group.
	"""
	
	def __init__(self, name, group=None, dimensions=[], attributes={}, dtype=numpy.float32, data=None):
		"""
		<group> parameter is optional but if no group is provided then named dimensions cannot
		be used, rather dimensions has to contain only Dimension instances
		
		<dimensions> is a ordered dict of Dimension instances or names referencing existing 
		Dimension instances in the group
		
		<attributes> is a dictionary used to intialise the attributes list
		
		<data> can be used to create an in memory variable, it must be a numpy.ndarray 
		instance of the correct dimensionality as described by the dimensions list
		
		>>> print Variable('myvariable')
		<CDM Variable: myvariable>
		>>> print Variable('myvariable', group=Group())
		<CDM Variable: myvariable>
		"""
		self.name = name
		self.data = data

		#print "in Variable.__init__  data.shape = ", self.data.shape
		
		# Check group argument is a Group instance
		if group:
			if type(group) is Group:
				self.group = group
			else:
				raise TypeError('group is of type {}, expecting an object of type {}'.format(type(group), Group))
		else:
			self.group = None
						
		# Initialise the attributes list from the attributes argument
		self.attributes = AttributeList(attributes)
		
		# Check all passed dimensions are Dimension instances or names of dimensions 
		# already defined in the parent group
		self.dimensions = []
		for dimension in dimensions:
			
			# See if we have a Dimension instance
			if type(dimension) is Dimension:
				self.dimensions.append(dimension)
				
			# else we might have a dimension name as a unicode instance
			elif type(dimension) is unicode:
				
				# We can't have named dimensions if we don't have a group
				if not self.group:
					raise CDMError('Cannot use named dimensions without a group')
				
				# If we have a group then the named dimension needs to be in the group
				# otherwise we raise an exception
				else:
					if self.group.has_dimension(dimension):
						self.dimensions.append(self.group.get_dimension(dimension))
					else:
						raise CDMError('Named dimension {} not found in group dimensions'.format(dimension))
			
			
	def __repr__(self):
	
		return "<CDM Variable: {}>".format(self.name)
		
	@property
	def shape(self):
		"""
		Returns a shape tuple representing the data shape of the variable
		
		>>> var = Variable('test', dimensions=[Dimension('x',40), Dimension('y',60)])
		>>> print var.shape
		(40, 60)
		"""
		
		shape = []
		for d in self.dimensions:
			
			# Check if we have a Dimension instance or just a name
			if isinstance(d, Dimension):
				shape.append(d.size)
			else:
				shape.append(self.group.get_dimension(d).size)
		
		return tuple(shape)
		
	
	def get_attribute(self, name):
		"""
		Return the value of the attribute with given name or None if such an attribute does
		not exist
		"""
		
		if name in self.attributes.keys():
			return self.attributes[name]
		else:
			return None
			
	
	def __getitem__(self, slices):
		
		return self.data[slices]

	def __setitem__(self, slices, data):
		print self.name, slices
		self.data[slices] = data
		
					
