import utils
from bot import AmyBot

# inits
BOT_CONFIG= utils.load_yaml(utils.BOT_CONFIG_FILE)
bot= AmyBot(BOT_CONFIG['prefix'], case_insensitive=True)

# run
bot.run(BOT_CONFIG['discord_key'])