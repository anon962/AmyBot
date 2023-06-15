from utils.scraper_utils import get_html, get_session
from utils.parse_utils import price_to_int, to_epoch
from bs4 import BeautifulSoup
import utils, asyncio, glob, os, re

class SuperScraper:
	SCRAPE_DELAY= 3
	HOME_BASE_LINK= r"https://reasoningtheory.net/"
	THREAD_BASE_LINK= r"https://forums.e-hentai.org/index.php?showtopic="
	DEFAULT_CACHE= {
		"seen": [],
		"parsed": dict(files=[], items=[], equips=[]),
		"num_map": {}, # itemlist name --> auction_number
		"time_map": {}, # itemlist name --> epoch timestamp
		"fails": [] # parsing fails
	}
	ITEM_REGEX= {
		"quant_name": re.compile(r"(?:(\d+) )?(.*)"), # num is optional since "Pony figurine set" was a thing ¯\_(ツ)_/¯
		"price_buyer": re.compile(r"(\d+[mkc]) \((.*) #[\d.]+\)")
	}
	EQUIP_REGEX= {
		"level_stats": re.compile(r"(\d+|Unassigned|n/a)(?:, (.*))?"),
		"price_buyer": re.compile(r"(\d+[mkc]) \((.*) #[\d.]+\)"),
		"stat_cleaning": re.compile(r"(\w+ )EDB", flags=re.IGNORECASE) # Elec EDB --> EDB
	}


	@classmethod
	async def scrape(cls):
		# inits
		CACHE= utils.load_json_with_default(utils.SUPER_CACHE_FILE, default=cls.DEFAULT_CACHE)

		async with get_session() as session:
			# check for new auctions
			home_html= await get_html(cls.HOME_BASE_LINK, session)
			home_soup= BeautifulSoup(home_html, 'html.parser')

			rows= home_soup.find("tbody").find_all("tr")
			auc_names= [r.find("a", href=lambda x: x and "itemlist" in x)['href'] for r in rows]
			auc_nums= [r.find("td").get_text().zfill(3) for r in rows]
			auc_dates= [r.find_all("td")[1].get_text() for r in rows]
			auc_dates= [cls._to_epoch(x) for x in auc_dates]
			assert len(auc_names) == len(auc_nums) == len(auc_dates)

			# get uncached pages
			new_aucs= []
			for i in range(len(rows)):
				if auc_names[i] not in CACHE['seen']:
					new_aucs.append((auc_nums[i], auc_names[i], auc_dates[i]))

			# create folder for auction page html
			if not os.path.exists(utils.SUPER_HTML_DIR):
				os.makedirs(utils.SUPER_HTML_DIR)

			# pull uncached pages
			for num,name,date in new_aucs:
				out_path= utils.SUPER_HTML_DIR + name + ".html"

				if not os.path.exists(out_path):
					await asyncio.sleep(cls.SCRAPE_DELAY)

					auc_html= await get_html(cls.HOME_BASE_LINK + name, session)
					if "Auction ended" not in auc_html: continue # ignore ongoing

					with open(out_path, "w", encoding='utf-8') as f:
						f.write(auc_html)

				tmp= name.replace("itemlist","")
				CACHE['seen'].append(name)
				CACHE['num_map'][tmp]= num
				CACHE['time_map'][tmp]= date


			# update cache
			if new_aucs:
				CACHE['seen'].sort(reverse=True)
				utils.dump_json(CACHE, utils.SUPER_CACHE_FILE)

		# true if new auctions found
		return bool(new_aucs)


	@classmethod
	async def parse(cls):
		# inits
		CACHE= utils.load_json_with_default(utils.SUPER_CACHE_FILE, default=cls.DEFAULT_CACHE)
		EQUIP_DATA= utils.load_json_with_default(utils.SUPER_EQUIP_FILE, default=[])
		ITEM_DATA= utils.load_json_with_default(utils.SUPER_ITEM_FILE, default=[])

		for x in ['files', 'equips', 'items']:
			CACHE['parsed'][x]= set(CACHE['parsed'][x])

		# scan auctions
		for file in glob.glob(utils.SUPER_HTML_DIR + "*.html"):
			auc_name= os.path.basename(file).replace(".html","")

			# skip ones already cached
			if auc_name in CACHE['parsed']: continue

			# get data
			result= cls._parse_page(open(file, encoding='utf-8').read())
			items= result['items']
			equips= result['equips']
			fails= [f"{auc_name} - {y}" for y in result['fails']]

			# add in dates / auction numbers
			if auc_name not in CACHE['seen']:
				await cls.scrape() # cache probably got deleted

			for x in items + equips:
				tmp= auc_name.replace("itemlist","")
				x['auction_number']= CACHE['num_map'][tmp]
				x['time']= CACHE['time_map'][tmp]
				x['thread']= cls.THREAD_BASE_LINK + tmp
				x['id']= f"{x['auction_number']}_{x['id']}"

			for x in items:
				if x['id'] not in CACHE['parsed']['items']:
					ITEM_DATA.append(x)
					CACHE['parsed']['items'].add(x['id'])

			for x in equips:
				if x['id'] not in CACHE['parsed']['equips']:
					EQUIP_DATA.append(x)
					CACHE['parsed']['equips'].add(x['id'])

			CACHE['fails']+= fails
			CACHE['parsed']['files'].add(auc_name)

		utils.dump_json(ITEM_DATA, utils.SUPER_ITEM_FILE)
		utils.dump_json(EQUIP_DATA, utils.SUPER_EQUIP_FILE)

		for x in ['files', 'equips', 'items']:
			CACHE['parsed'][x]= list(CACHE['parsed'][x])
		utils.dump_json(CACHE, utils.SUPER_CACHE_FILE)

		return ITEM_DATA, EQUIP_DATA


	@classmethod
	def _parse_page(cls, html):
		# inits
		ret= {
			"items": [],
			"equips": [],
			"fails": []
		}
		soup= BeautifulSoup(html, 'html.parser')

		# auction still ongoing
		if not soup.find(lambda tag: tag.name== "div" and tag.get_text() == "Auction ended"):
			return None

		# parse rows
		tables= soup.find_all("tbody")
		for tbl in tables:
			for row in tbl.find_all("tr"):
				# check if item or equip table
				try:
					if "Mat" in row.find("td").get_text():
						result= cls._parse_item_row(row)
						if result: ret["items"].append(result)
					else:
						result= cls._parse_equip_row(row)
						if result: ret["equips"].append(result)
				except SuperParseFail as e:
					ret['fails'].append(f"{e.stat} - {str(e)}")

		return ret


	@classmethod
	def _parse_item_row(cls, tr):
		# inits
		cols= tr.find_all("td")


		# get string vals
		id_= cols[0].get_text()
		quant,name= cls.ITEM_REGEX['quant_name'].fullmatch(cols[1].get_text()).group(1,2)
		seller= cols[5].get_text()

		match= cls.ITEM_REGEX['price_buyer'].fullmatch(cols[3].get_text())
		if match:
			price,buyer= match.group(1,2)
		else:
			return None


		# parse vals
		price= price_to_int(price)
		if quant is None: # "Pony figurine set" is a thing: itemlist194262
			quant= 1
		else:
			quant= int(quant)


		# return
		return {
			"name": name,
			"quantity": quant,
			"price": price,
			"unit_price": price // quant,
			"seller": seller,
			"buyer": buyer,
			"id": id_
		}

	@classmethod
	def _parse_equip_row(cls, tr):
		# inits
		cols= tr.find_all("td")


		# get string vals
		id_= cols[0].get_text()
		name= cols[1].get_text()
		link= cols[1].find('a')['href']
		seller= cols[5].get_text()

		match= cls.EQUIP_REGEX['level_stats'].fullmatch(cols[2].get_text()) # fails for 5-in-1, see: hea04 https://reasoningtheory.net/itemlist215252
		if match:
			level,stats= match.group(1,2)

			if stats is None:
				stats= ""
			else:
				stats= cls.EQUIP_REGEX['stat_cleaning'].sub("EDB", stats)
		else:
			raise SuperParseFail("level_stats", tr)

		match= cls.EQUIP_REGEX['price_buyer'].fullmatch(cols[3].get_text())
		if match:
			price,buyer= match.group(1,2)
		else:
			return None


		# parse vals
		if level == "Unassigned":
			level= 0
		elif level == "n/a":
			level= -1
		else:
			level= int(level)

		price= price_to_int(price)


		# return
		return {
			"name": name,
			"price": price,
			"stats": stats,
			"level": level,
			"seller": seller,
			"buyer": buyer,
			"link": link,
			"id": id_
		}

	# MM-DD-YY --> epoch timestamp
	@staticmethod
	def _to_epoch(date):
		s= [int(x) for x in date.split("-")]
		return to_epoch(s[2], s[0], s[1])


class SuperParseFail(Exception):
	def __init__(self, stat, tr):
		self.stat= stat
		self.tr= tr

	def __str__(self):
		return " | ".join(x.get_text() for x in self.tr)


if __name__ == "__main__":
	async def scrape_and_parse():
		await SuperScraper.scrape()
		await SuperScraper.parse()

	asyncio.get_event_loop().run_until_complete(scrape_and_parse())