import os

ROOT_DIR= os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + "/"
CONFIG_DIR= ROOT_DIR + "config/"
DATA_DIR= ROOT_DIR + "data/"
CACHE_DIR= ROOT_DIR + "cache/"
STRING_DIR= CONFIG_DIR + "strings/"
PERMS_DIR= CONFIG_DIR + "perms/"
COG_CONFIG_DIR= CONFIG_DIR + "cog_configs/"

BOT_CONFIG_FILE= CONFIG_DIR + "bot_config.yaml"

HELP_STRING_FILE= STRING_DIR + "help.yaml"
ERROR_STRING_FILE= STRING_DIR + "errors.yaml"
COG_STRING_FILE= STRING_DIR + "cog_descriptions.yaml"
PPRINT_STRING_FILE= STRING_DIR + "pprint.yaml"
NAME_STRING_FILE= STRING_DIR + "cog_command_names.yaml"

GLOBAL_PERMS_FILE= PERMS_DIR + "00globals.yaml"

AUCTION_CONFIG= COG_CONFIG_DIR + "equip_cog_config.yaml"
AUCTION_FILE= DATA_DIR + "merged_equip_data.json"

ITEM_CONFIG= COG_CONFIG_DIR + "item_cog_config.yaml"
ITEM_FILE= DATA_DIR + "merged_item_data.json"

PREVIEW_CONFIG= COG_CONFIG_DIR + "preview_cog_config.yaml"

REACTION_CONFIG= COG_CONFIG_DIR + "reaction_cog_config.yaml"
REACTION_ROLE_LOG_DIR= CACHE_DIR + "reaction_roles/"

SUPER_DIR= CACHE_DIR + "super/"
SUPER_HTML_DIR= SUPER_DIR + "html/"
SUPER_CACHE_FILE= SUPER_DIR + "cache.json"
SUPER_EQUIP_FILE= SUPER_DIR + "equips.json"
SUPER_ITEM_FILE= SUPER_DIR + "items.json"

MARKET_DIR= CACHE_DIR + "hvmarket/"
MARKET_CACHE_FILE= MARKET_DIR + "cache.json"
MARKET_ITEM_FILE= MARKET_DIR + "items.json"

KEDAMA_DIR= CACHE_DIR + "kedama/"
KEDAMA_HTML_DIR= KEDAMA_DIR + "html/"
KEDAMA_DEBUG_FILE= KEDAMA_DIR + "debug.json"
KEDAMA_EQUIP_FILE= KEDAMA_DIR + "equips.json"
KEDAMA_ITEM_FILE= KEDAMA_DIR + "items.json"

RANGES_FILE= DATA_DIR + "ranges.json"

UPDATE_LOG= CACHE_DIR + "update_log.json"