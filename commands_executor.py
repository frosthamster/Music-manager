from music_management import MusicLibrary
from ui import ui
from backup import Uploader
from getpass import getpass
from settings import settings
from music_downloading import LastFM, download_album_to_lib_async


class ArgsParser:
    def __init__(self, *args_types, split_by=' ', parser=None):
        self._args_types = args_types
        self._delimiter = split_by
        self._parser = parser

    @property
    def args_count(self):
        return len(self._args_types)

    def _split(self, data):
        result = []
        current_word = []
        current_quote = None

        for c in data:
            if c in ("'", '"'):
                if current_quote is None:
                    current_quote = c
                elif current_quote == c:
                    result.append(''.join(current_word))
                    current_word.clear()
                    current_quote = None
                else:
                    current_word.append(c)
            else:
                if c == self._delimiter and current_quote is None and len(current_word) > 0:
                    result.append(''.join(current_word))
                    current_word.clear()
                else:
                    current_word.append(c)

        if len(current_word) > 0:
            result.append(''.join(current_word))

        return result

    def parse(self, data):
        if self._parser is not None:
            return self._parser(data)
        data = self._split(data)
        if len(data) != self.args_count:
            raise ValueError(f'Incorrect args count (expected {self.args_count})')
        return [cons(d) for cons, d in zip(self._args_types, data)]


available_commands = {}


def command(key, prompt='', parser=ArgsParser(), input_func=None):
    def dec(f):
        def wrapper(self, *args):
            if parser.args_count > 0:
                args = ui.get_input_from_user(prompt, validation_func=parser.parse, input_func=input_func)
            return f(self, *args)

        if key in available_commands:
            raise ValueError('Command already exists')
        available_commands[key] = wrapper, f.__name__.replace('_', ' ')

        return f

    return dec


class CommandsExecutor:
    def __init__(self, library, loop):
        self._lib: MusicLibrary = library
        self._loop = loop
        self._running = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._loop.close()

    @command('ls')
    def show_library(self):
        self._lib.show_library()

    @command('aa', 'Enter path to album', ArgsParser(str))
    def add_album(self, album):
        self._lib.add_album(album)

    @command('af', 'Enter path to folder with music', ArgsParser(str))
    def extract_all_albums_from_folder(self, folder):
        self._lib.add_folder(folder)

    @command('e', 'Enter path to music player folder', ArgsParser(str))
    def export_library_to_player(self, folder):
        self._lib.export(folder)

    @command('b', 'Enter space-separated login and pass from yandex disk', ArgsParser(str, str),
             input_func=lambda: getpass('>'))
    def upload_library_to_yandex_disk(self, login, password):
        uploader = Uploader(login, password)
        uploader.upload(self._lib.location)

    @command('t')
    def show_recommended_albums(self):
        nickname = settings['last_fm_nickname']
        if nickname == '':
            nickname = ui.get_input_from_user('Enter last.fm nickname')

        last_fm = LastFM(nickname)
        recommended = last_fm.get_recommended_albums(self._lib)
        indexes = [str(i + 1) for i in range(len(recommended))]
        indexes.append('ex')
        options = [str(a) for a in recommended]
        options.append('abort operation')
        i, _ = ui.choose('Top albums of the week not included in library\nDownload some?', options, indexes)
        if i == len(recommended):
            return
        self._loop.run_until_complete(download_album_to_lib_async(recommended[i], self._lib))

    @command('d', 'Enter performer and album title', ArgsParser(str, str))
    def download_album(self, performer, title):
        last_fm = LastFM()
        album = last_fm.search_album(performer, title)
        self._loop.run_until_complete(download_album_to_lib_async(album, self._lib))

    @command('ex')
    def save_library_and_exit(self):
        self._running = False

    def start(self):
        self._running = True
        while self._running:
            options = []
            indexes = []
            for k, v in available_commands.items():
                _, msg = v
                options.append(msg)
                indexes.append(k)

            idx, _ = ui.choose('Choose command', options, indexes)
            try:
                available_commands[indexes[idx]][0](self)
            except Exception as e:
                ui.show(str(e))
