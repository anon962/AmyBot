from classes.errors import TemplatedError
from utils.perm_utils import check_perms
from ruamel.yaml import YAML
from ruamel.yaml.parser import ParserError
from ruamel.yaml.scanner import ScannerError
import utils, re, discord, json


# ---- Decorators for on_raw_reaction_add ----

# check for admin or server owner
def is_admin_owner(bot, payload):
	global_admins= utils.load_yaml(utils.GLOBAL_PERMS_FILE)['admins']
	user= bot.get_user(payload.user_id)

	is_dm= payload.guild_id is None
	is_admin= global_admins and any(payload.user_id == global_admins[x] for x in global_admins)

	if is_dm or is_admin:
		pass
	else:
		guild= bot.get_guild(payload.guild_id)
		channel= guild.get_channel(payload.channel_id)
		user_perms= guild.get_member(payload.user_id).permissions_in(channel)

		if user.id == guild.owner.id:
			pass
		elif user_perms.administrator:
			pass
		else:
			return False

	return True


# check that message is not from self
def is_self(func):
	async def decorator(self, payload):
		channel= self.bot.get_channel(payload.channel_id)
		message= await channel.fetch_message(payload.message_id)

		if not message.author == self.bot.user:
			return
		if payload.user_id == self.bot.user.id:
			return

		return await func(self, payload)

	return decorator

# check reaction permissions
async def _has_perms(command_name, self, payload):
	channel= self.bot.get_channel(payload.channel_id)
	message= await channel.fetch_message(payload.message_id)

	ctx= await self.bot.get_context(message)
	ctx.author= self.bot.get_user(payload.user_id)

	return check_perms(ctx=ctx, command_name=command_name, cog_name=self.qualified_name, suppress=True)


# decorator for is_admin_owner, is_self, has_perms
def has_reaction_perms(command_name):
	def outer(func):
		async def inner(self, payload):
			# inits
			perm_check= await _has_perms(self=self, payload=payload, command_name=command_name)
			admin_check= is_admin_owner(bot=self.bot, payload=payload)

			# checks
			if not perm_check and not admin_check:
				return

			# passed checks
			return await func(self, payload)

		return inner
	return outer


# ---- Converters and the like ----

RR_MESSAGE= "message"
RR_ROLE= "roles"
RR_EMOTE= "emotes"

# Enforce argument to rr commands are either "message", "roles", or "emotes"
def get_rr_type(query, ctx):
	# inits
	spl= str(query).strip().split(maxsplit=1)
	new_query= spl[1]

	# check for guild
	if not ctx.guild: raise TemplatedError("no_guild")

	# get command type
	sw= lambda x: spl[0].lower().startswith(x.lower())

	if sw("msg") or sw("message"):
		ret= RR_MESSAGE
	elif sw("role"):
		ret= RR_ROLE
	elif sw("emote") or sw("emoji"):
		ret= RR_EMOTE
	else:
		raise TemplatedError("bad_rr_type", value=spl[0])

	return ret, new_query

async def get_rr_message(query, ctx, bot):
	# inits
	spl= query.strip().split(maxsplit=1)

	# validity checks
	if not ctx.guild: raise TemplatedError("no_guild")
	if not spl:	raise TemplatedError("no_rr_message_id")

	# get log
	message_id= spl[0]
	new_query= spl[1]

	log_file= utils.REACTION_ROLE_LOG_DIR + str(ctx.guild.id) + ".json"
	log= utils.load_json_with_default(log_file)

	# get message channel
	for ch in log:
		if message_id in log[ch]:
			msg_ch= bot.get_channel(int(ch))
			break
	else:
		raise TemplatedError("bad_rr_message_id", string=message_id)

	# fetch message
	try:
		msg= await msg_ch.fetch_message(int(message_id))
		return msg, new_query
	except discord.NotFound:
		raise TemplatedError("deleted_rr_message", string=message_id)
	except ValueError:
		raise TemplatedError("rr_message_not_int", string=message_id)

async def get_all_rr_messsages(query, ctx, bot):
	messages= []

	# check for guild
	if not ctx.guild: raise TemplatedError("no_guild")

	# get log
	log_file= utils.REACTION_ROLE_LOG_DIR + str(ctx.guild.id) + ".json"
	log= utils.load_json_with_default(log_file)

	# return existing messages
	for ch in log:
		for m in log[ch]:
			# fetch message
			try:
				msg_ch= bot.get_channel(int(ch))
				msg= await msg_ch.fetch_message(int(m))
				messages.append(msg)
			except discord.NotFound:
				pass

	return messages


# get roles from string, case insensitive
def parse_roles(string, ctx, bot):
	# inits
	def parse(string):
		# get exact rendered matches
		r_id= re.match(r"<@&(\d+)>", string)
		if r_id:
			role= bot.get_role(int(r_id))
			if role:
				string= string.replace(f"<@&{r_id}>", "", count=1)
				return role,string

		# get exact, spaced name matches
		for role in guild_roles:
			m= re.match(rf"{role.name}\b", string, flags=re.IGNORECASE)
			if m:
				string= re.sub(rf"{role.name}\b", "", string, count=1, flags=re.IGNORECASE)
				return role, string

		# get exact, unspaced name matches
		for role in guild_roles:
			m= re.match(rf"{role.name}", string, flags=re.IGNORECASE)
			if m:
				string= re.sub(rf"{role.name}", "", string, count=1, flags=re.IGNORECASE)
				return role,string

		# get partial matches based on first word (must match whole word in role name)
		spl= string.split()
		for role in guild_roles:
			if spl[0].lower() in role.name.lower().split():
				return role, " ".join(spl[1:])

		# get partial matches based on first word (can match part of a word in role name)
		spl= string.split()
		for role in guild_roles:
			if spl[0].lower() in role.name.lower():
				return role, " ".join(spl[1:])

	ret= []
	guild_roles= ctx.guild.roles

	# greedy matching
	i,last_length= 0,0
	while i < len(string):
		# get match
		result= parse(string[i:])
		if result:
			match= result[0]
			string= string[:i] + result[1]
			ret.append(match)

		# stay on iteration until no more matches found
		if len(ret) != last_length:
			last_length= len(ret)
			continue
		else:
			i+=1

	return ret, [x for x in string.split() if x]


# get emotes from string, case insensitive, preserves order
def parse_emotes(string, ctx, bot):
	# inits
	def parse(string):
		# get unicode emotes
		m= re.match(f"({CONFIG['unicode_emote_regex']})", string)
		if m:
			string= string.replace(m.group(0),"", 1)
			return m.group(0),string

		# get exact matches from rendered emotes
		m= re.match(r"<a?:[a-z\d_]+:([0-9]+)>", string, flags=re.IGNORECASE)
		if m:
			e= discord.utils.get(emotes, id=int(m.group(1)))
			if e:
				string= string.replace(m.group(0),"", 1)
				return e,""

		# get exact matches from id
		try:
			e= discord.utils.get(emotes, id=int(string))
			return e,""
		except ValueError: pass

		# get exact matches from name
		e= discord.utils.find(lambda y: string.lower() == y.name.lower(), emotes)
		if e:
			return e,""

		# get partial matches from name
		e= discord.utils.find(lambda y: string and (string.lower() in y.name.lower()), emotes)
		if e:
			return e,""

	ret= []
	emotes= bot.emojis
	spl= string.strip().split()
	CONFIG= utils.load_yaml(utils.REACTION_CONFIG)

	# greedy matching
	i, last_length= 0,0
	while i < len(spl):
		# get match
		result= parse(spl[i])
		if result:
			match,spl[i]= result
			ret.append(str(match))

		# stay on iteration until no more matches found
		if len(ret) != last_length:
			last_length= len(ret)
			continue
		else:
			i+=1

	return ret, [x for x in spl if x]

# get emotes from string, case insensitive
def parse_message_json(string):
	string= string.strip()

	# add brackets
	# string= "{ " + string if not string.startswith("{") else string
	# string+= "} " if not string.endswith("}") else ""

	# if empty
	if not string:
		raise TemplatedError("empty_message_json")

	# convert to yaml (which supports json)
	try:
		dct= YAML().load(string)
	except (ParserError, ScannerError) as e:
		raise TemplatedError("yaml_to_json", string=string, error=str(e))

	# convert yaml to dictionary
	dct= dict(dct)

	# get embed
	embed_dict= {}
	if "embed" in dct:
		try:
			embed= discord.Embed.from_dict(dct["embed"])
			embed_dict= embed.to_dict()
		except Exception as e:
			raise TemplatedError("bad_embed_json", string=string, error=str(e))

		if embed_dict == discord.Embed.from_dict({}).to_dict():
			raise TemplatedError("empty_embed_json", string=json.dumps(dct,embed=2))

	# get text
	text=""
	if "content" in dct:
		text= str(dct["content"])

	# check non-empty
	if not text and not embed_dict:
		raise TemplatedError("empty_message_json")

	return dict(content=text, embed=embed_dict)

def edit_rr_log(message, message_dict=None, roles=None, emotes=None):
	# load log
	log_file= utils.REACTION_ROLE_LOG_DIR + str(message.guild.id) + ".json"
	log= utils.load_json_with_default(log_file, default={})

	# add default values (includes channel id because cant fetch message without it)
	ch_id= str(message.channel.id)
	m_id= str(message.id)

	if ch_id not in log:
		log[ch_id]= {}
	if m_id not in log[ch_id]:
		log[ch_id][m_id]= dict(message={}, roles=[], emotes=[])

	# edit entry
	entry= log[str(message.channel.id)][str(message.id)]
	if message_dict is not None:
		entry['message']= message_dict
	if roles is not None:
		entry['roles']= [x.id for x in roles]
	if emotes is not None:
		entry['emotes']= [str(x) for x in emotes]

	# save log
	utils.dump_json(log, log_file)
	return entry

def get_emotes(id_list, bot, ctx, message):
	ret= []
	emotes= bot.emojis

	for x in id_list:
		try:
			e= discord.utils.get(emotes, id=int(x))
			if e is None:
				raise TemplatedError("deleted_rr_emote", id=x, ctx=ctx, message=message)
			else:
				ret.append(e)
		except ValueError:
			ret.append(x) # unicode emoji

	return ret

def get_roles(id_list, bot, ctx, message):
	ret= []
	roles= message.guild.roles

	for x in id_list:
		e= discord.utils.get(roles, id=int(x))
		if e is None:
			raise TemplatedError("deleted_rr_role", id=x, ctx=ctx, message=message)
		else:
			ret.append(e)

	return ret

async def notify_rr_emote_role_edit(ctx, roles, emotes, remainder, message):
	# inits
	CONFIG= utils.load_yaml(utils.REACTION_CONFIG)
	notify_template= CONFIG['rr_role_emote_edit_template']

	# preprocess
	pairs= zip_uneven_lists([x.name for x in roles], emotes)

	# notify
	text= utils.render(notify_template, dict(pairs=pairs, remainder=remainder, message=message))
	await ctx.send(text)

def zip_uneven_lists(lst1, lst2):
	pairs= []
	for i in range(max(len(lst1), len(lst2))):
		tmp= []

		if i < len(lst1): tmp.append(lst1[i])
		else: tmp.append("")

		if i < len(lst2): tmp.append(str(lst2[i]))
		else: tmp.append("")

		pairs.append(tuple(tmp))
	return pairs