from .global_utils import *
from .misc_utils import load_yaml, dump_yaml, load_json_with_default, dump_json, load_bot_config
import jinja2

ENV= jinja2.environment.Environment(trim_blocks=True, lstrip_blocks=True)
def render(template, dct):
	dct= { x.upper():y for x,y in dct.items() }
	return ENV.from_string(template).render(**dct)