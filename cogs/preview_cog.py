from discord.ext import commands
from classes import PartialCog, PartialCommand
from classes.errors import PermissionError

from utils.scraper_utils import get_session
from utils.perm_utils import check_perms
from utils.cog_utils import preview_utils
from utils.pprint_utils import get_pages

import time, re, discord, traceback, utils


# @todo: max previews per message
# Generate previews for certain links
class PreviewCog(PartialCog, name="Preview"):
	_excl= r"(!+)?[\S]*" # check for ! prefix
	_b1= r"(<.*)?" # check for < prefix
	_b2= r"(.*>)?" # check for > suffix
	LINK_REGEX= dict(
		equip= [
			rf"{_b1}{_excl}hentaiverse\.org/(isekai/)?equip/([A-Za-z\d]+)/([A-Za-z\d]+){_b2}", # http://hentaiverse.org/equip/123487856/579b582136
			rf"{_b1}{_excl}(isekai_never/)?eid=([A-Za-z\d]+)&key=([A-Za-z\d]+){_b2}" # old style -- http://hentaiverse.org/pages/showequip.php?eid=123487856&key=579b582136
		],
		thread= [
			rf"{_b1}{_excl}[\S]*e-hentai.*showtopic=(\d+)(?!.*&(?:p|pid)=\d+){_b2}" # https://forums.e-hentai.org/index.php?showtopic=236519
		],
		comment= [
			rf"{_b1}{_excl}e-hentai.*showtopic=(\d+).*&(?:p|pid)=(\d+){_b2}" # https://forums.e-hentai.org/index.php?s=&showtopic=204369&view=findpost&p=4816189
		],
		bounty= [
			rf"{_b1}{_excl}e-hentai.*?bid=(\d+){_b2}" # https://e-hentai.org/bounty.php?bid=21180
		],
	)


	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.session= get_session()
		self.last_sent= 0


	# Scan each message for a supported link
	@commands.Cog.listener()
	async def on_message(self, message):
		if message.author.bot:
			return

		ctx= await self.bot.get_context(message)
		ctx.__dict__['command']= self._preview
		ctx.__dict__['cog']= self

		try: check_perms(ctx)
		except PermissionError:	return

		for x in [self.scan_equip, self.scan_bounty, self.scan_thread, self.scan_comment]:
			result= await x(ctx)
			if result:
				self.last_sent= time.time()


	async def scan_equip(self, ctx):
		matches= self.get_matches(ctx.message.content, "equip")
		has_failed= False

		msgs= []
		for x in matches:
			await ctx.trigger_typing()
			has_excl, isekai, equip_id, equip_key= x

			# try parsing, add reaction to original message on fail
			try:
				t= await preview_utils.parse_equip_match(equip_id=equip_id,
														 equip_key=equip_key,
														 level=len(has_excl),
														 isekai=bool(isekai),
														 session=self.session)
			except Exception as e:
				CONFIG= utils.load_yaml(utils.PREVIEW_CONFIG)
				traceback.print_tb(e.__traceback__)

				if not has_failed:
					await ctx.message.add_reaction(CONFIG['fail_reaction_emote'])
					has_failed= True
					continue

			msgs.append(t)

		texts= [f"```py\n{x.strip()}\n```" for x in msgs if isinstance(x,str)]
		embeds= [x for x in msgs if isinstance(x, discord.Embed)]

		sent= []
		for x in get_pages("".join(texts), no_orphan=10, join_char="\n"):
			if x:
				sent.append(await ctx.send(x))

		for x in embeds:
			sent.append(await ctx.send(embed=x))

		self.bot.track(ctx.message, sent, post_func=self.on_message)


	@preview_utils.scan_decorator(key="thread")
	async def scan_thread(self, match):
		has_excl, thread_id= match
		embed= await preview_utils.parse_thread_match(thread_id=thread_id,
													  session=self.session,
													  is_long=has_excl)
		return embed


	@preview_utils.scan_decorator(key="comment")
	async def scan_comment(self, match):
		has_excl, thread_id, post_id= match
		embed= await preview_utils.parse_comment_match(thread_id=thread_id,
													   post_id=post_id,
													   session=self.session,
													   is_long=has_excl)
		return embed


	@preview_utils.scan_decorator(key="bounty")
	async def scan_bounty(self, match):
		has_excl, bounty_id= match
		embed= await preview_utils.parse_bounty_match(bounty_id=bounty_id,
													  session=self.session,
													  is_long=has_excl)
		return embed


	def get_matches(self, string, regex_key):
		# inits
		matches= []

		# scan for links
		for x in self.LINK_REGEX[regex_key]:
			tmp= re.findall(x, string)
			if tmp: matches+= tmp

		# get matches without < and >
		ret= []
		for x in matches:
			if not (x[0] and x[-1]):
				ret.append(x[1:-1])

		return ret


	# Just so there's an entry in the help command.
	@commands.command(name="preview", short="preview", cls=PartialCommand)
	async def _preview(self):
		pass

	async def get_edit(self, message):
		ctx= await self.bot.get_context(message)
