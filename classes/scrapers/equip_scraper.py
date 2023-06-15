from utils.scraper_utils import get_html, get_session
from bs4 import BeautifulSoup
import aiohttp, json, utils, asyncio, re, math, copy
from utils.scraper_utils import get_session

"""
For pulling the equip-stat ranges from https://reasoningtheory.net/viewranges \
as well as the raw stat values from .../equip/{ID}/(KEY) links
"""

class EquipScraper:
	DATA_LINK= "https://reasoningtheory.net/viewranges"
	LOGIN_FAIL_STRING= "You must be logged on to visit the HentaiVerse."

	# get equip ranges and save as json
	@classmethod
	async def scrape_ranges(cls):
		async with get_session() as session:
			html= await get_html(cls.DATA_LINK, session)

			soup= BeautifulSoup(html, 'html.parser')
			json_string= soup.find(lambda x: 'data-itemranges' in x.attrs)['data-itemranges']

			data= json.loads(json_string)
			utils.dump_json(data, utils.RANGES_FILE)
			return data

	@staticmethod
	async def do_hv_login(session=None):
		CONFIG= utils.load_yaml(utils.BOT_CONFIG_FILE)
		if session is None:
			session= get_session()
		await session.get(CONFIG['hv_login_link'])
		return session

	@classmethod
	async def scrape_equip(cls, link, session=None, max_tries=3, try_delay=3):
		if session is None:
			session= await cls.do_hv_login()

		# get equip page
		html= await get_html(link, session)

		tries= 1
		while cls.LOGIN_FAIL_STRING in html and tries < max_tries:
			await cls.do_hv_login(session)
			await asyncio.sleep(try_delay)
			html= await get_html(link, session)
			tries+= 1
		if cls.LOGIN_FAIL_STRING in html:
			raise Exception(f"Failed to retrieve equip page after {max_tries} tries with delay {try_delay}s: {link}")

		soup= BeautifulSoup(html, 'html.parser')

		# get name and main stats
		name, alt_name= cls._get_names(soup)
		forged_stats= cls._get_main_stats(soup.find(class_="ex"))

		# get attack damage (weapons)
		adb= soup.find(lambda x: 'class' in x.attrs and x['class'] in [["eq","et"], ["eq","es"]]).findAll(lambda x: "title" in x.attrs, recursive=False)
		if adb: forged_stats['Attack Damage']= float(adb[0]['title'].replace("Base: ", ""))

		# get special stats
		for ep in soup.findAll(class_="ep"):
			cat= ep.find("div").text
			forged_stats[cat]= cls._get_other_stats(ep)

		# get forge upgrades
		forging= {}
		tmp= soup.find("span", id="eu")
		if tmp: forging= cls._get_upgrades(tmp)

		# get iw enchants
		enchants= {}
		tmp= soup.find("span", id="ep")
		if tmp: enchants= cls._get_upgrades(tmp)

		# get IW level / PXP info for unforging purposes
		potency_info= soup.find("div", class_=["eq", "et"]).find_all("div")[1]
		potency_info= re.search(r"Potency Tier: (\d+) (.*)", potency_info.get_text()).groups()

		# unforge base values
		forged_stats= cls._clean_stat_dict(forged_stats)
		base_stats= copy.deepcopy(forged_stats)
		base_stats= cls._unforge(stats=base_stats, forging=forging, potency_info=potency_info, eq_name=name, enchants=enchants)

		# unenchant base values
		base_stats= cls._unenchant(base_stats, enchants)

		# get level and tradeable
		tmp= soup.find("div", class_=["eq", "et"]).find("div").get_text()
		tradeable= "Tradeable" in tmp
		soulbound= "Soulbound" in tmp

		m= re.search(r"Level (\d+)", tmp)
		level= int(m.group(1)) if m else 0

		# get owner
		owner= soup.find(target="_forums").get_text()

		# clean up stats and return
		return dict(
			name=name,
			alt_name=alt_name,
			stats= forged_stats,
			base_stats= base_stats,
			forging=forging,
			enchants=enchants,
			tradeable=tradeable,
			soulbound=soulbound,
			level=level,
			owner=owner
		)

	# get real equip name and custom name (if exists)
	@staticmethod
	def _get_names(soup):
		name= ""
		alt_name= None

		if soup.find("div", class_="fc4 fac fcb"):
			divs= soup.find(id="showequip").find_all("div", recursive=False)
			if "id" in divs[1].attrs: # no custom name
				name= " ".join(x.get_text() for x in soup.find_all("div", class_="fc4 fac fcb"))
			else:
				alt_name= " ".join(x.get_text() for x in soup.find_all("div", class_="fc4 fac fcb"))
				name= " ".join(x.get_text() for x in soup.find_all("div", class_="fc2 fac fcb"))
		else:
			# get name from classnames
			lines= soup.find_all(class_="fc f4b")
			for x in lines:
				tmp= x.find_all("div")[1:]
				name+= "".join( x['class'][0][-1] for x in reversed(tmp) ).replace("9", " ")

				if x != lines[-1]:
					name+= " "

			# capitalize
			ignore= ["of", "the"]
			split= name.split()
			name= []
			for x in split:
				if x not in ignore:
					x= x.capitalize()
				name.append(x)

			name= " ".join(name)


		return name,alt_name


	@staticmethod
	def _get_main_stats(div):
		ret= {}

		stat_divs= div.findAll(lambda x: "title" in x.attrs)
		for d in stat_divs:
			base= float(d['title'].replace("Base: ",""))
			name= d.find("div").text
			ret[name]= base

		return ret

	@staticmethod
	def _get_other_stats(div):
		ret= {}

		stat_divs= div.findAll(lambda x: "title" in x.attrs)
		for d in stat_divs:
			base= float(d['title'].replace("Base: ",""))
			d.span.clear();	name= d.text.replace(" +","")
			ret[name]= base

		return ret

	@staticmethod
	def _get_upgrades(span):
		ret= dict()
		for x in span.find_all("span"):
			tmp= re.search(r"([\w ]*) Lv\.(\d+)", x.get_text()) # eg "Strength Bonus Lv.17"
			if tmp:
				name,level= tmp.groups()
			else:
				name,level= x.get_text(),0 # eg "Hollowforged"

			ret[name]= int(level)

		return ret

	@staticmethod
	def _clean_stat_dict(dct):
		ret= {}
		for cat in dct:
			if type(dct[cat]) is not dict:ret[cat]= dct[cat]

			elif cat == "Primary Attributes":
				for stat in dct[cat]:
					ret[f"{stat}"]= dct[cat][stat]

			elif cat == "Damage Mitigations":
				for stat in dct[cat]:
					ret[f"{stat} MIT"]= dct[cat][stat]

			elif cat == "Spell Damage":
				for stat in dct[cat]:
					ret[f"{stat} EDB"]= dct[cat][stat]

			elif cat == "Proficiency":
				for stat in dct[cat]:
					ret[f"{stat} PROF"]= dct[cat][stat]

			else: raise ValueError(f"Unknown stat category [{cat}]")

		return ret

	# based off LPR script and wiki page: https://ehwiki.org/wiki/The_Forge#Upgrade
	@classmethod
	def _unforge(cls, eq_name, stats, forging, potency_info, enchants):
		def clean_upgrade_name(st):
			reps= {
				"Physical Damage": "Attack Damage",
				"Physical Defense": "Physical Mitigation",
				"Magical Defense": "Magical Mitigation",
				"Magical Hit Chance": "Magic Accuracy",
				"Physical Hit Chance": "Attack Accuracy",
				"Magical Crit Chance": "Magic Crit Chance",
				"Physical Crit Chance": "Attack Crit Chance",
				"Magical": "Magic",
				"Physical": "Attack",
				"Proficiency": "PROF",
				"Spell Damage": "EDB",
				" Bonus": "",
				"Mitigation": "MIT"
			}
			for x,y in reps.items():
				if x in st:
					st= st.replace(x, y)
					break
			return st

		for st,level in forging.items():
			st= clean_upgrade_name(st)
			if st == 'Attack Damage':
				coeff= 0.279575

				if 'Butcher' in enchants:
					iw_coeff= 1 + 0.02*enchants['Butcher']
				else:
					iw_coeff= 1
			elif st == 'Magic Damage':
				coeff= 0.279575

				if 'Archmage' in enchants:
					iw_coeff= 1 + 0.02*enchants['Archmage']
				else:
					iw_coeff= 1
			else:
				coeff= 0.2
				iw_coeff= 1

			if potency_info[0] == "0":
				pxp_zero= re.search(r"\((\d+\s+)/(\s+\d+)\)", potency_info[1]).group(2)
				pxp_zero= int(pxp_zero)
			else:
				pxp_zero= cls._get_pxp_zero(eq_name)

			forge_coeff= 1 + coeff*math.log( 0.1*level + 1 )
			quality_bonus= (pxp_zero-100) * (cls._get_base_multiplier(st) / 25)
			unforged_base= (stats[st] - quality_bonus) / (forge_coeff * iw_coeff) + quality_bonus

			stats[st]= unforged_base

		return stats

	@staticmethod
	def _unenchant(stats, enchants):
		key_map= dict(
			# butcher="Attack Damage", # handled in unforge
			Overpower= ("Counter-Parry",1.92),
			# archmage="Magic Damage", # handled in unforge
			Penetrator= ("Counter-Resist",4),
		)

		for x,y in key_map.items():
			if x in enchants:
				stats[y[0]]-= y[1]*enchants[x]

		return stats

	@staticmethod
	def _get_pxp_zero(eq_name):
		dct= { # average PXP0 of various equips -- from LPR script
			'axe':375, 'club':375, 'rapier':377, 'shortsword':377, 'wakizashi':378,
			'estoc':377, 'katana':375, 'longsword':375, 'mace':375,
			'katalox staff':368, 'oak staff':371, 'redwood staff':371, 'willow staff':371,
			'buckler':374, 'force shield':374, 'kite shield':374,
			'phase':377, 'cotton':377,
			'arcanist':421, 'shade':394, 'leather':393,
			'power':382, ' plate':377,
		  }
		for x in dct:
			if x.lower() in eq_name.lower():
				if "Peerless" in eq_name:
					mult= 1
				elif "Legendary" in eq_name:
					mult= 0.95
				elif "Magnificent" in eq_name:
					mult= 0.89
				else:
					mult= 0.8

				return round(mult*dct[x])
		else:
			print(f"PXP WARNING: No average PXP0 for: [{eq_name}]")
			return 0

	@staticmethod
	def _get_base_multiplier(stat_name):
		dct= {
			'Attack Damage': 0.0854,
			'Attack Crit Chance': 0.0105,
			'Attack Crit Damage': 0.01,
			'Attack Accuracy': 0.06069,
			'Attack Speed': 0.0481,
			'Magic Damage': 0.082969,
			'Magic Crit Chance': 0.0114,
			'Spell Crit Damage': 0.01,
			'Magic Accuracy': 0.0491,
			'Casting Speed': 0.0489,
			'Strength': 0.03,
			'Dexterity': 0.03,
			'Endurance': 0.03,
			'Agility': 0.03,
			'Intelligence': 0.03,
			'Wisdom': 0.03,
			'Evade Chance': 0.025,
			'Resist Chance': 0.0804,
			'Physical Mitigation': 0.021,
			'Magical Mitigation': 0.0201,
			'Block Chance': 0.0998,
			'Parry Chance': 0.0894,
			'Mana Conservation': 0.1,
			'Crushing': 0.0155,
			'Slashing': 0.0153,
			'Piercing': 0.015,
			'Burden': 0,
			'Interference': 0,
			'Elemental': 0.0306,
			'Divine': 0.0306,
			'Forbidden': 0.0306,
			'Deprecating': 0.0306,
			'Supportive': 0.0306,
			'Holy EDB': 0.0804,
			'Dark EDB': 0.0804,
			'Wind EDB': 0.0804,
			'Elec EDB': 0.0804,
			'Cold EDB': 0.0804,
			'Fire EDB': 0.0804,
			'Holy MIT': 0.1,
			'Dark MIT': 0.1,
			'Wind MIT': 0.1,
			'Elec MIT': 0.1,
			'Cold MIT': 0.1,
			'Fire MIT': 0.1,
			'Counter-Resist': 0.1,
		}

		for x in dct:
			if x.lower() in stat_name.lower():
				return dct[x]
		else:
			print(f"BASE_MULT WARNING: No base multiplier for: [{stat_name}]")
			return 1
