import numpy as np

import sys
sys.path.append('../')
import pycdm

ds = pycdm.open('data/gfs.subset.nc')

ds.root.make_fields()
