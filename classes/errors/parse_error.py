from discord.ext.commands.errors import CommandError
import utils

class ParseError(CommandError):
	def __init__(self, keyword=None, value=None, reason=None):
		"""
		For pretty printing parse errors.
		:param keyword: Keyword that the value belongs to
		:param value: String being parsed
		:param exception: Exception raised during parsing
		"""

		self.keyword= keyword
		self.value= value
		self.reason= reason

	def render(self, ctx):
		COG_STRINGS= utils.load_yaml(utils.COG_STRING_FILE)
		ERROR_STRINGS= utils.load_yaml(utils.ERROR_STRING_FILE)

		reps= {
			"PREFIX": ctx.prefix,
			"COMMAND": ctx.command.name,
			"ARGS": COG_STRINGS[ctx.command.cog.qualified_name]['commands'][ctx.command.name]['args'],
			"VALUE": self.value,
			"KEYWORD": self.keyword,
			"REASON": str(self.reason)
		}

		return utils.render(ERROR_STRINGS['parse_error_template'], reps)

	def __str__(self):
		STRINGS= utils.load_yaml(utils.ERROR_STRING_FILE)
		reps= {
			"VALUE": self.value,
			"KEYWORD": self.keyword,
			"REASON": str(self.reason)
		}
		return utils.render(STRINGS['parse_console_template'], reps)