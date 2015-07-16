import json
import netCDF4

standard = json.loads(open('cf.json').read())

def cf_time(units):

	try:
		netCDF4.num2date(0, units)
	except:
		return False
	else:
		return True

variable = {'units':'days since 1900-01-01'}

for key, config in standard:
	print config