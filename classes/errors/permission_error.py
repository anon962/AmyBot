from discord.ext import commands
import utils

class PermissionError(commands.CheckFailure):
	SERVER_LEVEL= 2
	COG_LEVEL= 1
	COMMAND_LEVEL= 0
	DEFAULT_LEVEL= -1

	# Init with everyone set to True if the permission failure was due to the perm_dict's everyone key being false.
	def __init__(self, command, cog, level, exception=None, everyone=False, is_dm=False, silent=True, details=False):
		self.cog= cog
		self.command= command
		self.exception= exception
		self.level= level
		self.everyone= everyone
		self.is_dm= is_dm
		self.silent= silent
		self.details= details

	def render(self):
		STRINGS= utils.load_yaml(utils.ERROR_STRING_FILE)

		if self.level == self.DEFAULT_LEVEL:
			return utils.render(STRINGS['default_perm_error'], self.__dict__)
		if self.level == self.SERVER_LEVEL:
			return utils.render(STRINGS['server_perm_error'], self.__dict__)
		else:
			return utils.render(STRINGS['command_or_cog_perm_error'], self.__dict__)