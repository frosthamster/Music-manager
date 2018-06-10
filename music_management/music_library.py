import re
from os.path import abspath
from shutil import copytree, rmtree
from music_downloading import LastFM
from .case_non_sensitive_dict import CaseNonSensitiveDict
from functools import wraps
from itertools import chain, groupby
from pathlib import Path
from pickle import dump
from deflacue.deflacue import CueParser
from typing import Dict, List
from utils import with_upper_first_letter
from pickle import load
from .copy import copy_with_progress
from .track import Track
from ui import ui
from .album import Album

__all__ = ['MusicLibrary']

ALBUM_RE = re.compile(r'(^\d{4}) - (.+)$')


def parse_path(f=None, *, strict=False):
    if f is None:
        return lambda func: parse_path(func, strict=strict)

    @wraps(f)
    def wrapper(*args, **kwargs):
        if len(args) < 2:
            raise ValueError

        file_name = args[1]
        if isinstance(file_name, Path):
            return f(*args, **kwargs)

        path = Path(file_name)
        path = path.resolve()
        if not path.exists():
            ui.show(f'Not found: {file_name}')
            if strict:
                raise FileNotFoundError
            return

        return f(*((args[0], path) + args[2:]), **kwargs)

    return wrapper


def log_err(path, exc_info):
    _, e, _ = exc_info
    ui.show(f'{path}\n{str(e)}')


class MusicLibrary:
    supported_types = ('.flac', '.alac', '.mp3', '.wav')
    covers_extensions = ('.jpeg', '.jpg', '.bmp', '.png')

    @parse_path(strict=True)
    def __init__(self, path):
        self._path: Path = path
        self._library: Dict[str, List[Album]] = self._load_library(self._path)
        self._clean_library()

    def close(self):
        with self._metadata.open('wb') as f:
            dump(self._library, f)
        ui.show('Library saved')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def location(self):
        return self._path

    @property
    def library(self):
        return self._library.items()

    @staticmethod
    def _purge(folders):
        for folder in folders:
            rmtree(abspath(folder), onerror=log_err)

    def _update_albums_data(self):
        pass

    def _remove_non_exists_albums(self):
        for performer, albums in self._library.copy().items():
            exist_albums = [a for a in albums if a.get_location(self._path).exists()]
            if len(exist_albums) > 0:
                self._library[performer] = exist_albums
            else:
                del self._library[performer]

    def _add_all_unknown_albums_from(self, path: Path):
        performer = with_upper_first_letter(path.name)
        exists_albums = set() if performer not in self._library else {repr(a) for a in self._library[performer]}
        for album_dir in (p for p in path.iterdir()
                          if p.is_dir() and p.name not in exists_albums and self._is_folder_with_tracks(p)):
            self.add_album(album_dir, performer=performer, inside_ok=True, delete_src=True)

    def _handle_unknown_albums(self):
        for path in (p for p in self._path.iterdir() if p.is_dir()):
            if self._is_folder_with_tracks(path):
                self.add_album(path, inside_ok=True, delete_src=True)
            else:
                self._add_all_unknown_albums_from(path)
            if path.exists() and len(list(path.iterdir())) == 0:
                rmtree(path.absolute(), onerror=log_err)

    def _clean_library(self):
        self._remove_non_exists_albums()
        self._update_albums_data()
        ui.show('Search for unknown albums in the library')
        self._handle_unknown_albums()

    @staticmethod
    def _get_albums_repr(library):
        result = []
        for performer, albums in library.items():
            result.append(f'{performer if len(albums) == 0 else albums[0].performer}:')
            for album in albums:
                result.append(f'    {str(album)}')
        result.append('\n')
        return '\n'.join(result)

    def show_library(self):
        albums = self._get_albums_repr(self._library)
        ui.show(albums if albums != '\n' else 'Library is empty')

    def _get_diff(self, other_lib):
        for performer, albums in self._library.items():
            albums = set(albums)
            yield from (albums - set(other_lib._library[performer]))

    @property
    def _metadata(self):
        return self._path.joinpath('library.metadata')

    @parse_path
    def export(self, path):
        diff = list(self._get_diff(MusicLibrary(path)))
        if len(diff) == 0:
            ui.show('Library is up to date')
            return
        albums = {k: list(g) for k, g in groupby(diff, key=lambda e: e.performer)}
        if not ui.ask_ok(f'These albums will be copied from {path.absolute()}\n{self._get_albums_repr(albums)}'):
            return
        for album in diff:
            src = album.get_location(self._path)
            dest = album.get_location(path)
            path.joinpath(album.performer).mkdir(parents=True, exist_ok=True)
            copytree(src.absolute(), dest.absolute(), copy_function=copy_with_progress)
        copy_with_progress(self._metadata, path)
        ui.show('Library exported')

    @staticmethod
    def _load_library(path):
        cache = list(path.glob('library.metadata'))
        if len(cache) > 0:
            with cache[0].open('rb') as f:
                return load(f)
        return CaseNonSensitiveDict(list)

    @property
    def performers(self):
        return list(with_upper_first_letter(k) if len(self._library[k]) == 0 else self._library[k][0].performer
                    for k in self._library.keys())

    @staticmethod
    def _get_cue(path):
        cues = list(path.glob('*.cue'))
        if len(cues) > 0:
            return CueParser(cues[0].absolute()), cues[0]
        return None, None

    @staticmethod
    def _get_year_and_title(path, cue):
        year, title = None, None
        name_match = ALBUM_RE.match(path.name)
        if name_match is not None:
            year, title = name_match.groups()

        if cue is not None:
            album_data = cue.get_data_global()
            if year is None and album_data['DATE'] is not None and album_data['DATE'].isdigit():
                year = album_data['DATE']
            if title is None and album_data['ALBUM'] != 'Unknown':
                title = album_data['ALBUM']

        if year is None:
            year = ui.get_input_from_user('Enter title release date', read_int=True)
        if title is None:
            title = path.name
        return int(year), with_upper_first_letter(title)

    def _get_tracks(self, path: Path, cue, interactive=True):
        result = []
        if cue is not None:
            tracks_data = cue.get_data_tracks()
            for data in tracks_data:
                if data['FILE'] is not None and 'TITLE' in data and 'INDEX' in data:
                    if Path(data['FILE']).name not in (p.name for p in path.iterdir() if p.is_file()):
                        ui.show(f'WARNING: {data["FILE"]} declared in .cue not found')
                        continue
                    result.append(Track(data['TITLE'], data['FILE'], data['INDEX']))
        if len(result) == 0:
            result = [Track(p.stem, p.name) for p in path.iterdir() if p.is_file() if p.suffix in self.supported_types]

        tracks = '\n'.join(str(t) for t in result)
        if not interactive or ui.ask_ok(f"These tracks will be added from {path.absolute()}\n{tracks}\n"):
            return result

    def _get_performer_from_user(self):
        _, result = ui.choose('Enter performer or choose from existing', self.performers)
        return with_upper_first_letter(result)

    def _get_performer(self, cue):
        result = None
        if cue is not None:
            album_data = cue.get_data_global()
            if album_data['PERFORMER'] != 'Unknown':
                result = album_data['PERFORMER']

        if result is None:
            return self._get_performer_from_user()

    def _normalize_album_metadata(self, performer, year, title):
        metadata = [performer, year, title]
        indexes = ['ok', 'p', 'y', 't', 'ex']
        options = ['all right', 'change performer', 'change year', 'change title', 'abort operation']

        while True:
            index, result = ui.choose(f"It's the correct album data?\n"
                                      f"Performer: {metadata[0]}\n"
                                      f"Year:      {metadata[1]}\n"
                                      f"Title:     {metadata[2]}\n",
                                      options, indexes)
            if index == 4:
                return None
            if index == 0:
                new_album = Album(*metadata, [])
                if metadata[0] in self._library and new_album in self._library[metadata[0]]:
                    ui.show('Such an album already exists in the library\n'
                            'Try change metadata of new album or delete old one\n')
                    continue
                return metadata
            if index == 1:
                metadata[0] = self._get_performer_from_user()
                continue
            metadata[index - 1] = ui.get_input_from_user(f'Enter new {options[index].split()[1]}',
                                                         read_int=True if index == 2 else False)
            if index == 3:
                metadata[2] = with_upper_first_letter(metadata[2])

    def _copy_album_to_library(self, album: Album, path: Path):
        destination = album.get_location(self._path)
        destination.mkdir(parents=True, exist_ok=True)
        to_copy = chain(filter(lambda e: e is not None, (album.cover_name, album.cue_name)),
                        (p.path for p in album.tracks))

        for src in set(path.joinpath(p) for p in to_copy):
            copy_with_progress(src, destination)

    def _get_or_download_cover(self, performer, title, path):
        covers = [p for p in path.iterdir() if p.is_file() and p.suffix in self.covers_extensions]
        if len(covers) > 0:
            return covers[0]
        lf = LastFM()

        if lf.try_download_cover(performer, title, path):
            ui.show('Successfully downloaded cover for album')
            return path.joinpath('cover.png')

    @parse_path
    def add_album(self, path: Path, performer=None, inside_ok=False, delete_src=False, interactive=True):
        if not path.is_dir():
            ui.show(f'Is not dir: {path.name}')
            return

        if not inside_ok and path in self._path.rglob(path.name):
            ui.show(f'Album already exists')
            return

        cue, cue_path = self._get_cue(path)
        tracks = self._get_tracks(path, cue, interactive)
        if tracks is None:
            ui.show('Tracks not found')
            return
        if performer is None:
            performer = self._get_performer(cue)
        year, title = self._get_year_and_title(path, cue)
        if interactive:
            normalized_metadata = self._normalize_album_metadata(performer, year, title)
            if normalized_metadata is None:
                return
            performer, year, title = normalized_metadata
        cover = self._get_or_download_cover(performer, title, path)
        cue_name = None if cue_path is None else cue_path.name
        cover_name = None if cover is None else cover.name
        album = Album(performer, year, title, tracks, cue_name, cover_name)
        try:
            if not album.get_location(self._path).exists():
                self._copy_album_to_library(album, path)
                if delete_src:
                    rmtree(path.absolute(), onerror=log_err)
        except OSError as e:
            ui.show(str(e))
            return
        self._library[performer].append(album)
        ui.show(f'Successfully added {year} - {title} to {performer}\n')

    def _is_folder_with_tracks(self, path: Path):
        return any(p.suffix in self.supported_types for p in path.iterdir() if p.is_file())

    @parse_path
    def add_folder(self, path):
        if self._is_folder_with_tracks(path):
            self.add_album(path)
        for path in path.iterdir():
            if path.is_dir():
                self.add_folder(path)
