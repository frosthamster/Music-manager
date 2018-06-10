import sys
import logging
import asyncio
import argparse
from pathlib import Path

from settings import settings
from music_management import MusicLibrary
from commands_executor import CommandsExecutor
from ui import set_ui, ConsoleUI, ui


def parse_args():
    parser = argparse.ArgumentParser('Music manager')
    parser.add_argument('-l', '--library', help='path to library')
    return parser.parse_args()


def get_library_location(args):
    if args.library is not None:
        return args.library
    return settings['library_location']


def main():
    args = parse_args()
    logging.basicConfig(format='%(message)s', level=logging.INFO)
    set_ui(ConsoleUI())

    if sys.platform == 'win32':
        asyncio.set_event_loop(asyncio.ProactorEventLoop())
    loop = asyncio.get_event_loop()

    lib_location = get_library_location(args)
    if lib_location == '' or not Path(lib_location).exists():
        ui.show('Not found library, specify it in settings.json or pass through arguments')
        sys.exit(1)

    with MusicLibrary(lib_location) as ml:
        ui.show(f'Library loaded [{lib_location}]')
        ml.show_library()
        with CommandsExecutor(ml, loop) as executor:
            executor.start()


if __name__ == '__main__':
    main()
