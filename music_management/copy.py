from os.path import getsize, abspath, basename
import shutil
from .shutil_monkey_patching import patch_shutil
from utils import ProgressTracker

__all__ = ['copy_with_progress']


def copy_with_progress(src, dest):
    src = abspath(src)
    dest = abspath(dest)
    size = getsize(src)
    tracker = ProgressTracker(size, f'Copying {basename(src)}')
    patch_shutil(tracker.add_progress)
    shutil.copy2(src, dest)
    tracker.close()
