from classes import Table

# @ todo: comment this
def pprint(columns, prefix="", suffix="", code=None, v_sep="|", h_sep="-", v_pad=1, borders=False, corner="+"):
	ret= ""

	columns= columns.columns if isinstance(columns, Table) else columns
	padding= "".join([" "]*v_pad)
	v_sep_pad= padding + v_sep + padding

	not_link= [x for x in columns if not x.is_link]
	is_link= [x for x in columns if x.is_link]
	single_tick= (len(is_link) != 0)

	assert all([len(columns[0]) - len(x) == 0 for x in columns[1:]]) # check all columns same length
	assert len(not_link) > 0

	if code is not None and not single_tick: ret+= f"```{code}\n"
	if prefix: ret+= prefix + "\n"

	# horiz separator for header
	if h_sep:
		h_sep_length= sum(x.max_width for x in not_link) + len(not_link) * len(v_sep_pad) - v_pad
		if borders: h_sep_length+= len(v_sep_pad) - v_pad

		h_div= "".join(["-"] * h_sep_length)
		if borders:
			tmp= len(corner)+1
			h_div= f"{corner} " + h_div[tmp:-tmp] + f" {corner}"

		if single_tick: h_div= f"`{h_div}`"

	if h_sep and borders: ret+= h_div + "\n"

	# headers
	if any(x.header for x in columns):
		tmp= ""

		if borders: tmp+= v_sep + padding

		for col in not_link:
			tmp+= col.header.ljust(col.max_width) + v_sep_pad
		if single_tick: tmp= f"`{tmp}`"

		ret+= tmp + "\n"
		if h_sep: ret+= h_div + "\n"

	# data
	for i in range(len(not_link[0])):
		tmp= ""

		if borders: tmp+= v_sep + padding

		for col in not_link:
			tmp+= col[i].ljust(col.max_width) + v_sep_pad
		if single_tick: tmp= f"`{tmp}`"

		for col in is_link:
			tmp+= col[i].ljust(col.max_width) + padding + padding

		ret+= tmp + "\n"

	# trailers
	if any(x.trailer for x in columns):
		tmp= ""

		if borders: tmp+= v_sep_pad + padding
		if h_sep: ret+= h_div + "\n"

		for col in not_link:
			tmp+= col.trailer.ljust(col.max_width) + v_sep_pad
		if single_tick: tmp= f"`{tmp}`"

		ret+= tmp + "\n"

	if h_sep and borders: ret+= h_div + "\n"


	if suffix: ret+= suffix + "\n"
	if code is not None and not single_tick: ret+= f"\n```"
	return ret


# Groups strings into a new list of "pages" such that each page
#    has length < max_len
#    has either exactly 0 or greater than no_orphan lines of each string
def get_pages(strings, max_len=1900, no_orphan=4, join_char="\n"):
	# inits
	if not isinstance(strings, list):
		strings= [strings]

	pages= []
	split= [x.split("\n") for x in strings]

	jlen= len(join_char)
	def page_len(lst): # calculate length of a page, accounting for join_char length
		return sum(len(x) for x in lst) + len(lst)*jlen

	pg= []
	for i in range(len(split)): # loop each message
		tbl= split[i]

		for j in range(len(tbl)): # loop each line in message
			line= tbl[j]

			# if new_page, check if enough space for adding no_orphan lines to current page
			next_len= page_len(pg) + page_len(tbl[:no_orphan])
			will_orphan= (j == 0 and next_len > max_len)

			# check if enough space for current line
			will_exceed= (page_len(pg) + len(line) + jlen > max_len)

			if will_orphan or will_exceed:
				pages.append(pg)
				pg= [line]
			else:
				pg.append(line)

	if pg: pages.append(pg)
	return [join_char.join(x) for x in pages]
