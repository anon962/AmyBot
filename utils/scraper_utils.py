async def get_html(link, session):
	from classes.errors import TemplatedError

	resp= await session.get(link)
	if not resp.status == 200:
		raise TemplatedError("bad_response", link=link, response=resp)
	else:
		text= await resp.text(encoding='utf-8', errors='ignore')
		return text

def get_session():
	import aiohttp

	# keep-alive because https://github.com/aio-libs/aiohttp/issues/3904#issuecomment-632661245
	return aiohttp.ClientSession(headers={'Connection': 'keep-alive'})