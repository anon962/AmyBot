from .scrapers.equip_scraper import EquipScraper
import utils, copy

# Parses equip link for stats and converts to percentile values.
class EquipParser:
	def __init__(self):
		self.RANGES= utils.load_json_with_default(utils.RANGES_FILE, default=False)

	# Gets min / max values for each equip stat
	def get_ranges(self, equip_name, only_legendary=False):
		reps= ["of ", "Of ", "the ", "The ", "Shield ", "Staff "]
		for x in reps: equip_name= equip_name.replace(x, "")  # eg Peerless Chaged Phase Cap of Surtr --> Peerless Chaged Phase Cap Surtr

		spl= equip_name.split() # ['Peerless', 'Charged', 'Phase', 'Cap', 'Surtr']
		quality= spl.pop(0) # Peerless

		if len(spl) < 2:
			raise ValueError

		types= ["oak", "redwood", "willow", "katalox",
				"axe", "club", "rapier", "shortsword", "wakizashi", "estoc", "longsword", "mace", "katana",
				"cotton","phase","leather","shade","power","plate",
				"buckler","kite","force"]

		# check if type or prefix comes next
		if quality.lower() not in ["peerless", "legendary"]:
			if spl[0].lower() in types:
				prefix= ""
			else:
				prefix= spl.pop(0) # Charged
		else:
			prefix= spl.pop(0) # Charged


		if only_legendary:
			quality= "Legendary"

		suffix= spl.pop(-1) # Surtr

		data= copy.deepcopy(self.RANGES)
		for x in spl:
			if x not in data:
				raise ValueError(f"[{equip_name}] (\"{x}\") not found in range data.")
			data= data[x]
		data= data[quality]

		for stat in data:
			if stat == "lastUpdate": continue

			tmp= None
			for opt in data[stat]:
				reqs= opt.split(" | ")

				if reqs[0] == "all": pass
				elif reqs[0] == prefix: pass
				elif reqs[0].startswith("not!") and prefix not in reqs[0].split("!")[1:]: pass
				else: continue

				if reqs[1] == "all": pass
				elif reqs[1] == suffix: pass
				elif reqs[1].startswith("not!") and suffix not in reqs[1].split("!")[1:]: pass
				else: continue

				tmp= data[stat][opt]

			assert tmp is not None, "failed prefix/suffix checks,\t" + equip_name
			data[stat]= tmp

		return data

	def raw_stat_to_percentile(self, name, raw_stats, only_legendary=False):
		ret= {}
		eq_ranges= self.get_ranges(name, only_legendary=only_legendary)

		for st in raw_stats:
			st_r= st
			if st_r not in eq_ranges: st_r= st.replace(" MIT", "").replace(" PROF", "")
			if st_r not in eq_ranges or eq_ranges[st_r]['max'] == 0:
				print(f"STAT WARNING: [{st_r}] is an invalid stat for [{name}]")
				continue

			numer= raw_stats[st] - eq_ranges[st_r]['min']
			denom= (eq_ranges[st_r]['max'] - eq_ranges[st_r]['min'])
			ret[st]= 100*numer/denom

		return ret

	@staticmethod # convienence function
	def update_ranges():
		EquipScraper.scrape_ranges()

	def reload_ranges(self):
		self.RANGES= utils.load_json_with_default(utils.RANGES_FILE, default=False)