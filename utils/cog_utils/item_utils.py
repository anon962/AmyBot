from utils.parse_utils import int_to_price, contains_maybe, epoch_to_date
from classes import Column, Table
import utils.cog_utils.misc_utils as misc
import json, utils, datetime


# Returns dict -- each key is an item name -- each value is a list of dicts (sale data)
def find_items(keyword_list):
	# inits
	data= json.load(open(utils.ITEM_FILE, encoding='utf-8'))

	# check timestamp is after jan 1st of that year
	check_date= lambda timestamp,year: timestamp >= datetime.datetime(year,1,1).timestamp()

	# if keyword passed in, use it to filter results
	checks= {
		"minq": lambda x: x['quantity'] >= keyword_list['minq'].value,
		"maxq": lambda x: x['quantity'] <= keyword_list['maxq'].value,
		"minp": lambda x: x['price'] >= keyword_list['minp'].value,
		"maxp": lambda x: x['price'] <= keyword_list['maxp'].value,
		"minu": lambda x: x['unit_price'] >= keyword_list['minu'].value,
		"maxu": lambda x: x['unit_price'] <= keyword_list['maxu'].value,
		"date": lambda x: check_date(x['time'], keyword_list['date'].value),
		"seller": lambda x: contains_maybe(to_search=x['seller'], to_find=keyword_list['seller'].value, spaced=False),
		"buyer": lambda x: contains_maybe(to_search=x['buyer'], to_find=keyword_list['buyer'].value, spaced=False),
		'name': lambda x: contains_maybe(to_search=x['name'], to_find=keyword_list['name'].value)
	}
	checks= [checks[x] for x in checks if x in keyword_list and keyword_list[x].has_value]

	f= misc.filter_data(checks, data, keyword_list)
	f.sort(key=lambda x: x['time'], reverse=True)
	return f


# convert item results to a table (string) to print
# certain columns are only printed if a relevant keyword is passed in (see key_maps)
def to_table(command, lst, keyword_list, prop_dct=None):
	CONFIG= utils.load_yaml(utils.ITEM_CONFIG)
	special_cols= ['date'] # these have to be added last for formatting reasons

	# special formatting
	def format_stats(c): c.max_width= CONFIG[command]['stat_col_width']; return c
	def format_price(c): c.data= [str(int_to_price(x)) for x in c.data]; return c
	def format_quant(c): c.data= [f"{int(x):,}" for x in c.orig_data]; return c
	format_rules= dict(stats=format_stats, price=format_price, unit_price=format_price, quantity=format_quant)

	# get cols
	col_names= misc.get_col_names(default_cols=CONFIG[command]['default_cols'],
								  key_map=CONFIG['key_map'],
								  keyword_list=keyword_list)
	cols= misc.get_cols(data=lst, special_cols=special_cols, col_names=col_names,
						format_rules=format_rules, CONFIG=CONFIG)

	# add date col
	if 'date' in col_names:
		data= []
		for x in lst:
			x['date']= epoch_to_date(x['time'])
			tmp= utils.render(CONFIG['date_template'],x)
			data.append(tmp)
		cols.append(Column(data=data, header=CONFIG['equip_headers']['date']))

	# add attrs if requested
	ret= Table(cols)
	if prop_dct:
		for x in prop_dct:
			ret.__dict__[x]= prop_dct[x]

	# return
	return ret



