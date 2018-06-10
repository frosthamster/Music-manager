from abc import ABC, abstractmethod
from typing import Tuple

from console_progressbar import ProgressBar

__all__ = ['ui', 'set_ui', 'ConsoleUI']


class AbstractProgressBar(ABC):
    @abstractmethod
    def print_progress_bar(self, percent):
        pass


class AbstractUI(ABC):
    @abstractmethod
    def get_input_from_user(self, msg, read_int=False, validation_func=None, input_func=None):
        pass

    @abstractmethod
    def show(self, msg):
        pass

    @abstractmethod
    def choose(self, msg, options, indexes=None) -> Tuple[int, str]:
        pass

    @abstractmethod
    def get_progress_bar(self, msg) -> AbstractProgressBar:
        pass

    def ask_ok(self, msg):
        return self.choose(msg, ['all right', 'abort operation'], ['ok', 'ex'])[0] == 0


class UIProxy:
    def __init__(self):
        self._ui = None

    def set_ui(self, concrete_ui):
        self._ui = concrete_ui

    def __getattr__(self, item):
        if self._ui is None:
            raise NotImplementedError('UI no specified. Call set_ui() before use module')
        return getattr(self._ui, item)


ui: AbstractUI = UIProxy()


def set_ui(concrete_ui):
    ui.set_ui(concrete_ui)


class ConsoleUI(AbstractUI):
    def get_progress_bar(self, msg) -> AbstractProgressBar:
        return ProgressBar(100, length=50, suffix=msg)

    def choose(self, msg, options, indexes=None) -> Tuple[int, str]:
        print(msg)
        if indexes is not None and len(indexes) != len(options):
            raise ValueError

        indexes_and_options = zip(range(len(options)) if indexes is None else indexes, options)
        print('\n'.join(f'[{i}] - {option}' for i, option in indexes_and_options))
        while True:
            result = input('>').strip()
            if indexes is not None:
                try:
                    result = indexes.index(result)
                    return result, options[result]
                except ValueError:
                    print(f'Choose index from {indexes}')
            elif result.replace('-', '', 1).isdigit():
                result = int(result)
                if 0 <= result < len(options):
                    return result, options[result]
                else:
                    print(f'Enter number in range [0, {len(options) - 1}]')
            else:
                return -1, result

    def show(self, msg):
        print(msg)

    def get_input_from_user(self, msg, read_int=False, validation_func=None, input_func=None):
        print(msg)
        if read_int:
            validation_func = lambda n: int(n)
        if input_func is None:
            input_func = lambda: input('>')

        while True:
            result = input_func().strip()

            if validation_func is not None:
                try:
                    result = validation_func(result)
                except ValueError as e:
                    self.show(str(e))
                    continue
            return result
