import aiohttp
from settings import get_google_api_key

__all__ = ['resolve_track_async']


async def resolve_track_async(performer, name):
    params = {
        'q': f'{performer} {name}',
        'part': 'id,snippet',
        'maxResults': 20,
        'key': get_google_api_key()
    }

    async with aiohttp.ClientSession() as session:
        async with session.get('https://www.googleapis.com/youtube/v3/search',
                               params=params) as resp:
            resp = await resp.json()
            if 'error' in resp:
                err = resp['error']
                errors = '\n'.join(' '.join(str(i) for i in e.items()) for e in err['errors'])
                raise RuntimeError(f"{err['message']}\n{errors}")

            tracks = extract_urls_from_api_resp(resp)
            for title, video_id in tracks:
                if 'live' not in title.lower():
                    return f'https://youtube.com/watch?v={video_id}'


def extract_urls_from_api_resp(data):
    videos = []

    for search_result in data.get("items", []):
        if search_result["id"]["kind"] == "youtube#video":
            videos.append((search_result["snippet"]["title"], search_result["id"]["videoId"]))

    return videos
