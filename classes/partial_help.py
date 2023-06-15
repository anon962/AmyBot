from discord.ext import commands
import utils

# @ todo: check aliases
# Override of help command for partial matching
class PartialHelp(commands.DefaultHelpCommand):

	# Find relevant cogs / cmds with support for partial matching
	async def command_callback(self, ctx, *, name=None):
		bot= ctx.bot
		mapping= self.get_bot_mapping()

		if name is None or len(name) < 3: return await self.send_default_help(mapping)

		# find matching cog names
		cogs= []
		for x in bot.cogs:
			if name.lower() in x.lower() and not bot.cogs[x].hidden:
				cogs.append(bot.cogs[x])

		# find matching commands
		cmds= []
		for x in bot.all_commands:
			if name.lower() in x.lower() and not bot.all_commands[x].hidden:
				cmds.append(bot.all_commands[x])

		# return main help message if no matches, else show help info for the matches
		if not cogs and not cmds:
			return await self.send_default_help(mapping)
		else:
			return await self.send_specific_help(mapping, cogs, cmds)

	# No cog name / command name supplied
	async def send_default_help(self, mapping):
		HELP_STRINGS= utils.load_yaml(utils.HELP_STRING_FILE)
		COG_STRINGS= utils.load_yaml(utils.COG_STRING_FILE)

		reps= {
			"COGS": [x for x in mapping if x is not None and not x.hidden],
			"PREFIX": self.clean_prefix,
			"COG_STRINGS": COG_STRINGS
		}

		ret= utils.render(template=HELP_STRINGS['default_help_template'], dct=reps)
		await self.get_destination().send(ret)

	# Specific cogs / commands supplied
	async def send_specific_help(self, mapping, cogs, commands):
		HELP_STRINGS= utils.load_yaml(utils.HELP_STRING_FILE)
		COG_STRINGS= utils.load_yaml(utils.COG_STRING_FILE)

		reps= {
			"COGS": cogs,
			"COMMANDS": commands,
			"PREFIX": self.clean_prefix,
			"COG_STRINGS": COG_STRINGS
		}

		ret= utils.render(template=HELP_STRINGS['specific_help_template'], dct=reps)
		await self.get_destination().send(ret)