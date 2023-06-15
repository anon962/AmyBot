from discord.ext import commands
from utils.cog_utils import categorize, item_utils
from classes import PartialCommand, PartialCog, KeywordList, Keyword
from classes.errors import TemplatedError
from utils import cog_utils

import utils, copy
import utils.parse_utils as Parse

COG_NAMES= utils.load_yaml(utils.NAME_STRING_FILE)['item']

base_keys= KeywordList([
	Parse.get_date_key(),
	Keyword("name", Parse.to_potential_string, aliases=["name"]),
	Keyword("seller", Parse.to_potential_string, aliases=["sell", "sold"]),
	Keyword("buyer", Parse.to_potential_string, aliases=["buy", "bought"]),
	Keyword("minq", Parse.to_pos_int),
	Keyword("maxq", Parse.to_pos_int),
	Keyword("minp", Parse.price_to_int),
	Keyword("maxp", Parse.price_to_int),
	Keyword("minu", Parse.price_to_int),
	Keyword("maxu", Parse.price_to_int),
])

class ItemCog(PartialCog, name=COG_NAMES['cog_name']):

	@commands.command(**COG_NAMES['commands']['item'], cls=PartialCommand)
	async def item(self, ctx):
		# inits
		CONFIG= utils.load_yaml(utils.ITEM_CONFIG)['item']
		clean_query,keywords= Parse.parse_keywords(ctx.query, copy.deepcopy(base_keys))
		keywords['name'].value= clean_query

		# enforce minimum query length
		if not cog_utils.check_query_length(keywords, min_length=CONFIG['min_search_length']):
			raise TemplatedError("short_query")

		# search and group
		item_list= item_utils.find_items(keywords)
		cats= categorize(item_list, "name")

		# convert to tables
		del keywords['name']
		tables= [item_utils.to_table("item", cats[x], keywords, dict(name=x)) for x in cats]

		# convert to strings
		table_strings= cog_utils.stringify_tables(tables, header_func=lambda x: x.name)

		# add table summary
		for i,x in enumerate(cats.keys()):
			total_units= sum(y['quantity'] for y in cats[x])
			total_price= sum(y['price'] for y in cats[x])
			table_strings[i]+= f"# {''.join(['-']*(sum(x.max_width for x in tables[i].columns)+3*len(tables[i].columns)-2))}\n"
			table_strings[i]+= f"# Total Units: [{total_units:,}] | Total Price: [{Parse.int_to_price(total_price)}]\n"

		# return
		return await cog_utils.pageify_and_send(ctx, table_strings, CONFIG)

	@staticmethod
	def _search(item_name, keywords):
		DATA= utils.load_json_with_default(utils.ITEM_FILE, default=False)