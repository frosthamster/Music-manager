from json import load

with open('settings.json') as f:
    settings = load(f)


def extract_value(key):
    if settings[key] != '':
        return settings[key]
    raise ValueError(f'Not found {key} in settings.json')


def get_last_fm_api_key():
    return extract_value('last_fm_api_key')


def get_google_api_key():
    return extract_value('google_api_key_with_youtube_support')
