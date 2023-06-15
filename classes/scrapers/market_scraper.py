from utils.parse_utils import price_to_int, to_epoch
from utils.scraper_utils import get_html, get_session
from bs4 import BeautifulSoup
import utils, aiohttp, asyncio, re, copy


class MarketScraper:
	SCRAPE_DELAY= 10
	RESULTS_PER_PAGE= 100 # fixed by site
	BASE_LINK= r"https://hvmarket.xyz/all_transactions?page="
	PAGE_INFO_REGEX= re.compile(r"\((\d+).*total\)")
	DEFAULT_CACHE= {
		"invalid": []
	}

	@classmethod
	async def scrape(cls):
		# inits
		DATA= utils.load_json_with_default(utils.MARKET_ITEM_FILE)
		CACHE= utils.load_json_with_default(utils.MARKET_CACHE_FILE, default=cls.DEFAULT_CACHE)
		CACHE['invalid']= set(CACHE['invalid'])

		target_page_number= 1
		target_index= None

		session= get_session()
		html= await get_html(cls.BASE_LINK, session)


		# Loop logic:
		# 1. add results for current page to data
		# 2. calculate target_index
		# 3. check if done
		#       (target_index >= num_results OR target_index >= a pending entry index)
		# 4. move to page containing target_index
		#       (the target index may shift off-page by the time we visit the page due to new purchases, but doesnt matter, we'll get it eventually)
		# 5. go to step 1
		while True:
			# step 1
			result= cls.get_entries(html, target_page_number)
			DATA.update(result['entries'])
			total= result['total']
			CACHE['invalid'] |= result['invalid_indices']

			# step 2
			if target_index is None:
				target_index= 1 # one-indexed from oldest
			while str(target_index) in DATA or target_index in CACHE['invalid']:
				target_index+= 1

			# step 3
			if result['pending_indices'] and target_index >= min(result['pending_indices']):
				break
			if target_index >= total:
				break

			# step 4
			target_page_number= cls.get_target_page(target_index, total)
			html= await get_html(cls.BASE_LINK + str(target_page_number), session)

			# be nice to lestion
			print(f"{(len(DATA.keys()) + len(CACHE['invalid']))} / {total}...", end="")
			await asyncio.sleep(cls.SCRAPE_DELAY)

			# intermediate save
			tmp= copy.deepcopy(CACHE)
			tmp['invalid']= list(CACHE['invalid'])
			tmp['invalid'].sort()
			utils.dump_json(tmp, utils.MARKET_CACHE_FILE)
			utils.dump_json(DATA, utils.MARKET_ITEM_FILE)

		# final save
		CACHE['invalid']= list(CACHE['invalid'])
		CACHE['invalid'].sort()
		utils.dump_json(CACHE, utils.MARKET_CACHE_FILE)
		utils.dump_json(DATA, utils.MARKET_ITEM_FILE)


	# page_number should be 1-indexed from newest
	@classmethod
	def get_entries(cls, html, page_number):
		# inits
		ret= {
			"total": None,
			"entries": {},
			"pending_indices": [],
			"invalid_indices": set([])
		}

		soup= BeautifulSoup(html, 'html.parser')
		table= soup.find(class_="results_table")
		entries= table.find_all("tr")[1:] # ignore headers

		ret['total']= cls.get_pagination_info(html)['total']
		top_entry_index= ret['total'] - (page_number-1)*cls.RESULTS_PER_PAGE # 0-indexed from oldest

		# loop rows
		for i,row in enumerate(entries):
			if row['class'] == ['paid']:
				ret['entries'][str(top_entry_index-i)]= cls.get_entry_data(row)
			elif row['class'] in [['sent'], ['unsent']]: # pending
				ret['pending_indices'].append(top_entry_index-i)
			else: # invalid (eg unpaid)
				ret['invalid_indices'].add(top_entry_index-i)

		return ret


	@staticmethod
	def get_entry_data(row):
		# shortened helper funcs
		gt= lambda x: x.get_text()
		rep= lambda x: x.replace(r"/shop_search?player_name=", "")
		pti= lambda x: price_to_int(x)

		def te(hour_minute, day_month_year): # to epoch
			s1= day_month_year.split("-")
			# s2= hour_minute.split(":")
			# return to_epoch(*(list(reversed(s1)) + s2))
			return to_epoch(*(list(reversed(s1))))

		# do parsing
		cols= row.find_all("td")
		return {
			"name": cols[0].find('a')['title'],
			"buyer": rep(cols[1].find('a')['href']),
			"price": pti(gt(cols[2])),
			"quantity": pti(gt(cols[3])),
			"unit_price": pti(gt(cols[4])),
			"seller": rep(cols[5].find('a')['href']),
			"time": te(gt(cols[6]), gt(cols[7]))
		}


	# get total results from pagination string at bottom of page
	@classmethod
	def get_pagination_info(cls, html):
		soup= BeautifulSoup(html, 'html.parser')
		page_info= soup.find(class_="pagination_info").get_text().replace("\n", " ")

		total= cls.PAGE_INFO_REGEX.search(page_info).group(1)
		return dict(total=int(total))

	# get page number (1-indexed from newest) of the target index (1-indexed from oldest)
	# oldest page may not have same number of results as RESULTS_PER_PAGE
	@classmethod
	def get_target_page(cls, index, total_results):
		index-= 1
		remainder= total_results % cls.RESULTS_PER_PAGE
		invert= cls.RESULTS_PER_PAGE - remainder

		total_pages= total_results // cls.RESULTS_PER_PAGE
		if remainder != 0: total_pages+= 1

		target_page_from_oldest= (index + invert) // cls.RESULTS_PER_PAGE # 0-indexed from oldest
		if remainder == 0:
			target_page_from_oldest-= 1

		target_page_from_newest= total_pages - target_page_from_oldest # 1-indexed from newest

		return target_page_from_newest

if __name__ == "__main__":
	asyncio.get_event_loop().run_until_complete(MarketScraper.scrape())