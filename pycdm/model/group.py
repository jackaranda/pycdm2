from attribute import AttributeList
from dimension import Dimension

from field import Field

class Group(object):
	
	def __init__(self, name='', dataset=None, parent=None, dimensions=[], attributes={}, variables={}):
		"""
		A Group is a container for Attributes, Dimensions, EnumTypedefs, Variables, and nested 
		Groups. The Groups in a Dataset form a hierarchical tree, like directories on a disk.
		There is always at least one Group in a Dataset, the root Group, whose name is the empty string.
		
		>>> print Group()
		<CDM Group: [root]>
		>>> group = Group()
		>>> child1 = Group('child1', parent=group)
		>>> child2 = Group('child2', parent=group)
		>>> print child1.parent
		<CDM Group: [root]>
		>>> print child2.parent
		<CDM Group: [root]>
		>>> print group.children
		[<CDM Group: child1>, <CDM Group: child2>]
		"""
		self._isroot = False
		self.name = name
		self.dataset = dataset
		self.parent = parent
		self.attributes = AttributeList(attributes)
		self.variables = variables
		
		self._dimensions = dimensions
		
		self.children = []
		
		# If there is no parent then this must be a root group which must have an empty 
		# string as the name
		if (not parent or name == ''):
			self._isroot = True
			self.name = ''
		
		# Add group into a datasets group hierachy
		elif (type(parent) == Group and parent.dataset == dataset):
			self.parent = parent
			parent.children.append(self)
			
		self.make_fields()
			
	def make_fields(self):
		"""
		Identify spatial fields within the group and collate variables with the same 
		spatial fields into the same group field.
		"""
		
		self.variable_fields = {}
		
		for varname, variable in self.variables.items():
			#print varname, variable
			field = Field(variable)
			#print field.variables
			#print field.coordinates_mapping
			self.variable_fields[field.variables[0].name] = field
		
		#self.fields = []
		#done = 0
		#for i in range(0, len(fields)):
			
			
			
			
		
			
	@property
	def dimensions(self):
		"""
		Returns the OrderedDict of dimensions associated with this group
		"""
		
		return self._dimensions
	
	def has_dimension(self, dimension):
		"""
		Tests for existence of a dimension.  Dimension can either be a Dimension instance
		or a name referencing an existing Dimension instance
		"""

		if isinstance(dimension, Dimension):
			if dimension.name in self._dimensions.keys():
				if dimension.length() == self._dimensions[dimension.name].length():
					return True
		elif isinstance(dimension, unicode):
			if dimension in self._dimensions.keys():
				return True
		else:
			return False
			
	def get_dimension(self, name):
		"""
		Retrieve a dimension from the group given a dimension name.
		
		Returns Dimension instance if found or None if not found.
		"""
		
		try:
			return self._dimensions[name]
		except:
			return None
	
	
	def __repr__(self):
		
		if self._isroot:
			return "<CDM %s: %s>" % (self.__class__.__name__, '[root]')
		else:
			return "<CDM %s: %s>" % (self.__class__.__name__, self.name)
			
