import numpy as np
import netCDF4
import datetime
import calendar

def days_in_month(year, month, cal='standard'):
	
	# We modulo the month to 12 for convenience
	year += (month-1)/12
	month = 1 + (month-1) % 12

	#print "days_in_month: ", year, month

	if cal in ['standard', 'gregorian']:
		return calendar.monthrange(year, month)[1]
		
	if cal in ['360_day']:
		return 30
		
	if cal in ['365_day', 'no_leap']:
		days = calendar.monthrange(year, month)[1]
		if calendar.isleap(year) and month == 2:
			return 28

def time_slices(times, time_units, origin={}, length='1 month', after=None, before=None):
	
	length_parts = length.split()
	length_val = int(length_parts[0])
	length_units = length_parts[1]

	print "time_slices ", length_val, length_units

	real_times = netCDF4.num2date(times, time_units)

	# Set before and after to start and end times if not specified
	if not after:
		after = real_times[0]
	if not before:
		before = real_times[-1]

	#print "time_slices, after {} and before {}".format(after, before)

	all_years = np.arange(real_times[0].year, real_times[-1].year+1)
	
	for s in origin:
		if 'year' not in s.keys():
			years = all_years
			print years
		else:
			if type(s['year']) == list:
				years = s['year']
			else:
				years = [s['year']]
			
		if 'month' not in s.keys():
			months = np.arange(1,13)
		else:
			months = [s['month']]
		
		if 'day' not in s.keys():
			days = np.nan
		else:
			days = [s['day']]
			
		if 'hour' not in s.keys():
			hours = np.arange(0,24)
		else:
			hours = [s['hour']]

	slices = []

	#print 'years: ', years
	#print 'months: ', months

	for year in years:
		for month in months:
			
			if np.isnan(days):
				tmp_days = range(1,days_in_month(year, month))
			else:
				tmp_days = days
		
			#print "tmp_days = ",tmp_days
	
			for day in tmp_days:
				for hour in hours:
				
					this_start = datetime.datetime(year, month, day, hour)
					
					# Calculate end date based on length units and value
					if length_units == 'year':
						end_year = year + length_val
					else:
						end_year = year
						
					if length_units == 'month':
						end_month = month + length_val
					else:
						end_month = month
						
					if length_units == 'day':
						end_day = day + length_val
					else:
						end_day = day

					# Now modulo the end day and end month
					while end_day > days_in_month(end_year, end_month):
						end_day = end_day - days_in_month(end_year, end_month)
						end_month += 1
						if end_month > 12:
							end_month = end_month - 12
							end_year = end_year + 1
					
					if end_month > 12:
						end_month = end_month - 12
						end_year = end_year + 1
					

					#end_day = min(days_in_month(end_year, end_month), day)
					this_end = datetime.datetime(end_year, end_month, end_day, hour)
					
					# Check if are completely before or after the time range
					if this_start < after or this_end > before:
#						print this_start, after
#						print this_end, before
						continue

					start_value = netCDF4.date2num(this_start, time_units)
					end_value = netCDF4.date2num(this_end, time_units)
					
					# Crop origin_value and end_value to the time range
					#if start_value <= times[0]:
					if start_value <= times[0]:
						start_index = 0
					else:
						start_index = np.where(times >= start_value)[0][0]
					
					if end_value >= times[-1]:
						end_index = len(times)-1
					else:
						end_index = np.where(times <= end_value)[0][-1]
					
					#print netCDF4.date2num(this_origin, time_units), netCDF4.date2num(this_end, time_units)
					#print origin_index, end_index
					#print "from file: ", netCDF4.num2date(times[start_index], time_units), netCDF4.num2date(times[end_index], time_units)
					
					slices.append(slice(start_index, end_index))
	
	return slices

def time_aggregation(field, func, start={}, length='1 month', mask_less=np.nan, mask_greater=np.nan):
	
	print "global range ", np.ma.max(field.variable[:]), np.ma.min(field.variable[:])
	
	times = field.times
	slices = time_slices(times, field.time_variable.getAttribute('units'), start, length)
	
	shape = field.variable.shape
	
	time_dim = field.coordinates_mapping['time']['map'][0]

	new_shape = list(shape)
	new_shape[time_dim] = len(slices)
	new_shape = tuple(new_shape)
	
	source = field.variable[:]
	result = np.ma.empty(new_shape, dtype=np.float32)

	result_selection = []
	source_selection = []
	for d in shape:
		source_selection.append(slice(None))
		result_selection.append(slice(None))
	
	for i in range(len(slices)):
		source_selection[time_dim] = slices[i]
		result_selection[time_dim] = i
		#print source_selection, result_selection
		#print field.variable[source_selection].shape
		
#		tmp = np.ma.masked_array(field.variable[source_selection])
		tmp = source[source_selection]
		#print type(tmp)
		#print np.ma.min(tmp), np.ma.max(tmp)
		
		if not np.isnan(mask_less):
			tmp = np.ma.masked_less(tmp, mask_less)

		if not np.isnan(mask_greater):
			tmp = np.ma.masked_greater(tmp, mask_greater)
		
		
		result[tuple(result_selection)] = func(tmp, axis=time_dim)
		#print i, source[source_selection][:,77], result[tuple(result_selection)][77]

		
	result_times = [times[s.stop-1] for s in slices]

	return result, netCDF4.num2date(result_times, field.timevar.getAttribute('units'))
	
def time_subset(field, start={}, length='1 month', mask_less=np.nan, mask_greater=np.nan):
	
	print "global range ", np.ma.max(field.variable[:]), np.ma.min(field.variable[:])
	
	times = field.times()
	slices = time_slices(times, field.timevar.getAttribute('units'), start, length)
	
	indices = []
	for s in slices:
		indices.extend(range(s.start, s.stop))
		
	#print indices
	
	shape = field.variable.shape
	time_dim = field.coordinates_mapping['time']['map'][0]

	new_shape = list(shape)
	new_shape[time_dim] = len(indices)
	new_shape = tuple(new_shape)
	print "new shape: ", new_shape
	
	source = field.variable[:]
	print 'source: ', source
	source_selection = []
	for d in shape:
		source_selection.append(slice(None))
	source_selection[time_dim] = indices
	#print "source selection: ", source_selection
	
	return source[source_selection], netCDF4.num2date(times[indices], field.timevar.getAttribute('units'))
	
