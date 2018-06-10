__all__ = ['Track']


class Track:
    def __init__(self, name, path, offset='00:00:00'):
        self.name = name
        self.path = path
        self.offset = offset

    def __str__(self):
        return f'{self.name:30} located at [{self.offset}] {self.path}'

    def __repr__(self):
        return str(self)
