from typing import List
from os.path import join
from .track import Track

__all__ = ['Album']


class Album:
    def __init__(self, performer, year, name, tracks=None, cue_name: str = None, cover_name: str = None):
        self.performer = performer
        self.name = name
        self.year = year
        self.tracks: List[Track] = tracks
        self.cue_name = cue_name
        self.cover_name = cover_name

    def get_location(self, root):
        return root.joinpath(self.performer, repr(self))

    @property
    def location(self):
        return join(self.performer, repr(self))

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f'{self.year} - {self.name}'

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.name.lower() == other.name.lower() and self.year == other.year

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.name.lower()) ^ 397 + hash(self.year)
