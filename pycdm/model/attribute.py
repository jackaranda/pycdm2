"""
Implements the AttributeList class
"""
from collections import OrderedDict

class AttributeList(object):
	"""
	An attribute list is implemented as a python dictionary where values are restricted to strings
	"""
	
	def __init__(self, attributes={}):
		"""
		>>> print AttributeList()
		<CDM AttributeList>
		>>> print AttributeList(attributes={'attr':'Attribute value'}).keys()
		['attr']
		>>> print AttributeList(attributes={'attr':1234.3}).keys()
		[]
		"""
		
		self._attributes = OrderedDict()
		
		for key, value in attributes.items():
			try:
				self.__setitem__(key, value)
			except:
				pass
				
	def __setitem__(self, key, value):
		
		if type(value) is str or type(value) is unicode or type(value) is float or type(value) is int:
			self._attributes[key] = value
		
	def __getitem__(self, key):
		return self._attributes[key]
		
	def __repr__(self):
		return "<CDM AttributeList>"
		
	def keys(self):
		return self._attributes.keys()

	def items(self):
		return self._attributes.items()
