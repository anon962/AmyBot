# @todo clean up Column.setattr
class Column:
	def __init__(self, data, header="", trailer="", is_link=False, max_width=None):
		self.header= str(header)
		self.trailer= str(trailer)
		self.is_link= is_link # If true, column will not use a header nor be code-wrapped

		self.max_width= None # so the ide stops complaining
		self.__dict__['max_width']= max(len(self.header), len(self.trailer), max([len(str(x)) for x in data])) # get max_width from data
		self._limit_request= None

		self.data= []
		self.orig_data= data

	def __iter__(self):
		return self.data

	def __len__(self):
		return len(self.data)

	def __getitem__(self, ind):
		return self.data[ind]

	# @todo: handle modifications to specific data indices (eg Column.data[1]) via data wrapper class
	def __setattr__(self, key, value):
		if key in ['data', 'orig_data', 'max_width']:
			if key in ['orig_data', 'data']:
				if not value:
					self.__dict__['orig_data']= []
					self.__dict__['data']= self.__dict__['orig_data'].copy()
					return
				else:
					self.__dict__['orig_data']= value
					self.__dict__['data']= [str(x) for x in value]
			elif key == "max_width":
				if value is None: return
				self.__dict__['_limit_request']= value

			# recalculate max width and truncations
			self.__dict__['max_width']= max(len(self.header), len(self.trailer), max([len(str(x)) for x in self.data]))
			if self._limit_request is not None:
				self.__dict__['max_width']= min(int(self._limit_request), self.max_width)

			if self._limit_request:
				for i in range(len(self.orig_data)):
					if len(self.data[i]) > self._limit_request:
						self.__dict__['data'][i]= self.data[i][:self.max_width-3] + "..."

		else:
			self.__dict__[key]= value