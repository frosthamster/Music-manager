from typing import List

from pylast import LastFMNetwork, WSError, Album
from urllib.request import urlopen
from settings import get_last_fm_api_key

__all__ = ['LastFM']


class LastFM:
    def __init__(self, username=''):
        self._username = username
        self._api = LastFMNetwork(api_key=get_last_fm_api_key())
        self._user = self._api.get_user(self._username)

    def try_download_cover(self, performer, title, path):
        title = self._api.get_album(performer, title)
        try:
            cover = title.get_cover_image()
        except WSError:
            return False
        cover_data = urlopen(cover).read()
        with open(path.joinpath('cover.png'), 'wb') as f:
            f.write(cover_data)
        return True

    def get_weekly_top_albums(self):
        return self._user.get_weekly_album_charts()

    def search_album(self, performer, title):
        suitable = []
        for album in self._api.search_for_album(title).get_next_page():
            if album.artist.name.lower() == performer.lower():
                suitable.append(album)
        if len(suitable) > 0:
            return max(*suitable, key=lambda a: len(a.get_tracks()))

    def get_recommended_albums(self, library, max=20) -> List[Album]:
        result = []
        top_albums = self.get_weekly_top_albums()
        existed_albums = {performer: set(alb.name.lower() for alb in albums) for performer, albums in library.library}
        for album, weight in top_albums:
            if len(result) >= max:
                break

            performer = album.artist.get_name().lower()
            title = album.get_name().lower()

            if title not in existed_albums.get(performer, set()):
                result.append(album)
        return result
