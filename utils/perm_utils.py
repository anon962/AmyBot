from classes.errors import PermissionError
import utils, os, copy

# Don't immediately return in order to update perm dict for missing commands
def check_perms(ctx, command_name=None, cog_name=None, suppress=False):
	ret= False

	# inits
	GLOBALS= utils.load_yaml(utils.GLOBAL_PERMS_FILE)
	cmd= ctx.command.name if command_name is None else command_name
	if cog_name is None:
		cog= ctx.cog.qualified_name if ctx.cog is not None else "none"
	else:
		cog= cog_name

	# check global admin
	if _is_global_admin(ctx, GLOBALS):
		ret |= True

	# if dm, check dm perms in global_perms file, else guild perms file
	if ctx.guild is None:
		ret |= _check(cmd=cmd, cog=cog, perm_dict=GLOBALS['dm'], flags=GLOBALS['flags'], ctx=ctx, is_dm=True)
		utils.dump_yaml(GLOBALS, utils.GLOBAL_PERMS_FILE)
	else:
		# check guild owner
		if ctx.author.id == ctx.guild.owner.id:
			ret |= True

		# check guild admin
		member= ctx.guild.get_member(ctx.author.id)
		perms= member.permissions_in(ctx.channel)
		if perms.administrator:
			ret |= True

		# load guild perms
		perms_file= f"{utils.PERMS_DIR}{str(ctx.guild.id)}.yaml"
		if os.path.exists(perms_file):
			perms_dict= utils.load_yaml(perms_file)
		else:
			perms_dict= GLOBALS['default_perms']
			utils.dump_yaml(perms_dict, perms_file)

		# check guild perms
		if not suppress and not ret:
			ret |= _check(cmd=cmd, cog=cog, perm_dict=perms_dict, flags=perms_dict['flags'], ctx=ctx, is_dm=False)
		else:
			try:
				ret |= _check(cmd=cmd, cog=cog, perm_dict=perms_dict, flags=perms_dict['flags'], ctx=ctx, is_dm=False)
			except PermissionError:
				ret |= False

		utils.dump_yaml(perms_dict, perms_file)

	return ret

# do checks, starting with smallest scope
def _check(cmd, cog, perm_dict, flags, ctx, is_dm=False):
	# inits
	default_dict= dict(everyone=flags['PASS'], exceptions=[]) # @TODO: use flag reference
	chks= {
		"user": lambda dct: "user" not in dct or ctx.author.id == dct['user'],
		"roles": lambda dct: "roles" not in dct or all(y in [x.id for x in ctx.author.roles] for y in dct['roles']),
		"channel": lambda dct: "channel" not in dct or ctx.channel.id == dct['channel'],
	}
	def flag_chk(val):
		if val == flags['ALLOW']: return True
		elif val == flags['FAIL']: return False
		elif val == flags['PASS']: return None

	if is_dm: keys= ['user']
	else: keys= ['user', 'roles', 'channel']

	silent= not perm_dict['vocal_fail']
	details= perm_dict['details']


	# make if missing
	if cog not in perm_dict: perm_dict[cog]= copy.deepcopy(default_dict)
	if cmd not in perm_dict[cog]: perm_dict[cog][cmd]= copy.deepcopy(default_dict)

	# cmd checks
	for i,dct in enumerate([perm_dict[cog][cmd], perm_dict[cog], perm_dict]): # loop levels
		for e in dct['exceptions']: # loop exception list
			if all(chks[k](e) for k in keys): # check user / role / channel id listed in expception

				# if allowed return True, if fail raise PermissionError, else move to next level
				tmp= flag_chk(e['value'])
				if tmp is True:
					return tmp
				elif tmp is False:
					raise PermissionError(cmd, cog, exception=e, level=i, is_dm=is_dm, silent=silent, details=details)
				else: pass

		# if no matching exceptions, check "everyone" flag for current level
		if (tmp:=flag_chk(dct['everyone'])) is not None:
			if tmp is False:
				raise PermissionError(cmd, cog, level=i, everyone=True, is_dm=is_dm, silent=silent, details=details)
			return tmp

	raise PermissionError(cmd, cog, level=PermissionError.DEFAULT_LEVEL, is_dm=is_dm, silent=silent, details=details)


def _is_global_admin(ctx, GLOBALS):
	global_admins= GLOBALS['admins']
	if global_admins and any(ctx.author.id == global_admins[x] for x in global_admins):
		return True
	return False
