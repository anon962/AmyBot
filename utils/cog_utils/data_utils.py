"""
Functions for loading each main data file, creating the file from cached pages if necessary.
"""

from classes import SuperScraper, KedamaScraper, MarketScraper
from datetime import datetime
import utils, os

async def merge_auctions():
	# get data
	if not os.path.exists(utils.SUPER_EQUIP_FILE):
		_,s_data= await SuperScraper.parse()
	else: s_data= utils.load_json_with_default(utils.SUPER_EQUIP_FILE, default=False)

	if not os.path.exists(utils.KEDAMA_EQUIP_FILE):
		_,k_data= KedamaScraper.parse()
	else: k_data= utils.load_json_with_default(utils.KEDAMA_EQUIP_FILE, default=False)

	# merge data
	merged_data= []
	for x in s_data:
		x['type']= "super"
		merged_data.append(x)
	for x in k_data:
		x['type']= "kedama"
		merged_data.append(x)

	# dump
	utils.dump_json(merged_data, utils.AUCTION_FILE)
	return merged_data

async def merge_items():
	# get data
	if not os.path.exists(utils.SUPER_ITEM_FILE):
		_,s_data= await SuperScraper.parse()
	else: s_data= utils.load_json_with_default(utils.SUPER_ITEM_FILE, default=False)

	if not os.path.exists(utils.KEDAMA_ITEM_FILE):
		_,k_data= KedamaScraper.parse()
	else: k_data= utils.load_json_with_default(utils.KEDAMA_ITEM_FILE, default=False)

	if not os.path.exists(utils.MARKET_ITEM_FILE):
		_,h_data= await MarketScraper.scrape()
	else: h_data= utils.load_json_with_default(utils.MARKET_ITEM_FILE, default=False)


	# merge data
	merged_data= []
	for x,y in [('super',s_data), ('kedama',k_data)]:
		for z in y:
			z['type']= x
			merged_data.append(z)
	for x in h_data:
		h_data[x]['type']= "market"
		merged_data.append(h_data[x])

	# dump
	utils.dump_json(merged_data, utils.ITEM_FILE)
	return merged_data

def check_update_log(check_name, min_time, exact_day=None):
	# inits
	time_check= False
	day_check=False

	log= utils.load_json_with_default(utils.UPDATE_LOG)
	log.setdefault(check_name, 0)

	# check if right day
	if datetime.today().weekday() == exact_day or exact_day is None:
		day_check= True

	# check if enough time has passed since last check
	if day_check:
		now= datetime.now().timestamp()
		if now - log[check_name] > min_time:
			time_check= True

	# dump and return
	return day_check and time_check