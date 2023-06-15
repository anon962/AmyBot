from datetime import datetime
import json
import runpy

async def lotto_hotfix(message):
	import utils, asyncio

	if message.content.startswith("!lwinners") or message.content.startswith("!lwin") or message.content.startswith("!luser"):
		split= message.content.lower().split()[1:]
		if not split: return
		if message.guild and message.channel.id != 634255830094446592 and message.guild.id == 603053441157169155: return

		result,stats = await searchLottoWinners(" ".join(split))
		if not result: return await message.channel.send("No results found.")

		statLst= []
		for key in stats: statLst.append([key] + stats[key])

		print(statLst)
		text= "```\n" + pprint(statLst, headers= ["Item", "Total Count", "Wins"]) + "```\n"
		text+= "```py\n"
		text+= pprint(result, headers=["Prize", "Grand Prize", "Ticket Pool", "# Lotto / MM-YY"])
		text+= "\n```"
		print(text)

		text = breakMessage(text, codeblock=True, lang="py")
		lim = 2
		if message.guild:
			tx = text[:lim]
		else:
			tx = text

		for msg in tx:
			# print("msg",msg)
			if not msg: continue
			await message.channel.send(msg)
			await asyncio.sleep(.5)

		if message.guild and len(text) > lim: await message.channel.send(f"{len(text) - lim} additional pages omitted.")


	if message.content.startswith("!litem") or message.content.startswith("!lit"):
		split= message.content.lower().split()[1:]
		if not split: return
		if message.guild and message.channel.id != 634255830094446592 and message.guild.id == 603053441157169155: return

		result = await searchLottoItems(" ".join(split))
		if not result: return await message.channel.send("No results found.")

		text= "```py\n"
		text+= pprint(result, headers=["Prize", "Winner", "Ticket Pool", "# Lotto / Date"])
		text+= "\n```"
		print(text)

		text = breakMessage(text, codeblock=True, lang="py")
		lim = 1
		if message.guild:
			tx = text[:lim]
		else:
			tx = text

		for msg in tx:
			# print("msg",msg)
			if not msg: continue
			await message.channel.send(msg)
			await asyncio.sleep(.5)

		if message.guild and len(text) > lim: await message.channel.send(f"{len(text) - lim} additional pages omitted.")

async def lotto_dl(session):
	import os,json,time,utils
	from utils.scraper_utils import get_session, get_html

	LOGIN_FAIL_STRING= "You must be logged on to visit the HentaiVerse."

	wlink="https://hentaiverse.org/?s=Bazaar&ss=lt&lottery="
	alink="https://hentaiverse.org/?s=Bazaar&ss=la&lottery="
	links={wlink:"w", alink:"a"}

	start=99999

	CONFIG= utils.load_bot_config()


	# session= get_session()
	await session.get(CONFIG['hv_login_link'])

	for link in links:
		for i in range(1,start):
			filename = utils.CACHE_DIR + "lottery/" + links[link] + "".join(["0"] * (5 - len(str(i)))) + str(i) + ".html"

			if os.path.exists(filename): continue
			if not os.path.exists(os.path.dirname(filename)):
				os.makedirs(os.path.dirname(filename))

			l = link + str(i)
			html= await get_html(l, session)
			if "Winner:" not in html: break
			with open(filename, "w", encoding="utf-8") as file:
				print(links[link], l)
				file.write(str(html))

			time.sleep(.66)

async def lotto_parse():
	import glob,json,os,utils
	from bs4 import BeautifulSoup

	data= utils.load_json_with_default(utils.DATA_DIR + "lotto_data.json", default={"w":{}, "a":{}})

	files= reversed(glob.glob(utils.CACHE_DIR + "lottery/*.html"))
	for file in files:
		baseName= os.path.basename(file).replace(".html", "")

		num= int(baseName[1:])
		type= baseName[0]
		if str(num) in data[type]: continue

		#print(file)

		html= open(file, encoding="utf-8").read()
		#if "do not want" in str(html).lower(): continue

		soup = BeautifulSoup(html, 'html.parser')

		left= soup.find("div", {"id": "leftpane"})

		date= [x.text for x in left.find_all("div") if "Grand Prize" in x.text][0].split()
		date= [date[3],date[4][:-1][:-2],date[4][:-1][-2:]]

		eq= left.find("div", {"id": "lottery_eqname"}).text

		prizePane= [x for x in left.find_all("div") if "font-family:verdana" in str(x) and "Prize:" in str(x)]

		prizes = []
		winners = []
		for x in prizePane[0].find_all("div"):
			if "Winner: " in x.text:
				if "Equip Winner: " in x.text:
					winners.append(x.text.replace("Equip Winner: ",""))
				elif "Core Winner: " in x.text:
					# Core does not have a separate "Prize <div>" - add manually
					prizes.append(['1', 'Core'])
					winners.append(x.text.replace("Core Winner: ",""))
				else:
					winners.append(x.text.replace("Winner: ",""))
			if "Prize: " in x.text:
				prizes.append(x.text.split()[2:])

		prizes= [[int(x[0]), " ".join(x[1:])] for x in prizes]

		right= soup.find("div", {"id": "rightpane"}).find_all("div")
		tix= [x.text for x in right if "You hold" in x.text]
		tix= tix[0].split()[4]

		print(num,date,eq,winners,prizes, tix)
		if winners: data[type][num]= {
			"date": date,
			"eq": eq,
			"winners": winners,
			"prizes": prizes,
			"tickets": tix
		}


	with open(utils.DATA_DIR + "lotto_data.json", "w") as file:
		file.write(json.dumps(data,indent=2))

async def searchLottoWinners(winner):
	import utils
	from utils.scraper_utils import get_session

	lst= []
	stats= {
		"Equips": [0,0],
		"Core": [0,0],
		"Chaos Token": [0,0],
		"Chaos Tokens": [0,0],
		"Golden Lottery Ticket": [0,0],
		"Golden Lottery Tickets": [0,0],
		"Caffeinated Candy": [0,0],
		"Caffeinated Candies": [0,0]
	}

	data= utils.load_json_with_default(utils.DATA_DIR + "lotto_data.json", default={"w":{}, "a":{}})

	numW= max([int(x) for x in data["w"].keys()]) if data['w'] else 0
	numA= max([int(x) for x in data["a"].keys()]) if data['a'] else 0
	if weaponLotteryOutdated(numW) or armorLotteryOutdated(numA):
		print("OUTDATED", numW, numA)
		await lotto_dl(get_session())
		await lotto_parse()

	data= utils.load_json_with_default(utils.DATA_DIR + "lotto_data.json", default={"w":{}, "a":{}})

	for type in data:
		ks= list(data[type].keys())
		ks.sort(key= lambda x: -int(x))

		for num in ks:
			ent = data[type][num]

			if winner.lower() in [x.lower() for x in ent["winners"]]:
				date= f"#{num} / {ent['date'][0]} {ent['date'][1]}{ent['date'][2]}"

				lower= [x.lower() for x in ent['winners']]
				place= lower.index(winner)
				if place == 0:
					prize= ent["eq"].replace("Peerless ","")
					stats["Equips"][0]+= 1
					stats["Equips"][1]+= 1
					gp= ""
				else:
					n= ent["prizes"][place-1][0]
					nm= ent["prizes"][place-1][1]
					prize= str(n) + " " + nm
					stats[nm][0]+= n
					stats[nm][1]+= 1
					gp= ent["eq"].replace("Peerless ","")

				tix= formatPrice(ent["tickets"])

				#print(date, prize, tix)
				lst.append([prize,gp,tix,date])

	merge= lambda x,y: [str(x[0]+y[0]), str(x[1]+y[1])]

	stats["Chaos Tokens"]= merge(stats["Chaos Tokens"], stats["Chaos Token"])
	del stats["Chaos Token"]

	stats["Golden Lottery Tickets"] = merge(stats["Golden Lottery Tickets"], stats["Golden Lottery Ticket"])
	del stats["Golden Lottery Ticket"]

	stats["Caffeinated Candies"] = merge(stats["Caffeinated Candy"], stats["Caffeinated Candies"])
	del stats["Caffeinated Candy"]

	stats["Equips"][0]= str(stats["Equips"][0])
	stats["Equips"][1]= str(stats["Equips"][1])

	stats["Core"] = [str(x) for x in stats["Core"]]
	return lst,stats


async def searchLottoItems(item):
	import utils
	from utils.scraper_utils import get_session

	lst = []
	split= item.split()

	data= utils.load_json_with_default(utils.DATA_DIR + "lotto_data.json", default={"w":{}, "a":{}})

	numW= max([int(x) for x in data["w"].keys()]) if data['w'] else 0
	numA= max([int(x) for x in data["a"].keys()]) if data['a'] else 0
	if weaponLotteryOutdated(numW) or armorLotteryOutdated(numA):
		print("OUTDATED", numW, numA)
		await lotto_dl(get_session())
		await lotto_parse()

	data= utils.load_json_with_default(utils.DATA_DIR + "lotto_data.json", default={"w":{}, "a":{}})

	for type in data:
		ks= list(data[type].keys())
		ks.sort(key= lambda x: -int(x))

		for num in ks:
			ent= data[type][num]

			if all([x in ent["eq"].lower() for x in split]):
				date = f"#{num} / {ent['date'][0]} {ent['date'][1]}{ent['date'][2]}"
				try: winner= ent['winners'][0]
				except Exception as e: print(num,type,ent)
				tix = formatPrice(ent["tickets"])
				item= ent["eq"]

				# print(date, winner, tix)
				lst.append([item, winner, tix, date])

	return lst


def weaponLotteryOutdated(lottoNum, threshold=2):
	firstLottery = datetime.strptime("September 14 13", "%B %d %y")
	if lottoNum + threshold < abs((datetime.today() - firstLottery).days):
		return True
	return False

def armorLotteryOutdated(lottoNum, threshold=2):
	firstLottery = datetime.strptime("March 30 14", "%B %d %y")
	if lottoNum + threshold < abs((datetime.today() - firstLottery).days):
		return True
	return False

def formatPrice(x, numDec=0):
	sx= str(x)

	if len(sx) > 6: sx= sx[:-6] + "." + sx[-6:][:numDec] + "m"
	elif len(sx) > 3: sx = sx[:-3] + "." + sx[-3:][:numDec] + "k"

	if "." in sx:
		while sx[-2] == '0': sx= sx[:-2] + sx[-1]
		if sx[-2]== ".": sx =sx[:-2] + sx[-1]

	return sx

def breakMessage(msg, codeblock=True, lang=""):
	text= []

	if codeblock: msg= msg.replace("```" + lang,"").replace("```","")

	splt = msg.split("\n")
	txt= ""
	while len("\n".join(splt)) > 1850:
		if codeblock: txt= "```" + lang + "\n"
		else: txt= ""

		while len(txt) < 1850:
			txt+= splt[0] + "\n"
			splt= splt[1:]

		if codeblock: txt+= "```"
		else: txt+= ""

		if len(txt) > 3: text.append(txt)

	if codeblock: text.append("```" + lang + "\n" + "\n".join(splt) + "```")
	else: text.append("\n".join(splt))

	return text


def pprint(lst, div="|", spc=1, headers=None, quoteWrap=False, links=None):
	num = len(lst[0])
	widths = [0] * (num)

	for i in range(num):
		widths[i] = max([len(str(x[i])) for x in lst])
		if headers: widths[i]= max(widths[i], len(headers[i]))

		widths[i]= widths[i] + 1 + spc

	htext = ""
	if headers:
		line= ""
		for j in range(len(headers)):
			padding= widths[j]-len(headers[j])

			line+= headers[j] + " ".join([""]*padding) + div + " "
		if quoteWrap: htext+= f"`{line}`\n"
		else: htext+= f"{line}\n"

	text = ""
	for i in range(len(lst)):
		line= ""
		for j in range(num):
			padding= widths[j]-len(lst[i][j])

			line+= lst[i][j] + " ".join([""]*padding) + div + " "

		if quoteWrap: text+= f"`{line}`\n"
		else: text+= f"{line}\n"

	text= text[:-1]

	m= max([len(x) for x in text.split("\n")])
	if quoteWrap: m=m-2

	div= "".join(["-"]*m)
	if quoteWrap: div= f"`{div}`\n"
	else: div+= "\n"

	if quoteWrap and links:
		split= text.split("\n")
		split= [split[i] + links[i] for i in range(len(split))]
		text= "\n".join(split)

	return htext + div + text
