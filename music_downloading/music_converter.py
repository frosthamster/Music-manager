from os import devnull
from pathlib import Path
from ffmpy3 import FFmpeg

__all__ = ['convert_to_audio_async']


async def convert_to_audio_async(src: Path, dest_folder: Path, audio_format='mp3'):
    if not src.exists():
        raise FileNotFoundError(src)
    if not dest_folder.exists():
        raise FileNotFoundError('Not found output dir')

    dest = dest_folder.joinpath(f'{src.stem}.{audio_format}').absolute()
    src = src.absolute()

    ff = FFmpeg(
        inputs={str(src): '-y'},
        outputs={str(dest): f'-f {audio_format}'}
    )

    with open(devnull, 'w') as nul:
        await ff.run_async(stdout=nul, stderr=nul)
        await ff.wait()
