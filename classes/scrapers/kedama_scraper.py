from utils.parse_utils import price_to_int
from utils.scraper_utils import get_html, get_session
from bs4 import BeautifulSoup
import utils, glob, re, asyncio, os, datetime

"""
Unlike the scrapers for super / hvmarket, there's no way to tell if new results have been added without \
crawling multiple pages (ie all the pages in search result). 

On the bright side, Kedama's auctions are discontinued so scrape / parse functions should only ever have to be run once.
As such, equip / item data is built from scratch (from the cached html) each time parse() is called, \
beacuse it's silly to optimize for future updates when there won't be any.
"""

class KedamaScraper:
	DELAY= 3
	RESULTS_PER_PAGE= 25 # fixed by site
	THREAD_SEARCH= {
		"link": r"https://forums.e-hentai.org/index.php?",
		"payload": dict(forums=77,cat_forum="forum",act="Search",joinname=1,CODE="01",keywords=r"Kedama's Auction #")
	}
	THREAD_ID_REGEX= re.compile(r"showtopic=(\d+)")
	THREAD_BASE_LINK= r"https://forums.e-hentai.org/index.php?showtopic="

	_eq_regex= r"\[href=(.*)\]\[eq_name=(.*)\]" # [href=...][eq_name=Legendary...] --- not part of original, comes from elem.replace_with
	_lvl_stat_regex= r"\((?:Lv)?[\s.]*(\d+|Unassigned),?\s*(?:(.*?))?\)" # (Lv.406, EDB 65%, Agi 78%, Evd 25%)
	_seller_regex= r"\(seller:\s*(.*?)\)" # (seller: rokyroky)
	_buyer_price_regex= r"(?:(.*) (\d+.?\d*[mkc])\s*#\d+)" # magiclamp 250k #9
	EQUIP_REGEX= re.compile(r"\s*".join([_eq_regex, _lvl_stat_regex, _seller_regex, _buyer_price_regex]))

	_it_head_regex= r"\[(?:M|v|sp)(?:at)?\d+\]" # [Mat01]
	_quant_name_regex= r"(\d+)x?\s*(.*)" # 50x Binding of the Owl
	ITEM_REGEX= re.compile(r"\s*".join([_it_head_regex, _quant_name_regex, _seller_regex, _buyer_price_regex]))


	# get all threads from the WTS forum's search engine
	@classmethod
	async def scrape(cls):
		async with get_session() as session:
			# get search results page
			search_link= None
			while search_link is None:
				async with session.post(cls.THREAD_SEARCH['link'], data=cls.THREAD_SEARCH['payload']) as resp:
					soup= BeautifulSoup(await resp.text(), 'html.parser')
					tmp= soup.find(class_="redirectfoot")
					if tmp:
						search_link= tmp.find("a")['href']
					else:
						print("kedama: rate limit")
						await asyncio.sleep(30) # wait for a while if hit rate limit

			# get thread links
			await asyncio.sleep(cls.DELAY)
			html= await get_html(search_link, session); print("kedama: getting",search_link)
			soup= BeautifulSoup(html, 'html.parser')

			num_pages= soup.find(id=lambda y: y and "page-jump" in y)
			num_pages= num_pages.get_text().replace(" Pages", "")
			num_pages= int(num_pages)

			links= cls._scrape_search_page(soup)
			for i in range(1,num_pages):
				await asyncio.sleep(cls.DELAY)
				html= await get_html(search_link + f"&st={25*i}", session); print("kedama: getting",search_link + f"&st={25*i}")
				soup= BeautifulSoup(html, 'html.parser')
				links+= cls._scrape_search_page(soup)

			# save threads to file
			for x in links:
				thread_id= cls.THREAD_ID_REGEX.search(x).group(1)
				out_file= utils.KEDAMA_HTML_DIR + thread_id + ".html"

				if os.path.exists(out_file):
					continue
				else:
					await asyncio.sleep(cls.DELAY)
					html= await get_html(x, session); print("kedama: getting (no-html)",x)
					with open(out_file, "w", encoding='utf-8') as file:
						file.write(html)

	@classmethod
	def _scrape_search_page(cls, soup):
		links= soup.find_all(lambda x: x.name == "a" and "[Auction] Kedama's" in x.get_text())
		return [x['href'].replace("&hl=","") for x in links]


	# regenerate eq / item data from scratch
	@classmethod
	def parse(cls):
		ITEMS= []
		EQUIPS= []
		DEBUG= {
			"unsold": dict(equips=[], items=[]),
			"fails": dict(equips=[], items=[])
		}

		for file in glob.glob(utils.KEDAMA_HTML_DIR + "*.html"):
			# inits
			html= open(file, encoding='utf-8'); print('parsing', os.path.basename(file))
			soup= BeautifulSoup(html, 'html.parser')


			# equip sections tend to be wrapped in a font-size-10 setting.
			first_post= soup.find(class_="postcolor")
			sects= first_post.find_all(lambda x: x.name == "span" and \
												  x.get("style") and \
												 "font-size:10pt" in x.get("style"))


			# elem.get_text() wont print correctly due to bbcode formatting
			# so apply various fixes before grabbing string to parse
			lines= []
			for sct in sects:
				[y.replace_with(f"[href={y['href']}][eq_name={y.text}]") for y in sct.find_all("a")] # equip links
				[y.replace_with(f"{y.get_text()}") for y in sct.find_all("b")] # bold text
				[y.replace_with("\n") for y in sct.find_all("br")] # new lines

				lines+= [x for x in sct.get_text().split("\n") if x]

			# date (from "Aug 14 2019, 09:37")
			date= soup.find(lambda x: x.get("style") and "float: left;" in x.get("style") and x.name == "div")
			date=date.get_text().strip()
			timestamp= cls._get_epoch(date)

			# auction number (eg 146 in "[Auction] Kedama's Auction #146")
			auc_num= soup.find(class_="maintitle").find("td").get_text().strip()
			tmp= re.search(r"#([^\s]+)", auc_num)
			if tmp:
				auc_num= tmp.group(1).replace(",","").zfill(3)

			# thread link
			thread_link= cls.THREAD_BASE_LINK + os.path.basename(file).replace(".html","")

			# parse
			result= cls._parse_lines(lines)

			it= result['items']
			eq= result['equips']
			for x in it+eq:
				x['time']= timestamp
				x['auction_number']= auc_num
				x['thread']= thread_link


			EQUIPS+= eq
			ITEMS+= it

			# save failed lines for debugging
			for x in ['unsold', 'fails']:
				for y in ['items', 'equips']:
					DEBUG[x][y]+= result[x][y]


		utils.dump_json(EQUIPS, utils.KEDAMA_EQUIP_FILE)
		utils.dump_json(ITEMS, utils.KEDAMA_ITEM_FILE)
		utils.dump_json(DEBUG, utils.KEDAMA_DEBUG_FILE)

		return ITEMS,EQUIPS


	@classmethod
	def _parse_lines(cls, lines):
		ret= {
			"items": [],
			"equips": [],
			"unsold": dict(equips=[], items=[]),
			"fails": dict(equips=[], items=[])
		}

		for l in lines:
			if tmp := cls.EQUIP_REGEX.search(l):
				link,name,level,stats,seller,buyer,price= tmp.groups()

				level= cls._clean_level(level)
				price= price_to_int(price)
				if seller is None: seller= "SakiRaFubuKi"
				buyer= re.sub(r"start:[\d.]+.? ", "", buyer)

				ret['equips'].append(dict(name=name,price=price,level=level,stats=stats,seller=seller,buyer=buyer,link=link))

			elif tmp := cls.ITEM_REGEX.search(l):
				quant,name,seller,buyer,price= tmp.groups()

				quant= int(quant)
				price= price_to_int(price)
				unit_price= price // quant
				if seller is None: seller= "SakiRaFubuKi"
				buyer= re.sub(r"start:[\d+.].? ", "", buyer)

				ret['items'].append(dict(unit_price=unit_price,quantity=quant,name=name,seller=seller,buyer=buyer,price=price))

			else: # mark any unparsed lines
				is_mat= any(x in l for x in ["Mat","[M0","[M1","[sp"])
				key_name= "items" if is_mat else "equips"

				if "#" not in l:
					ret['unsold'][key_name].append(l)
				else:
					ret['fails'][key_name].append(l)

		return ret

	@staticmethod
	def _clean_level(lvl):
		if lvl.lower() == "unassigned": return 0

		try: return int(lvl)
		except ValueError: return -1

	@staticmethod
	def _get_epoch(time_string):
		MONTHS= "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

		split= time_string.strip().split(" ") # Jul 27 2020, 12:06   OR    Today, 12:58     OR     Yesterday, 23:17
		hr,min= split[-1].split(":") # 12:06

		date= datetime.datetime.today().replace(hour=int(hr),minute=int(min))
		if "Yesterday," in split[0]:
			date= date.replace(day=date.day-1)
		elif "Today" in split[0]:
			pass
		else:
			date= date.replace(year=int(split[2][:-1]), # remove comma
							   month=1+MONTHS.index(split[0]), # month string to 1-indexed int
							   day=int(split[1]))

		return date.timestamp()

if __name__ == "__main__":
	# asyncio.get_event_loop().run_until_complete(KedamaScraper.scrape())
	KedamaScraper.parse()