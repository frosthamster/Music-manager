from ui import ui
from os import remove
from utils import get_size
from shutil import make_archive
from .ya_disk import YaDiskWithProgress
from YaDiskClient.YaDiskClient import YaDiskException

__all__ = ['Uploader']


class Uploader:
    root_folder = 'music library'

    def __init__(self, login, password):
        self._disk = YaDiskWithProgress(login, password)
        try:
            self._available_space = int(self._disk.df()['available'])
        except YaDiskException as e:
            if e.code == 401:
                raise ValueError('Incorrect auth information') from e

        if self.root_folder not in [p['displayname'] for p in self._disk.ls('/')]:
            self._disk.mkdir(self.root)

    @property
    def root(self):
        return f'/{self.root_folder}'

    def upload(self, folder):
        size = get_size(folder)
        if size > self._available_space:
            raise ValueError('Not enough space')
        ui.show('Zipping library')
        archive = make_archive('__library__', 'zip', root_dir=folder)
        ui.show('Successfully zipped')
        ui.show('Start uploading')
        self._disk.upload(archive, f'{self.root}/library.zip')
        remove(archive)
