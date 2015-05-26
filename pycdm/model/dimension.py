"""
Implements the Dimension class
"""

from error import CDMError

class Dimension(object):
	"""
	A Dimension is used to define the array shape of a Variable. It may be shared among Variables, which 
	provides a simple yet powerful way of associating Variables. When a Dimension is shared, it has a 
	unique name within the Group. If unlimited, a Dimension's length may increase. If variableLength, then 
	the actual length is data dependent, and can only be found by reading the data. A variableLength 
	Dimension cannot be shared or unlimited.
	"""
	
	def __init__(self, name, length=None, unlimited=False):
		"""
		Create a dimenion instance with a given name and length
		>>> print Dimension('latitude', length=90)
		<CDM Dimension: latitude (90)>
		>>> print Dimension('latitude').isUnlimited
		True
		>>> print Dimension('longitude', length=180).len()
		180
		>>> print Dimension('longitude', length=180).length
		180
		"""
		
		self.name = name
		self._length = length
		self._unlimited = unlimited
		self._shared = False
		
		if not length:
			self._unlimited = True
		
	@property
	def length(self):
		if not self._unlimited:
			return self._length
			
	@property
	def size(self):
		if not self._unlimited:
			return self._length	
		
	@property
	def isUnlimited(self):
		return self._unlimited
	
	@property
	def isShared(self):
		return self._shared
		
	@property
	def isVariableLength(self):
		return self._variableLength
		
	def __eq__(self, other):
		if type(other) is Dimension:
			return (self.name == other.name and self.length == other.length)
		else:
			raise TypeError('Cannot compare {} with {}'.format(Dimension, type(other)))
		
	def __repr__(self):
		return "<CDM %s: %s (%d)>" % (self.__class__.__name__, self.name, self.size)
