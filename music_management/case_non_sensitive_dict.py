from collections import defaultdict
from collections.abc import MutableMapping

__all__ = ['CaseNonSensitiveDict']


class CaseNonSensitiveDict(MutableMapping):
    def __init__(self, default_factory=None):
        self._dict = defaultdict(default_factory)

    def __delitem__(self, key):
        del self._dict[key]

    def __setitem__(self, key, value):
        self._dict[key.lower()] = value

    def __len__(self):
        return len(self._dict)

    def __getitem__(self, key):
        return self._dict[key.lower()]

    def __iter__(self):
        return iter(self._dict)

    def __contains__(self, item):
        return item.lower() in self._dict

    def copy(self):
        return self._dict.copy()
