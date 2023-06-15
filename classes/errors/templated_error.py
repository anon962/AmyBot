from discord.ext import commands
import utils

# Auto-selects a template from utils.ERROR_STRING_FILE based on error_name
class TemplatedError(commands.CommandError):
	def __init__(self, error_name, **kwargs):
		self.error_name= error_name
		self.kwargs= kwargs

	def render(self, ctx):
		ERROR_STRINGS= utils.load_yaml(utils.ERROR_STRING_FILE)

		name= self.error_name.replace("_template", "")
		template_name= f"{self.error_name}_template"

		if template_name not in ERROR_STRINGS:
			available= [x for x in ERROR_STRINGS if x.endswith("template")]
			return utils.render(ERROR_STRINGS['tmp_not_found_template'], dict(NAME=name, AVAILABLE=available))

		return utils.render(ERROR_STRINGS[template_name], self.kwargs)