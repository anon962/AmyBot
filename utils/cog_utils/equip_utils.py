from utils.parse_utils import int_to_price, contains_maybe, epoch_to_date
from classes import Column, Table
import utils.cog_utils.misc_utils as misc
import json, utils, datetime

""" NOTE: find_equips and to_table should be able to handle the same keywords """

# Returns dict -- each key is an equip name -- each value is a list of dicts (sale data)
def find_equips(keyword_list):
	# inits
	data= json.load(open(utils.AUCTION_FILE, encoding='utf-8'))

	# check timestamp is after jan 1st of that year
	def check_date(timestamp, year):
		return timestamp >= datetime.datetime(year,1,1).timestamp()

	# if keyword passed in, use it to filter results
	checks= {
		"min": lambda x: int(x['price']) >= keyword_list['min'].value,
		"max": lambda x: int(x['price']) <= keyword_list['max'].value,
		"date": lambda x: check_date(x['time'], keyword_list['date'].value),
		"seller": lambda x: contains_maybe(to_search=x['seller'], to_find=keyword_list['seller'].value, spaced=False),
		"buyer": lambda x: contains_maybe(to_search=x['buyer'], to_find=keyword_list['buyer'].value, spaced=False),
		'name': lambda x: contains_maybe(to_search=x['name'], to_find=keyword_list['name'].value),
		"rare": lambda x: is_rare(x['name']),
		"norare": lambda x: not is_rare(x['name'])
	}
	checks= [checks[x] for x in checks if x in keyword_list and keyword_list[x].has_value]

	filtered= misc.filter_data(checks, data, keyword_list)
	filtered.sort(key= lambda x: x['price'], reverse=True)
	return filtered


# convert equip results to a table (string) to print
# certain columns are only printed if a relevant keyword is passed in (see key_map in config)
def to_table(command, eq_list, keyword_list, prop_dct=None):
	CONFIG= utils.load_yaml(utils.AUCTION_CONFIG)
	special_cols= ['thread', 'link', 'date'] # these have to be added last for formatting reasons

	# special formatting
	def format_stats(c): c.max_width= CONFIG[command]['stat_col_width']; return c
	def format_price(c): c.data= [str(int_to_price(x)) for x in c.data]; return c
	format_rules= dict(stats=format_stats, price=format_price)

	# get cols
	col_names= misc.get_col_names(keyword_list=keyword_list,
								  default_cols=CONFIG[command]['default_cols'],
								  key_map=CONFIG['key_map'])
	cols= misc.get_cols(data=eq_list, special_cols=special_cols, col_names=col_names,
						format_rules=format_rules, CONFIG=CONFIG)

	# add date col
	if 'date' in col_names:
		data= []
		for x in eq_list:
			x['date']= epoch_to_date(x['time'])
			tmp= utils.render(CONFIG['date_template'],x)
			data.append(tmp)
		cols.append(Column(data=data, header=CONFIG['equip_headers']['date']))

	# add link col
	if 'link' in col_names:
		cols.append(Column(data=[x['link'] for x in eq_list],
						   header=CONFIG['equip_headers']['link'], is_link=True))

	# add thread col
	if 'thread' in col_names:
		cols.append(Column(data=[x['thread'] for x in eq_list],
						   header=CONFIG['equip_headers']['thread'], is_link=True))

	# add attrs if requested
	ret= Table(cols)
	if prop_dct:
		for x in prop_dct:
			ret.__dict__[x]= prop_dct[x]

	return ret


# Potentially valuable suffix / prefixes
def is_rare(name):
	rares= ["Savage", "Mystic", "Shielding", "Charged", "Frugal", "Radiant"]
	return any(x.lower() in name.lower() for x in rares)