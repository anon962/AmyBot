from classes.errors import ParseError

# todo: properties
class Keyword:
	def __init__(self, name, parsing_function=None, aliases=None):
		self.name= name
		self.__dict__['value']= None
		self.has_value= False

		if parsing_function is None: # default parsed value type is string
			self.parsing_function= lambda x: str(x)
		else:
			self.parsing_function= parsing_function

		if aliases is None:
			self.aliases= []
		else:
			self.aliases= aliases

	# force lower-case
	def __setattr__(self, key, value):
		if key in ['name']:
			self.__dict__[key]= value.lower()
		elif key in ['aliases']:
			self.__dict__[key]= [x.lower() for x in value]
		elif key in ['value']:
			self.__dict__['has_value']= True
			self.__dict__['value']= value
		else:
			self.__dict__[key]= value

	def __bool__(self):
		return bool(self.value) and self.has_value

	# for debug purposes
	def __str__(self):
		return f"Keyword [{self.name}] {'has value [{}]'.format(self.value) if self.has_value else 'has no value.'}"

	# split key and val (eg min30k --> 30k) and apply parsing function
	def get_val(self, string):
		to_chk= [self.name] + self.aliases
		to_chk.sort(key=lambda x: len(x), reverse=True) # check longest first

		for x in to_chk:
			if string.startswith(x):
				tmp= string.replace(x,"",1)

				try:
					self.value= self.parsing_function(tmp)
				except Exception as e:
					raise ParseError(keyword=self.name, value=string, reason=str(e))

				return self.value

		return None