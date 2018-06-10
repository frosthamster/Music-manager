from asyncio import gather
from pathlib import Path
import aiohttp
from os import remove
from pytube import YouTube, Stream
from pylast import Album

from utils import ProgressTracker
from .last_fm import LastFM
from .music_converter import convert_to_audio_async
from .youtube_resolver import resolve_track_async
from ui import ui

__all__ = ['download_album_async', 'download_album_to_lib_async']


def get_audio_download_stream(url):
    if url is None:
        return
    return YouTube(url).streams.filter(only_audio=True).first()


async def download_audio_async(stream: Stream, dest, chunk_size=4 * 1024, on_chunk_read=lambda s: None):
    if stream is None:
        return
    if not Path(dest).parent.exists():
        raise FileNotFoundError('Not found output dir')

    url = stream.url
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:

            with open(dest, 'wb') as fd:
                while True:
                    chunk = await resp.content.read(chunk_size)
                    if not chunk:
                        break
                    fd.write(chunk)
                    on_chunk_read(chunk_size)


async def download_album_async(album: Album, dest_folder):
    if not dest_folder.exists():
        raise FileNotFoundError(dest_folder)
    ui.show('Searching album description')
    tracks = album.get_tracks()
    year = album.get_wiki_published_date()
    if year is not None:
        year = year[-11:-7]
    else:
        year = ui.get_input_from_user('Enter album release date', read_int=True)
    performer = album.artist
    title = album.title
    dest = dest_folder.joinpath(f'{year} - {title}')
    dest.mkdir()
    ui.show('Downloading cover')
    LastFM().try_download_cover(performer, title, dest)

    ui.show('Searching tracks')
    video_urls = await gather(*[resolve_track_async(track.artist, track.title) for track in tracks])
    ui.show('Extracting sources')
    streams = [get_audio_download_stream(url) for url in video_urls]
    total_size = sum(s.filesize for s in streams if s is not None)
    tracker = ProgressTracker(total_size, 'Downloading album')
    destinations = []
    for i, stream in enumerate(streams):
        if stream is not None:
            destinations.append(dest.joinpath(f'{str(i+1).zfill(2)} {tracks[i].title}.{stream.subtype}'))
        else:
            ui.show(f'Not found {str(tracks[i])}')
            destinations.append(None)

    await gather(*[download_audio_async(stream, raw, on_chunk_read=tracker.add_progress)
                   for stream, raw in zip(streams, destinations)])
    tracker.close()
    ui.show('Converting to mp3')
    await gather(*[convert_to_audio_async(d, dest) for d in destinations if d is not None])
    for raw in filter(lambda e: e is not None, destinations):
        remove(raw)
    return dest


async def download_album_to_lib_async(album: Album, library):
    dest = library.location.joinpath(album.artist.name)
    dest.mkdir(exist_ok=True)
    album_path = await download_album_async(album, dest)
    library.add_album(album_path, performer=album.artist.name,
                      inside_ok=True, interactive=False)
