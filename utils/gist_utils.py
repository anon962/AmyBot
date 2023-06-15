import aiohttp, json

# todo: handle github rate limits
# todo: dump command data as well
async def update_data_gist(text, config):
	headers= dict(
		Authorization=f"token {config['gist_token']}"
	)
	payload= json.dumps({
		"files": {
			"bot_dump.md": {
				"content": text
			}
		}
	})
	target_url= f"https://api.github.com/gists/{config['gist_id']}"

	session= aiohttp.ClientSession(headers=headers)
	resp= await session.patch(target_url, data=payload)
	assert resp.status == 200
	await session.close()

def get_gist_link(bot_config):
	c= bot_config
	if c['enable_gist']:
		return f"https://gist.github.com/{c['gist_user']}/{c['gist_id']}"
	else:
		return None