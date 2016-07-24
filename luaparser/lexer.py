# coding=utf-8
"""Lua lexer for CS325."""

import re
from luaparser.types import Tuple, TokenType, LexIterator, TokenIterator, \
    ErrorStore


class LexEx(Exception):
    """All lexing errors extend this class"""

    @property
    def msg(self):
        """Get the message passed in the error."""
        try:
            return self.args[0]
        except IndexError:
            return ""


class Lexer:
    """Class for turning a file into tokens."""

    def __init__(self, e: ErrorStore):
        self._e = e  # ErrorStore.
        self._line = 0  # Current line number.
        self._iterator = self.iterator()  # Iterator over file.
        self._skip = 0  # Number of letters to skip iterating over.

    def e(self, msg: str):
        """
        Store an error at the current location.
        :param msg: Message to be displayed to the user.
        """
        self._e.report(self._line, msg)

    def iterator(self) -> LexIterator:
        """
        Get an iterator for the file.
        :return: Iterator over input file.
        """
        line_number = 1
        increment_line_number = False

        with open(self._e.filename) as file:
            source = file.read()

        for position, character in enumerate(source):
            if increment_line_number:
                increment_line_number = False
                line_number += 1

            if character == '\n':
                increment_line_number = True

            yield line_number, character, source[position:]

    def string(self, source: str) -> Tuple[str, TokenType]:
        """
        Check if the beginning of the input has a valid Lua string.
        :param source: A string of characters.
        :return: The Lua string and its token type.
        """
        bracket = source[0]
        val = source[1:]
        token = bracket

        if bracket == '[':
            # Long string.
            try:
                bracket, val = val.split('[', 1)
            except ValueError:
                self.e("String does not have a second '[' symbol.")
                bracket = ""
                for c in val:
                    if c != "=":
                        break
                    bracket += "="
                val = val[len(bracket):]
                self._skip -= 1

            if set(bracket) != {'='} and bracket != "":
                self.e("Symbols other than '=' between initial '['.")
                temp = ""
                for _ in bracket:
                    temp += "="
                bracket = temp

            token += bracket + '['
            bracket = ']' + bracket + ']'

            val = val.split(bracket, 1)

            if len(val) == 1:
                self.e("String not closed.")
                val = val[0].split()
                if len(val) == 0:
                    val = ['']
                self._skip -= len(bracket)

            token += val[0] + bracket

            if len(token.split("[" + bracket[1:-1] + "[")) > 2:
                self.e("Long brackets are nested.")

            return token, TokenType.str
        else:
            escaped = False  # True if the previous character was an escape.

            for c in val:
                if escaped:
                    escapes = {'a', 'b', 'f', 'n', 'r', 't', 'v', '\\', '\"',
                               '\''}
                    if c not in escapes and not re.match('[0-9]', c):
                        self.e("Illegal escape in string.")
                        token += "\\"
                        self._skip -= 1
                    escaped = False

                elif c == '\\':
                    escaped = True

                elif c == bracket:
                    return token + bracket, TokenType.str

                token += c

            self.e("String not closed.")
            token = token.split()
            if len(token) == 0:
                token = ['']
            self._skip -= len(bracket)
            return token[0] + bracket, TokenType.str

    def number(self, source: str) -> Tuple[str, TokenType]:
        """
        Check if the beginning of the input has a valid Lua number.
        :param source: A string of characters.
        :return: The Lua number and its token type.
        """
        token = ""

        if source.startswith("0x"):
            # Hexadecimal.
            token = "0x"
            for c in source[2:]:
                if not re.match('[0-9a-fA-F]', c):
                    break
                token += c

        else:
            decimal = False  # The '.' character has been encountered.
            exponent = False  # 'E' or 'e' have been encountered.
            after_exponent = False  # 'E' or 'e' have just been encountered.

            for c in source:
                if not after_exponent and c in {'+', '-'}:
                    break
                after_exponent = False

                try:
                    if c == '.':
                        if decimal:
                            raise LexEx("Decimal point occurs multiple times.")
                        decimal = True

                    elif c in {'e', 'E'}:
                        if exponent:
                            raise LexEx("Multiple exponents in number.")
                        exponent = True
                        after_exponent = True

                    elif not re.match('[0-9]', c) and c not in {'+', '-'}:
                        break

                    token += c
                except LexEx as e:
                    self.e(e.msg)
                    self._skip += 1

        return token, TokenType.num

    @staticmethod
    def name(source: str) -> Tuple[str, TokenType]:
        """
        Check if the beginning of the input has a valid Lua name or keyword.
        :param source: A string of characters.
        :return: The Lua name or keyword and its token type.
        """
        keywords = {'and', 'break', 'do', 'else', 'elseif', 'end', 'false',
                    'for', 'function', 'if', 'in', 'local', 'nil', 'not', 'or',
                    'repeat', 'return', 'then', 'true', 'until', 'while'}
        token = ""

        for c in source:
            if not re.match('[0-9a-zA-Z_]', c):
                break
            token += c

        if token in keywords:
            return token, TokenType.key
        else:
            return token, TokenType.name

    def symbols(self, source: str) -> Tuple[str, TokenType]:
        """
        Check if the beginning of the input has a valid Lua symbol.
        :param source: A string of characters.
        :return: The Lua symbol and its token type.
        """
        symbols = {"+", "-", "*", "/", "%", "^", "#", "(", ")", "{", "}", "[",
                   "]", ";", ":", ","}

        if source[0] in symbols:
            return source[0], TokenType.sym

        long_symbols = ["...", "..", ".", "==", "~=", "<=", "=", ">=", "<",
                        ">"]
        for symbol in long_symbols:
            if source.startswith(symbol):
                return symbol, TokenType.sym

        self.e("'" + source[0] + "' does not start a valid token.")
        return source[0], TokenType.invalid

    def skip(self, n: int):
        """
        Increment the iterator.
        :param n: The number of times in addition to 'self._skip' the iterator
        should be incremented.
        """
        while n + self._skip:
            next(self._iterator)
            n -= 1

        self._skip = 0

    def lexer(self) -> TokenIterator:
        """
        Performs lexing and returns an iterator over tokens.
        :return: An iterator over tokens.
        """
        for self._line, character, remainder in self._iterator:
            if character.isspace():
                continue

            elif re.match('[a-zA-Z_]', character):
                token, token_type = self.name(remainder)

            elif re.match('[0-9]', character):
                token, token_type = self.number(remainder)

            elif (character == '"' or
                    character == '\'' or
                    remainder.startswith('[=') or
                    remainder.startswith('[[')):
                token, token_type = self.string(remainder)

            else:
                token, token_type = self.symbols(remainder)

            self.skip(len(token) - 1)

            if token_type != TokenType.invalid:
                yield token, token_type, self._line
