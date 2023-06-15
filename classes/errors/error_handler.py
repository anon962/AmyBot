from discord.ext import commands
from discord.errors import Forbidden

from .parse_error import ParseError
from .permission_error import PermissionError
from .templated_error import TemplatedError

import utils, traceback, sys

# mixin for globally handling errors
class ErrorHandler:
	async def on_command_error(self, ctx, e):
		if isinstance(e, Forbidden):
			pass # @ todo: handle no send perms
		if isinstance(e, PermissionError):
			if not e.silent:
				return await ctx.send(e.render())
		elif isinstance(e, TemplatedError) or isinstance(e, ParseError):
			self.track(ctx.message, await ctx.send(e.render(ctx)))
		elif isinstance(e, commands.CheckFailure):
			pass # @ todo: silent logging for checkfailure
		else:
			return await self.handle_other_error(ctx, e)

	# todo: replace jinja templates with mako
	# Unexpected errors
	async def handle_other_error(self, ctx, e):
		# get the actual stack trace if available
		if isinstance(e, commands.CommandInvokeError):
			err= e.original
		else: err= e

		# dump into template
		ERROR_STRINGS= utils.load_yaml(utils.ERROR_STRING_FILE)
		text= "\n".join(traceback.format_tb(err.__traceback__)) + "\n---\n" + str(e)
		uncaught= utils.render(ERROR_STRINGS['uncaught_template'], dict(EXCEPTION=text[-1400:], MESSAGE=ctx.message.content[:400]))

		# print
		m= await ctx.send(uncaught)
		traceback.print_tb(err.__traceback__)
		sys.stderr.write(str(e))

		# check for edit
		self.track(ctx.message, m)