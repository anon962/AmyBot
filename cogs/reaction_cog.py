from classes import PartialCog, PartialCommand
from utils.cog_utils.reaction_utils import has_reaction_perms, is_self
from utils.cog_utils import reaction_utils as React
from utils.pprint_utils import get_pages
from utils.cog_utils import pageify_and_send
from discord.ext import commands
import utils, discord, os, json


"""
For various reaction-related functions.
"""
class ReactionCog(PartialCog, name="Reaction"):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.hidden=False


	@commands.Cog.listener()
	async def on_raw_reaction_add(self, payload):
		if await self.reaction_delete(payload):
			return

		for x in [self.add_rr_role]:
			await x(payload)


	@commands.Cog.listener()
	async def on_raw_reaction_remove(self, payload):
		for x in [self.remove_rr_role]:
			await x(payload)

	@is_self
	@has_reaction_perms(command_name="reaction_role")
	async def add_rr_role(self, payload):
		return await self.handle_rr(payload, typ="add")

	@is_self
	@has_reaction_perms(command_name="reaction_role")
	async def remove_rr_role(self, payload):
		return await self.handle_rr(payload, typ="remove")

	async def handle_rr(self, payload, typ):
		# inits
		ch_id= str(payload.channel_id)
		m_id= str(payload.message_id)

		# check for guild
		if not payload.guild_id: return

		# load log
		log_file= utils.REACTION_ROLE_LOG_DIR + str(payload.guild_id) + ".json"
		if not os.path.exists(log_file): return
		log= utils.load_json_with_default(log_file, default=False)

		# check for existence
		if ch_id not in log: return
		if m_id not in log[ch_id]: return

		# get role index
		try:
			ind= log[ch_id][m_id]['emotes'].index(str(payload.emoji))
		except ValueError:
			return

		# get role
		role_id= log[ch_id][m_id]['roles'][ind]
		guild= self.bot.get_guild(payload.guild_id)
		role= guild.get_role(role_id)
		member= guild.get_member(payload.user_id)

		# add role to member
		try:
			if typ == "add":
				await member.add_roles(role, reason=f"reaction role")
			elif typ == "remove":
				if role in member.roles:
					await member.remove_roles(role, reason=f"reaction role")
			else:
				raise Exception(f"Bad typ passed to handle_rr (expected 'add' or 'remove' but got '{typ}')")

		except discord.Forbidden:
			CONFIG= utils.load_yaml(utils.REACTION_CONFIG)

			template= utils.load_yaml(utils.ERROR_STRING_FILE)[f'no_{typ}_perms_template']
			text= utils.render(template,dict(member=member, role=role))

			channel= self.bot.get_channel(int(ch_id))
			await channel.send(text, delete_after=CONFIG['error_deletion_delay'])
		return

	@commands.command(name="addrr", short="addrr", cls=PartialCommand)
	async def add_rr(self, ctx):
		# inits
		message_dict= React.parse_message_json(ctx.query)
		msg= await ctx.send(content=message_dict['content'],
							embed=discord.Embed.from_dict(message_dict['embed']))

		# edit log
		React.edit_rr_log(msg, message_dict=message_dict)
		return

	@commands.command(name="editrr", short="editrr", cls=PartialCommand)
	async def edit_rr(self, ctx):
		msg, query= await React.get_rr_message(ctx.query, ctx, self.bot)
		typ, query= React.get_rr_type(query, ctx)

		# if edit msg
		if typ == React.RR_MESSAGE:
			# inits
			message_dict= React.parse_message_json(query)
			await msg.edit(content=message_dict['content'],
						   embed=discord.Embed.from_dict(message_dict['embed']))

			# edit log
			entry= React.edit_rr_log(msg, message_dict=message_dict)
			return


		# if edit roles
		elif typ == React.RR_ROLE:
			# edit log
			roles, remainder= React.parse_roles(query, ctx, self.bot)
			entry= React.edit_rr_log(msg, roles=roles)

			# notify user
			await React.notify_rr_emote_role_edit(ctx, roles, entry['emotes'], remainder, message=msg)
			return


		# if edit emotes
		elif typ == React.RR_EMOTE:
			# edit log
			emotes, remainder= React.parse_emotes(query, ctx, self.bot)
			entry= React.edit_rr_log(msg, emotes=emotes)

			# edit msg
			await msg.clear_reactions()
			for x in emotes:
				await msg.add_reaction(x)

			# notify user
			roles= React.get_roles(entry['roles'], bot=self.bot, ctx=ctx, message=msg)
			await React.notify_rr_emote_role_edit(ctx, roles, emotes, remainder, message=msg)
			return

	@commands.command(name="getrr", short="getrr", cls=PartialCommand)
	async def get_rr(self, ctx):
		entries= []
		messages= []

		# get messages / log entries
		if ctx.query.lower() != "all" and ctx.query.strip():
			msg,_= await React.get_rr_message(ctx.query, ctx, self.bot)
			entry= React.edit_rr_log(msg)
			entries.append(entry)
			messages.append(msg)
		else:
			messages= await React.get_all_rr_messsages(ctx.query, ctx, self.bot)
			entries= [React.edit_rr_log(m) for m in messages]

		# format and send
		for m,ent in zip(messages,entries):
			# format
			template= utils.load_yaml(utils.REACTION_CONFIG)['rr_log_entry_template']
			pairs= React.zip_uneven_lists(ent['roles'],ent['emotes'])
			text= utils.render(template, dict(message_json=json.dumps(ent['message'],indent=2),
											  pairs=pairs,
											  message=m))

			# send
			await pageify_and_send(ctx, strings=text, page_limit_server=99)

	@commands.command(name="listroles", short="listroles", cls=PartialCommand)
	async def listroles(self, ctx):
		# format
		roles= ctx.guild.roles
		template= utils.load_yaml(utils.REACTION_CONFIG)['list_roles_template']
		text= utils.render(template, dict(roles=roles))

		# send
		await pageify_and_send(ctx, strings=text, page_limit_server=99, code="css")

	# delete bot messages reacted to with CONFIG['deletion_emote']
	@is_self
	@has_reaction_perms(command_name="reaction_delete")
	async def reaction_delete(self, payload):
		# inits
		CONFIG= utils.load_yaml(utils.REACTION_CONFIG)
		channel= self.bot.get_channel(payload.channel_id)
		message= await channel.fetch_message(payload.message_id)

		# check emoji
		if payload.emoji.is_unicode_emoji() and str(payload.emoji) == CONFIG['deletion_emote']:
			await message.delete()
			return True