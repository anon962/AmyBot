from discord.ext import commands

class PartialCommand(commands.Command):
	def __init__(self, func, short, **kwargs):
		self.short= short
		super().__init__(func, **kwargs)