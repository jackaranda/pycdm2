"""
Implements the Dataset class
"""
import sys

from group import Group

def open(uri):
	"""
	Simple utility function to open a dataset given a uri.  Delegates to the 
	Dataset.open class method
	"""
	
	return Dataset.open(uri=uri)


class Dataset(object):
	
	def __init__(self, name=None, uri=None):
		"""
		Creates a Dataset instance with given name and uri attributes.  Both name and uri
		are optional so you can create a nameless Dataset that is not associated with
		any specific data resource
		
		>>> ds = Dataset()
		>>> print ds
		<Dataset: None>
		"""
		self.name = name
		self.uri = uri
		self.root = Group()
		
		# If no name is given we substitute the uri as a name
		if not self.name:
			self.name = self.uri
	
	@classmethod
	def open(cls, uri):
		"""
		A class method to facilitate opening different data sources.  The approach is to
		attempt to use each subclass of Dataset to open the uri.  The first subclass
		that succeeds is used to return a Dataset subclass instance.
		
		To add handlers for different datasources the only requirement is that the 
		an Dataset subclass is created in the plugins/dataset directory which implements:
		- Dataset.__init__
		- Variable.__init__
		- Variable.__getitem__
		methods
		
		"""

		# If we have a location parameter, try to find a handler
		if uri:
			dataset = None
			for plugin in cls.__subclasses__():
				try:
					dataset = plugin(uri=uri)
				except:
					print sys.exc_info()
				else:
					break

			if dataset:
				return dataset
			else:
				raise IOError('cannot open uri: {}'.format(uri))
		
		
	def __repr__(self):
		return "<%s: %s>" % (self.__class__.__name__, self.name)

	def __unicode__(self):
		return unicode(self.__repr__())
