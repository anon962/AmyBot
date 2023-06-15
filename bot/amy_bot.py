import discord, utils
from discord.ext import commands
from classes import PartialCommand, PartialHelp, TrackedMessage
from classes.errors import ErrorHandler
from utils.perm_utils import check_perms

"""
All cogs must subclass PartialCog and all commands must subclass PartialCommand. 
"""

# @TODO: logging
class AmyBot(commands.Bot, ErrorHandler):
	def __init__(self, prefix, *args, **kwargs):
		intents= discord.Intents.default()
		intents.members= True
		super().__init__(command_prefix=prefix, intents=intents, *args, **kwargs)

		self.help_command= PartialHelp()
		self.tracked_messages= dict()

	async def on_ready(self):
		from cogs import UpdateCog, EquipCog, ItemCog, PreviewCog, ReactionCog
		print(f"Logged in as {self.user.display_name}#{self.user.discriminator}")

		# add cogs
		# load cogs and checks
		self.add_cog(EquipCog(self))
		self.add_cog(ItemCog(self))

		self.add_cog(UpdateCog(self))
		self.add_cog(PreviewCog(self))
		self.add_cog(ReactionCog(self))

		self.add_check(check_perms)


	# @ TODO: partial matching for aliases?
	# Override process_commands to allow for partial command name matching
	async def process_commands(self, message): # @todo: comment
		if message.author.bot:
			return

		# check for partial names
		ctx= await self.get_context(message)
		if ctx.invoked_with and ctx.command is None:
			for cmd in self.all_commands:
				if type(self.all_commands[cmd]) is PartialCommand and ctx.invoked_with.startswith(self.all_commands[cmd].short):
					ctx.command= self.all_commands[cmd]
					break

		# get query (eg !auction blah --> blah)
		ctx.query= message.content.split(maxsplit=1)
		ctx.query= ctx.query[1].strip() if len(ctx.query) > 1 else ""

		# start command and send "typing..." message
		if ctx.command is not None:
			async with ctx.typing():
				await self.invoke(ctx)


	# handle errors during command
	async def on_command_error(self, ctx, e):
		return await ErrorHandler.on_command_error(self, ctx, e)

	async def on_message(self, message):
		await super().on_message(message)

		from utils.lotto_hotfix import lotto_hotfix
		await lotto_hotfix(message)

		from utils.trend_hotfix import trend_hotfix
		await trend_hotfix(message)

	async def on_message_edit(self, before, after):
		entry= self.tracked_messages.get(before.id, set())
		if not entry:
			return

		for tracked in entry.copy():
			await tracked.refresh(self, after)

	def track(self, in_msg, out_msgs, **kwargs):
		if out_msgs:
			CONFIG= utils.load_bot_config()
			tracked= TrackedMessage(in_msg, out_msgs,
									expire=CONFIG['max_edit_delay'],
									**kwargs)
			self.tracked_messages.setdefault(in_msg.id, set()).add(tracked)

	def untrack(self, tracked):
		self.tracked_messages[tracked.in_msg.id].remove(tracked)