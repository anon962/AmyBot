from datetime import datetime
from discord.ext import tasks
from utils.cog_utils.data_utils import check_update_log, merge_auctions, merge_items
from classes import PartialCog, SuperScraper, MarketScraper, EquipScraper
import utils, os, glob, discord


def update_log(check_name):
	log= utils.load_json_with_default(utils.UPDATE_LOG)
	log[check_name]= datetime.now().timestamp()
	utils.dump_json(log, utils.UPDATE_LOG)

class UpdateCog(PartialCog):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, hidden=True, **kwargs)

		# self.check_market.start()
		self.check_super.start()
		self.update_ranges.start()
		self.purge_rr.start()

	# check super every sunday for equips + items
	@tasks.loop(hours=6)
	async def check_super(self):
		super_check= check_update_log("super", 24*60*60, exact_day=6)

		if super_check or not os.path.exists(utils.AUCTION_FILE):
			print("Checking super...")
			await SuperScraper.scrape()
			await SuperScraper.parse()
			await merge_auctions()
			update_log("super")
			print("Done checking super.")

	# check hvmarket for items
	@tasks.loop(hours=1)
	async def check_market(self):
		CONFIG= utils.load_bot_config()
		hvm_check= check_update_log("hvmarket", 3600*CONFIG['market_check_frequency_hours'])

		if hvm_check or not os.path.exists(utils.ITEM_FILE):
			print("Checking market...")
			await MarketScraper.scrape()
			await merge_items()
			update_log("hvmarket")
			print("Done checking market.")

	# check kedama fo... jk, her auctions discountinued
	# @tasks.loop(hours=12)
	# async def check_kedama(self):
		# kedama_check= check_update_log("kedama", 6.9*24*60*60)
		# if kedama_check:
		# 	await KedamaScraper.scrape()
		# 	KedamaScraper.parse()

	# update min/max ranges for equip stats
	@tasks.loop(hours=6)
	async def update_ranges(self):
		CONFIG= utils.load_bot_config()
		range_check= check_update_log("equip_ranges", 3600*CONFIG['equip_range_check_frequency_hours'])

		if range_check or not os.path.exists(utils.RANGES_FILE):
			print("Updating equip ranges...")
			await EquipScraper.scrape_ranges()
			update_log("equip_ranges")
			print("Done updating ranges.")

	# purge deleted reaction messages periodically
	@tasks.loop(hours=24)
	async def purge_rr(self):
		if self.purge_rr.current_loop == 0: return

		print("Purging rr logs...")
		for log_file in glob.glob(utils.REACTION_ROLE_LOG_DIR + "*.json"):
			# load log
			log= utils.load_json_with_default(log_file, default=False)

			# mark entries for purging
			ch_dels, m_dels= [], []
			for ch_id in log:
				# check channel
				channel= self.bot.get_channel(ch_id)
				if not channel:
					ch_dels.append(ch_id)

				#check message
				for m_id in log:
					try:
						await channel.fetch_message(m_id)
					except discord.NotFound:
						m_dels.append((ch_id,m_id))

			# do purging
			for tup in m_dels:
				del log[tup[0]][tup[1]]
			for ch in ch_dels:
				del log[ch]

			# save log
			utils.dump_json(log, log_file)
