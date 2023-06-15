async def trend_hotfix(message):
	import discord, json

	if message.content.startswith("!tre"):
		trend_help= """\
		__Description__: Plots equip prices by percentile value 
		__Usage__: `equip_name` `keywords`
		__Keywords__:
		\tdate: Range of years (eg `2017-2019`)
		\tmin: Minimum price (eg `min100k`)
		\tmax: Minimum price (eg `max2m`)
		\tgrouping: Data grouping (eg `stat` / `prefix` / `suffix` / `slot` / `type` / `name`)
		\tbin: bin size (eg `bin5` rounds 43% equips to 45%)
		"""
		split= message.content.split()[1:]
		if split == []:
			await message.channel.send(trend_help)
			return

		params,ignored= parseTrendCommand(split)
		if params is None:
			await message.channel.send(f"Error. Invalid input.\n{trend_help}")
			return

		result= generateTrendPlot(params)

		print(result, params)
		if result['outPath'] is None:
			for x in params:
				if type(params[x]) is list:
					if len(params[x]) > 3: params[x]= params[x][:2] + ["..."] + params[x][-1:]
					params[x]= f"[{', '.join([str(y) for y in params[x]])}]"
			await message.channel.send(f"No results found. Search parameters:\n```yaml\n{json.dumps(params,indent=2)}```")
			return

		import collections
		counts= collections.Counter(result['data']['groups'])
		counts= [f"{x} ({counts[x]})" for x in counts.keys()]
		if len(counts) > 4: counts= counts[:2] + ["..."] + counts[-2:]
		tmp= "\n\t"
		msg= f"data points ({len(result['data']['inputs'])}): \n\t`{f'`, {tmp}`'.join(counts)}`"

		msg+= f"""
grouped by: `{params['grouping']}`
bin size: `{params['bin']}%`
ignored (no stats): `{result['warnings']['no_stat']}`
"""
		if ignored: msg+= f"\nWords ignored: [`{'`, `'.join(ignored)}`]"
		if result['warnings']['bad_date']: msg+= f"ignored (date): `{result['warnings']['bad_date']}`"
		if result['warnings']['bad_price']: msg+= f"ignored (price): `{result['warnings']['bad_price']}`"
		await message.channel.send(content=msg, file=discord.File(result['outPath']))






def getDamage(turn):
	dmg= []
	for action in turn.actions:
		if action.subtype != "Offensive": continue

		for target in action.targets:
			dmg+= [int(target['damage'])]

	return dmg

def getCasts(turn):
	casts= []
	for action in turn.actions:
		if action.subtype != "Offensive": continue

		for target in action.targets:
			casts+= [action.name]

	return casts

def getAvg(dmgList):
	window= dmgList[-20:]
	return round(sum(window) / 1000 / max(len(window),1), None)

def getTotal(dmgList):
	window= dmgList[-20:]
	return sum(window) / 10000

def getSpellDmg(name, dmgList, castList):
	dmgs=[]
	for n,dmg in zip(castList, dmgList):
		if n == name: dmgs.append(dmg)

	return getAvg(dmgs)






from typing import List, Tuple
import json, itertools, pandas, re, seaborn, matplotlib.pyplot as plt, os, collections, math

def toint(x):
	ix = (x.lower().replace("k", "000").replace("m", "000000"))
	if "." in x:
		numDec = len(str(x).replace("k","").replace("m","").split(".")[1])
		ix = ix[:-numDec].replace(".", "")
	if not ix: ix = 0
	return int(ix)

exacts= ["Force", "Shield", "Plate", ]

dct= {
	"suffix": [
		"Surtr", "Freyr", "Niflheim", "Mjolnir", "Fenrir", "Heimdall",
		"Destruction", "Focus", "the Elementalist", "the Heaven-sent", "the Demon-fiend", "the Earth-walker", "the Curse-weaver",
		"Slaughter", "Balance", "the Battlecaster", "the Nimble", "the Vampire", "the Illithid", "the Banshee", "Swiftness",

		"Protection", "Warding", "Dampening", "Stoneskin", "Deflection",
		"the Battlecaster", "Barrier", "the Nimble",
		"the Shadowdancer", "the Arcanist", "the Fleet", "Negation",
		"Slaughter", "Balance"
	],

	"prefix": [
		"Charged", "Radiant", "Mystic", "Frugal", # Cotton
		"Agile", "Reinforced", "Savage", # Light
		"Shielding", "Mithril", "Savage", # Heavy
		"Agile", "Reinforced", "Mithril", # Shield

		"Onyx", "Cobalt", "Jade", "Ruby", "Zircon", "Amber", # Elem
		"Ethereal", "Fiery", "Arctic", "Shocking", "Tempestuous", "Hallowed", "Demonic",
	],

	"type": [
		"Cotton", "Phase",
		"Leather", "Shade",
		"Plate", "Power",

		"Axe", "Club", "Rapier", "Shortsword", "Wakizashi", "Estoc", "Longsword", "Mace", "Katana",
		"Oak", "Redwood", "Willow", "Katalox",
		"Force", "Kite", "Buckler"
	],

	"slot": [
		"Pants", "Gloves", "Robe", "Cap", "Shoes",
		"Helmet", "Breastplate", "Gauntlets", "Leggings", "Cuirass", "Armor", "Sabatons", "Greaves", "Boots",

		"Staff", "Shield", ""
	],

	"quality": [
		"Peerless",
		"Legendary",
		"Magnificent",
	],

	"year": [str(x) for x in range(2016,2030)],

	"stat": [],
}

def parseTrendCommand(split: List[str]):
	"""Returns:
	 	ret: dictionary of equip search parameters
	 	ignored: list of unused words from split
	"""

	matched= set()
	ret= {
		"quality": [],
		"prefix": [],
		"slot": [],
		"suffix": [],
		"type": [],
		"year": [],

		"grouping": "suffix",
		"min": 0,
		"max": 10**10,
		"bin": 5,
		"stat": [],
		"log": False
	}
	groupings= ["prefix", "suffix", "slot", "type", "name"]

	for word in split:
		try: # Check min
			if not word.startswith("min"): raise ValueError
			ret['min']= toint(word.replace("min",""))
			matched.add(word)
			continue
		except ValueError: pass

		try: # Check max
			if not word.startswith("max"): raise ValueError
			ret['max']= toint(word.replace("max",""))
			matched.add(word)
			continue
		except ValueError: pass

		try: # Check bin size
			if not word.startswith("bin"): raise ValueError
			ret['bin']= toint(word.replace("bin",""))
			matched.add(word)
			continue
		except ValueError: pass

		try: # Check log scale
			if word.lower().startswith("log"):
				w= word.replace("log","")
				ret['log']= toint(w) if not w=="" else 2
				matched.add(word)
		except ValueError: pass

		try: # Check date
			if word.lower().startswith("date") or word.lower().startswith("20"):
				w= word.replace("date","")
				start,end= w.split("-")
				start,end= int(start),int(end)
				ret['year']+= [str(x) for x in range(start,end+1)]
				matched.add(word)
		except ValueError: pass

		# Check for grouping word
		flag= False
		for x in groupings:
			if word.startswith(x[:3]):
				ret["grouping"]= x
				flag= True
				matched.add(word)
				break
		if flag: continue

		# Check for equip-naming words
		for cat in dct:
			matches= []

			for x in dct[cat]:
				if word.lower() in [x.lower() for x in exacts]:
					if word.lower() == x.lower():
						matches.append(x)
						matched.add(word)
				elif word.lower() in x.lower():
					matches.append(x)
					matched.add(word)

			ret[cat]+= matches

	# If one year, assume all future years too
	if len(ret['year']) == 1:
		ret['year']+= [str(x) for x in range(int(ret['year'][0]), int(ret['year'][0])+10)]

	if ret['quality'] == []:
		ret['quality'].append("Legendary")

	# Use all options for categories without a match
	for x in ret:
		if ret[x] == []:
			ret[x]= dct[x]

	if not matched: return None, None

	# Return search parameters and list of unused words from query
	ignored= [x for x in split if x not in matched]
	return ret, ignored

indexMap= {"quality": 0, "prefix": 1, "type": 2, "slot": 3, "suffix": 4}
def getStatName(eq: Tuple[str]):
	if eq[indexMap['slot']] == 'Staff': return "mdb"
	elif eq[indexMap['suffix']] in ["the Elementalist", "the Heaven-sent", "the Demon-fiend", "the Earth-walker", "the Curse-weaver"]: return "prof"
	elif eq[indexMap['type']] in ["Cotton", "Phase"]: return "edb"
	elif eq[indexMap['type']] in ["Axe", "Club", "Rapier", "Shortsword", "Wakizashi", "Estoc", "Longsword", "Mace", "Katana", "Shade", "Power"]: return "adb"
	elif eq[indexMap['type']] in ["Force", "Kite", "Buckler"]: return "blk"
	else: return "prof"

def generateTrendPlot(searchParams: dict, outPath="./tmp.png", showPlot=False):
	import utils
	warnings= {"no_stat": 0, "no_name": 0, "bad_date": 0, "bad_price": 0}

	data= json.load(open(utils.DATA_DIR + "trend_data.json"))
	dct= { "inputs": [], "outputs": [], "groups": [] }
	sp= searchParams

	for x in itertools.product(sp['quality'], sp['prefix'], sp['type'], sp['slot'], sp['suffix']):
		eqName= f"{x[0]} {x[1]} {x[2]} {x[3]} of {x[4]}".replace("  "," ")

		if eqName not in data:
			warnings["no_name"]+= 1
			continue

		eqList= data[eqName]
		statName= getStatName(x)
		if searchParams['grouping'] == 'name': group= " ".join(x).replace("  ","")
		else: group= x[indexMap[sp['grouping']]]

		for y in eqList:
			stat= re.search(rf"{statName} (\d+)%", y['stats'], re.IGNORECASE)
			if not stat:
				warnings['no_stat']+= 1
				continue
			else: searchParams['stat'].append(statName)
			if str(y['date'][2]) not in searchParams['year']:
				warnings['bad_date']+= 1
				continue

			stat= int(stat.groups()[0])
			stat= round(stat/sp['bin'])*sp['bin']
			price= int(y['price']) / 10**6

			if not (searchParams['min'] <= price <= searchParams['max']):
				warnings['bad_price']+= 1
				continue

			dct["inputs"].append(stat)
			dct["outputs"].append(price)
			dct['groups'].append(f"{group} ({statName})")

	if dct['outputs'] == []: return {"data": None, "warnings": warnings, "outPath": None}

	dataFrame= pandas.DataFrame(dct)
	with seaborn.axes_style("whitegrid"):
		ax= seaborn.relplot(x="inputs", y="outputs", hue="groups", kind="line", data=dataFrame,# ci=None,
							# style="type", dashes=[(1,1), (2,2), (3,3), (7,7)], palette={"red":"r", "green":"g", "blue":"b", "linear default": "gray"}
							)

		ax.set(
			# ylim=(sp['min']/10**6, min(max(dct['outputs']), sp['max']/10**6)),
			xlim=(0,105),
			xlabel="Percentile",
			ylabel="Price (millions)"
		)
		ax._legend.remove()

		if searchParams['log']: plt.yscale('log', basey=searchParams['log'])
		plt.gcf().set_size_inches(9,6)
		plt.legend(bbox_to_anchor=(0,1), loc="upper left")
		if showPlot: plt.show()
		plt.savefig(outPath)

	return {"data": dct, "warnings": warnings, "outPath": os.path.abspath(outPath)}

# def generateTrendPlot(searchParams: dict, outPath="./tmp.png", showPlot=False):
# 	print('starting trend search')
#
# 	import utils, datetime
# 	from utils.parse_utils import contains
#
# 	warnings= {"no_stat": 0, "no_name": 0, "bad_date": 0, "bad_price": 0}
#
# 	data= utils.load_json_with_default(utils.AUCTION_FILE, default=False)
# 	dct= { "inputs": [], "outputs": [], "groups": [] }
# 	sp= searchParams
#
# 	valid_names= list(itertools.product(sp['quality'], sp['prefix'], sp['type'], sp['slot'], sp['suffix']))
# 	# valid_names= [' '.join(x) for x in valid_names]
#
# 	matching_eqs= [x for x in data if any(contains(x['name'], ' '.join(y)) for y in valid_names)]
#
# 	print('done matching')
# 	for y in matching_eqs:
# 		for x in valid_names:
# 			if contains(y['name'], x):
# 				tup= x
# 				break
# 		else:
# 			print('trend fail', y, sp)
# 			continue
#
# 		statName= getStatName(tup)
# 		if searchParams['grouping'] == 'name':
# 			group= " ".join(tup).replace("  ","")
# 		else:
# 			group= tup[indexMap[sp['grouping']]]
#
# 		stat= re.search(rf"{statName} (\d+)%", y['stats'], re.IGNORECASE)
# 		if not stat:
# 			warnings['no_stat']+= 1
# 			continue
# 		else: searchParams['stat'].append(statName)
#
# 		yr= datetime.datetime.fromtimestamp(y['time'])
# 		yr= yr.year
# 		if str(yr) not in sp['year']:
# 			warnings['bad_date']+= 1
# 			continue
#
# 		stat= int(stat.groups()[0])
# 		stat= round(stat/sp['bin'])*sp['bin']
# 		price= int(y['price']) / 10**6
#
# 		if not (searchParams['min'] <= price <= searchParams['max']):
# 			warnings['bad_price']+= 1
# 			continue
#
# 		dct["inputs"].append(stat)
# 		dct["outputs"].append(price)
# 		dct['groups'].append(f"{group} ({statName})")
#
# 	#
# 	# for x in itertools.product(sp['quality'], sp['prefix'], sp['type'], sp['slot'], sp['suffix']):
# 	# 	eqName= f"{x[0]} {x[1]} {x[2]} {x[3]} of {x[4]}".replace("  "," ")
# 	#
# 	# 	# if eqName not in data:
# 	# 	# 	warnings["no_name"]+= 1
# 	# 	# 	continue
# 	#
# 	# 	eqList= [x for x in data if contains(to_search=x['name'], to_find=eqName)]
# 	# 	statName= getStatName(x)
# 	# 	if searchParams['grouping'] == 'name': group= " ".join(x).replace("  ","")
# 	# 	else: group= x[indexMap[sp['grouping']]]
# 	#
# 	# 	for y in eqList:
# 	# 		stat= re.search(rf"{statName} (\d+)%", y['stats'], re.IGNORECASE)
# 	# 		if not stat:
# 	# 			warnings['no_stat']+= 1
# 	# 			continue
# 	# 		else: searchParams['stat'].append(statName)
# 	#
# 	# 		yr= datetime.datetime.fromtimestamp(y['time'])
# 	# 		yr= yr.year
# 	# 		if str(yr) not in sp['year']:
# 	# 			warnings['bad_date']+= 1
# 	# 			continue
# 	#
# 	# 		stat= int(stat.groups()[0])
# 	# 		stat= round(stat/sp['bin'])*sp['bin']
# 	# 		price= int(y['price']) / 10**6
# 	#
# 	# 		if not (searchParams['min'] <= price <= searchParams['max']):
# 	# 			warnings['bad_price']+= 1
# 	# 			continue
# 	#
# 	# 		dct["inputs"].append(stat)
# 	# 		dct["outputs"].append(price)
# 	# 		dct['groups'].append(f"{group} ({statName})")
#
# 	if dct['outputs'] == []: return {"data": None, "warnings": warnings, "outPath": None}
#
# 	dataFrame= pandas.DataFrame(dct)
# 	with seaborn.axes_style("whitegrid"):
# 		ax= seaborn.relplot(x="inputs", y="outputs", hue="groups", kind="line", data=dataFrame,# ci=None,
# 							# style="type", dashes=[(1,1), (2,2), (3,3), (7,7)], palette={"red":"r", "green":"g", "blue":"b", "linear default": "gray"}
# 							)
#
# 		ax.set(
# 			# ylim=(sp['min']/10**6, min(max(dct['outputs']), sp['max']/10**6)),
# 			xlim=(0,105),
# 			xlabel="Percentile",
# 			ylabel="Price (millions)"
# 		)
# 		ax._legend.remove()
#
# 		if searchParams['log']: plt.yscale('log', basey=searchParams['log'])
# 		plt.gcf().set_size_inches(9,6)
# 		plt.legend(bbox_to_anchor=(0,1), loc="upper left")
# 		if showPlot: plt.show()
# 		plt.savefig(outPath)
#
# 	return {"data": dct, "warnings": warnings, "outPath": os.path.abspath(outPath)}

if __name__ == "__main__":
	msg= "elem robe prefix max3m bin15"
	sp,ig= parseTrendCommand(msg.split())
	generateTrendPlot(sp, showPlot=True)
	sp,ig= parseTrendCommand(msg.split())
	generateTrendPlot(sp, showPlot=True)