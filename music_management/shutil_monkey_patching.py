import shutil

_callback = None


def copyfileobj(src, dst, length=16 * 1024):
    while True:
        buf = src.read(length)
        if not buf:
            break
        dst.write(buf)
        _callback(length)


def patch_shutil(on_chunk_write_callback):
    global _callback
    if _callback is None:
        shutil.copyfileobj = copyfileobj
    _callback = on_chunk_write_callback
