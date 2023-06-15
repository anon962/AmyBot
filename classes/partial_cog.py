from discord.ext import commands


# todo: load cog config
class PartialCog(commands.Cog):
	def __init__(self, bot, hidden=False, **kwargs):
		self.bot= bot
		self.hidden=hidden
		super().__init__(**kwargs)