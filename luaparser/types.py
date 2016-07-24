# coding=utf-8
"""Type definitions."""

from enum import Enum
import itertools

try:
    from typing import Iterator, Tuple, Sequence
except ImportError:
    class DummyType(type):
        """Metaclass used to provide backward compatibility with Python 3.4."""

        def __getitem__(self, item):
            return item


    class Sequence(metaclass=DummyType):
        """Class used to provide backward compatibility with Python 3.4."""
        pass


    class Tuple(metaclass=DummyType):
        """Class used to provide backward compatibility with Python 3.4."""
        pass


    class Iterator(metaclass=DummyType):
        """Class used to provide backward compatibility with Python 3.4."""
        pass


class TokenType(Enum):
    """All the possible TokenTypes."""
    name = 1
    str = 2
    num = 3
    key = 4
    sym = 5
    invalid = 6


# Iterates over input file - stores tuples containing the current line number,
# the current character and the rest of the characters.
LexIterator = Iterator[Tuple[int, str, str]]

# Iterates over tokens - stores tuples containing the current token, its type
# and the line it was on in the original file.
TokenIterator = Iterator[Tuple[str, TokenType, int]]


class Tokens:
    def __init__(self, tokens: TokenIterator):
        """
        Initializes Tokens by storing the iterator and the first token.
        :param tokens: Iterator yielding tokens, their types and their line
        numbers in the input file.
        """
        self._tokens = tokens
        self._t, self._tt, self._line = next(self._tokens, (None, None, None))

    def next(self):
        """Increment the iterator."""
        self._t, self._tt, self._line = next(self._tokens, (None, None, None))

    def match(self, s: str) -> bool:
        """
        Increment iterator if string matches token.
        :param s: String to match against current token.
        :return: True if string matched.
        """
        if self._t == s:
            self.next()
            return True
        return False

    def nmatch(self, s: str) -> bool:
        """
        Increment iterator if string matches token.
        :param s: String to match against current token.
        :return: False if string matched.
        """
        return not self.match(s)

    def match_type(self, tt: TokenType) -> bool:
        """
        Increment iterator if 'tt' matches the type of the current token.
        :param tt: TokenType to match against the current one.
        :return: True if string matched.
        """
        if self._tt is tt:
            self.next()
            return True
        return False

    def nmatch_type(self, tt: TokenType) -> bool:
        """
        Increment iterator if 'tt' matches the type of the current token.
        :param tt: TokenType to match against the current one.
        :return: False if string matched.
        """
        return not self.match_type(tt)

    def match_set(self, s: set) -> bool:
        """
        If a string is matched the iterator is incremented.
        :param s: Set of strings.
        :return: True if current token matches any of the strings in 's'.
        """
        if self._t in s:
            self.next()
            return True
        return False

    def nmatch_set(self, s: set) -> bool:
        """
        If a string is matched the iterator is incremented.
        :param s: Set of strings.
        :return: True if current token does not match any
        of the strings in 's'.
        """
        return not self.match_set(s)

    def set_t(self, t: str, tt: TokenType):
        """
        Sets current token to given values.
        :param t: Token text.
        :param tt: Token type.
        """
        self._t = t
        self._tt = tt

    @property
    def lookahead(self) -> str:
        """Get next token value."""
        self._tokens, tokens = itertools.tee(self._tokens)
        t, tt, line = next(tokens)
        return t

    @property
    def lookahead_ttt(self) -> Tuple[str, TokenType]:
        """Get next token value and type."""
        self._tokens, tokens = itertools.tee(self._tokens)
        t, tt, line = next(tokens)
        return t, tt

    @property
    def get_t(self) -> str:
        """Get current token string."""
        return self._t

    @property
    def get_tt(self) -> TokenType:
        """Get current token's TokenType."""
        return self._tt

    @property
    def empty(self):
        """True if all tokens have been processed."""
        return self._t is None

    @property
    def line(self):
        """Returns line number of token."""
        return self._line


class ErrorStore:
    """Used for storing all encountered errors."""

    def __init__(self, filename):
        """
        :param filename: Name of the file to parse.
        """
        self._count = 0
        self._list = []
        self._filename = filename

    def report(self, line: int, message: str):
        """
        Store an error.
        :param line: The line number of the token creating the error.
        :param message: Message to be displayed to the user.
        """
        self._count += 1
        self._list.append((line, message))

    def print_errors(self):
        """Display all stored errors in order of detection."""
        print("Errors found")
        for line, message in self._list:
            if line is None:
                print("EOF: " + message)
            else:
                print(str(line) + ": " + message)

    @property
    def error_count(self) -> bool:
        """Get the number of errors that have occured so far."""
        return self._count

    @property
    def filename(self) -> str:
        """Get the name of the file being parsed."""
        return self._filename
