import os
from ui import ui


def with_upper_first_letter(string):
    return string[0].upper() + string[1:]


def get_size(start_path='.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


class ProgressTracker:
    def __init__(self, total_size, msg):
        self._pb = ui.get_progress_bar(msg)
        self._current = 0
        self._total_size = total_size
        self._closed = False

    def add_progress(self, count):
        if self._closed:
            return
        self._current += count
        percent = self._current / self._total_size * 100
        if percent > 99:
            return
        self._pb.print_progress_bar(percent)

    def reset(self, total_size=None, msg=None):
        self._closed = False
        self._current = 0
        if msg is not None:
            self._pb = ui.get_progress_bar(msg)
        if total_size is not None:
            self._total_size = total_size

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._pb.print_progress_bar(100)
        ui.show('')
