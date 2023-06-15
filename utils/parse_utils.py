import utils, datetime

def parse_keywords(query, keywords):
	"""
	Converts string such as "blah keywordval" into { "keyword": val }.

	:param query: String containing 0 or more keywords
	:param keywords: Dictionary of keyword : parsing function. If keyword is found and parsing function is not None, parsing function is applied to value found
	:param aliases: Dictionary of keyword : list of aliases
	:param reps: Dictionary of x : list y. Replace all substrings in query that are outlined in list y with string x.
	:return: Dictionary containing query with keywords removed and dictionary of keyword : parsed value
	"""
	# inits
	split= [x.lower() for x in query.split()]
	inds= [] # marks words in query to remove later

	# search for keywords
	# if duplicate keywords in query, only last value used
	for k in keywords:
		for i,x in enumerate(split):
			if k.get_val(x):
				inds.append(i)

	# clean up query
	inds.sort(reverse=True)
	for i in inds:
		split.pop(i)

	return " ".join(split), keywords


# ---- Parsing Functions ----
# Invalid values should raise an Exception with a reason supplied to the constructor
# These exceptions are then wrapped into a ParseError by the Keyword class

def int_to_price(x, numDec=1):
	sx= str(x).replace(",","")

	if len(sx) > 6: sx= sx[:-6] + "." + sx[-6:][:numDec] + "m"
	elif len(sx) > 3: sx = sx[:-3] + "." + sx[-3:][:numDec] + "k"
	else: sx+= "c"

	if "." in sx:
		while sx[-2] == '0': sx= sx[:-2] + sx[-1]
		if sx[-2]== ".": sx =sx[:-2] + sx[-1]

	return sx

def price_to_int(x):
	x= str(x).replace(",","").replace("c","")

	ix = (x.lower().replace("k", "000").replace("m", "000000"))
	if "." in x:
		numDec = len(str(x).replace("k","").replace("m","").split(".")[1])
		ix = ix[:-numDec].replace(".", "")

	return to_int(ix)

def to_int(val):

	if val.strip() == "":
		STRINGS= utils.load_yaml(utils.ERROR_STRING_FILE)
		raise Exception(STRINGS['int_reasons']['empty'])

	try:
		return int(val)
	except ValueError:
		STRINGS= utils.load_yaml(utils.ERROR_STRING_FILE)
		raise Exception(STRINGS['int_reasons']['not_int'])

def to_pos_int(val):
	ret= price_to_int(val)
	if ret < 0:
		STRINGS= utils.load_yaml(utils.ERROR_STRING_FILE)
		raise Exception(STRINGS['int_reasons']['negative'])
	return ret

def to_bool(val, empty=True):
	if str(val) == "": return empty
	else: return bool(val)

def to_potential_string(val, empty=True):
	if str(val) == "": return empty
	else: return val

# Checks that all words in to_find are contained in to_search
def contains(to_search, to_find):
	if isinstance(to_find, list):
		pass
	elif isinstance(to_find, str):
		to_find= [x.lower() for x in to_find.split()]
	else: raise ValueError(f"'{type(to_find)}' passed to 'contains' function as 'to_find' arg")

	to_search= to_search.lower()
	return all(x in to_search for x in to_find)

# if bool, then don't use it as filtering criteria
def contains_maybe(to_search, to_find, spaced=True):
	if isinstance(to_search, bool) or isinstance(to_find, bool):
		return True
	else:
		if not spaced:
			to_search= to_search.replace(" ", "")
			to_find= to_find.replace(" ", "")
		return contains(to_search=to_search, to_find=to_find)


def to_epoch(year, month, day, hour=0, minute=0):
	args= [int(x) for x in [year,month,day,hour,minute]]
	if len(str(args[0])) == 2: args[0]= int(f"20{args[0]}")
	return datetime.datetime(*args).timestamp()

def epoch_to_date(epoch):
	d= datetime.datetime.fromtimestamp(epoch)
	return [d.year, d.month, d.day, d.minute, d.second]

# workaround for parsing the alias "20" properly
# eg any in [date2019, 2019, year2019] will parse to 2019
def to_year(val):
	if val.startswith("20") and len(val) > 2: pass
	else: val= "20" + val

	return to_pos_int(val)

def get_date_key():
	from classes.keyword import Keyword
	return Keyword("date", to_year, aliases=["year", "20", "year20"])