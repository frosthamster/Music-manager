import os
from ui import ui
from utils import ProgressTracker

__all__ = ['ChunkPartitioner']


class ChunkPartitioner(object):
    def __init__(self, filename, msg, chunk_size=8 * 1024):
        self._filename = filename
        self._chunk_size = chunk_size
        self._total_size = os.path.getsize(filename)
        self._tracker = ProgressTracker(self._total_size, msg)

    def __iter__(self):
        with open(self._filename, 'rb') as file:
            while True:
                data = file.read(self._chunk_size)
                if not data:
                    self._tracker.close()
                    break
                self._tracker.add_progress(len(data))
                yield data

    def __len__(self):
        return self._total_size
