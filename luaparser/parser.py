# coding=utf-8

"""Lua parser for CS325."""

from luaparser.types import TokenIterator, Tokens, TokenType, ErrorStore
from difflib import SequenceMatcher


class EllipsisException(Exception):
    """When 'namelist()' encounters an ellipsis. Caught by funcbody()."""

    def __init__(self, msg: str, line: int, params: [str]):
        """
        :param msg: Message to be displayed to the user.
        :param line: The line number of the token creating the exception.
        :param params: List of names in the namelist so far.
        """
        super().__init__(msg, line)
        self._params = params

    @property
    def get_params(self):
        return self._params


class EndOfScopeException(Exception):
    """When 'varorfunctioncall()' encounters a word similar to an end
    of scope."""


class Parser:
    """Class for turning a TokenIterator into a list of errors or declared
    functions in case of no errors."""

    def __init__(self, e: ErrorStore, ti: TokenIterator):
        self._functions = dict([])  # All functions declared so far.
        self._lastfunction = ""  # Name of the functions being declared.
        self._unnamed_function = 0  # Number of declared unnamed functions.
        self._e = e  # ErrorStore.
        self._t = Tokens(ti)  # Iterator over tokens.

        # Constant setting of how similar two strings must be
        # to be considered a typo.
        self.SIMILAR = 0.65

    def e(self, expected: str, msg="expected"):
        """
        Store an error at the current location. If similar to the expected
        value, increment iterator.
        :param expected: A token value which was expected instead
        of the current one.
        :param msg: Optional message to be displayed to the user.
        """
        if expected != "":
            msg = "'" + expected + "' " + msg
            if SequenceMatcher(None, self.t.get_t, expected).ratio() \
                    > self.SIMILAR:
                self.t.next()

        msg = "'" + str(self.t.get_t) + "' not expected. " + msg + "."
        self._e.report(self.t.line, msg)

    def e_set(self, expectation: set, increment: bool, msg="") -> str:
        """
        Store an error at the current location. If similar to an expected
        value, return value.
        :param expectation: A set of token values, one of which was expected
        instead of the current one.
        :param increment: If True increment iterator if matched.
        :param msg: Message to be displayed to the user.
        :return: Keyword matched or "" if none matched.
        """
        best_match = ""

        if len(expectation) > 0:
            maximum = 0
            for expected in expectation:
                if expected is not None:
                    temp = SequenceMatcher(None, self.t.get_t, expected) \
                        .ratio()

                if temp > maximum:
                    maximum = temp
                    best_match = expected

            if maximum <= self.SIMILAR:
                best_match = ""
            elif increment:
                self.t.next()
        if msg != "":
            msg += "."
            self._e.report(self.t.line, msg)
        return best_match

    def var(self):
        """Parse Lua var."""
        if not self.varorfunctioncall(False, set()):
            self.e("", "Variable expected")

    def index(self):
        """Parse Lua index."""
        if self.t.match("."):
            self.name()

        elif self.t.match("["):
            self.exp()
            if self.t.nmatch("]"):
                self.e("]")

        else:
            self.e("", "'.' or '[' expected")

    def tableconstructor(self):
        """Parse Lua tableconstructor."""
        if self.t.nmatch("{"):
            self.e("{")

        if self.t.nmatch("}"):
            self.field()
            while self.t.match_set({',', ';'}):
                if self.t.get_t == "}":
                    break
                self.field()

            if self.t.nmatch("}"):
                self.e("}")

    def call(self):
        """Parse Lua call."""
        if self.t.match(":"):
            self.name()

        if self.t.nmatch_type(TokenType.str):
            if self.t.match("("):
                if self.t.nmatch(")"):
                    self.explist()
                    if self.t.nmatch(")"):
                        self.e(")")

            elif self.t.get_t == "{":
                self.tableconstructor()

            else:
                self.e("", "'(', '{' or a string expected")

    def field(self):
        """Parse Lua field."""
        if self.t.match("["):
            self.exp()
            if self.t.nmatch("]"):
                self.e("]")

        elif self.t.get_tt is TokenType.name and self.t.lookahead == "=":
            self.t.next()
            self.t.next()
            self.exp()

        else:
            self.exp()

    def sufix(self):
        """Parse Lua sufix."""
        if self.t.nmatch_type(TokenType.str):
            if self.t.match_set({'[', '.'}):
                self.index()

            else:
                self.call()

    def prefix(self):
        """Parse Lua prefix."""
        if self.t.match("("):
            self.exp()
            if self.t.nmatch(")"):
                self.e(")")

        else:
            self.name()

    def value(self):
        """Parse Lua value."""
        if self.t.nmatch_set({"nil", "false", "true", "..."}) \
                and self.t.nmatch_type(TokenType.num) \
                and self.t.nmatch_type(TokenType.str):

            if self.t.match("function"):
                self.funcbody()

            elif self.t.get_t == "{":
                self.tableconstructor()

            else:
                self.varorfunctioncall(True, set())

    def explist(self):
        """Parse Lua explist."""
        self.exp()
        if self.t.match(","):
            self.exp()

    def funcbody(self):
        """Parse Lua funcbody and save function parameters."""
        if self._lastfunction == "":
            # Unnamed Function.
            self._lastfunction += "Unnamed function " + \
                                  str(self._unnamed_function) + \
                                  " on line " + str(self.t.line)
            self._unnamed_function += 1

        if self._lastfunction in self._functions:
            self.e("", "Function '" + self._lastfunction +
                   "' defined multiple times")

        self._functions[self._lastfunction] = []

        if self.t.nmatch("("):
            self.e("(", "expected in function '" + self._lastfunction + "'")

        if self.t.nmatch(")"):
            if self.t.match("..."):
                self._functions[self._lastfunction].append("...")

            else:
                try:
                    self._functions[self._lastfunction] += self.namelist()

                except EllipsisException as e:
                    self._functions[self._lastfunction] += e.get_params
                    self._functions[self._lastfunction].append("...")

            if self.t.nmatch(")"):
                self.e(")", "expected in function '" + self._lastfunction +
                       "'")

            self._lastfunction = ""
            self.chunk({"end"})

    def namelist(self) -> [str]:
        """
        Parse Lua namelist.
        :return: List of encountered names.
        """
        temp = [self.name()]
        while self.t.match(","):
            if self.t.match("..."):
                raise EllipsisException("'...' encountered in namelist",
                                        self.t.line, temp)

            temp.append(self.name())
        return temp

    def name(self) -> str:
        """
        Parse Lua name.
        :return: The encountered name.
        """
        temp = self.t.get_t
        if self.t.nmatch_type(TokenType.name):
            self.e("", "'" + temp + "' is not a valid name")

        return temp

    def funcname(self):
        """Parse Lua funcname and save it."""
        self._lastfunction = ""
        self._lastfunction += self.name()
        while self.t.match("."):
            self._lastfunction += "."
            self._lastfunction += self.name()

        if self.t.match(":"):
            self._lastfunction += ":"
            self._lastfunction += self.name()

    def exp(self):
        """Parse Lua exp."""
        if self.t.match_set({"-", "not", "#"}):
            self.exp()

        else:
            self.value()
            binop = {'+', '-', '*', '/', '^', '%', '..', '<', '<=', '>', '>=',
                     '==', '~=', 'and', 'or'}

            if self.t.match_set(binop):
                self.exp()

    def stat(self, cond: set):
        """
        Parse Lua stat.
        :param cond: Set of strings, which could end the scope of the current
        chunk.
        """
        if self.t.match("do"):
            self.chunk({"end"})

        elif self.t.match("while"):
            self.exp()
            if self.t.nmatch("do"):
                self.e("do", "not found after 'while'")

            self.chunk({"end"})

        elif self.t.match("repeat"):
            self.chunk({"until"})
            self.exp()

        elif self.t.match("if"):
            self.exp()
            if self.t.nmatch("then"):
                self.e("then", "not found after 'if'")

            temp = self.chunk({"elseif", "else", "end"})
            while temp == "elseif":
                self.exp()
                if self.t.nmatch("then"):
                    self.e("then", "not found after 'else'")
                temp = self.chunk({"elseif", "else", "end"})
            if temp == "else":
                self.chunk({"end"})

        elif self.t.match("function"):
            self.funcname()
            self.funcbody()

        elif self.t.match("local"):
            if self.t.match("function"):
                self._lastfunction = self.name()
                self.funcbody()
            else:
                try:
                    self.namelist()
                except EllipsisException as e:
                    self.e("", e.args[0])
                if self.t.match("="):
                    self.explist()

        elif self.t.match("for"):
            self.name()
            if self.t.match("="):
                self.exp()
                if self.t.nmatch(","):
                    self.e(",", "expected in 'for' loop")

                self.exp()
                if self.t.match(","):
                    self.exp()
            else:
                while self.t.match(","):
                    self.name()

                if self.t.nmatch("in"):
                    self.e("in", "expected in 'for' loop")

                self.explist()

            if self.t.nmatch("do"):
                self.e("do", "expected in 'for' loop")

            self.chunk({"end"})

        elif self.varorfunctioncall(False, cond):
            # varlist
            while self.t.match(','):
                self.var()

            if self.t.match('='):
                self.explist()

            else:
                self.e('=')

    def varorfunctioncall(self, exp: bool, cond: set) -> bool:
        """
        Parse a Lua var, functioncall or '(' exp ')'.
        :param exp: True if '(' exp ')' production permitted.
        :param cond: Set of strings, which could end the scope of the current
        chunk.
        :return: True if is var.
        """
        name = False
        t, tt = self.t.lookahead_ttt

        if self.t.get_tt is TokenType.name:
            if t in {",", "="}:
                self.t.next()
                return True
            name = True

        elif self.t.match("("):
            self.exp()
            if self.t.get_t != ")":
                self.e(")")

        else:
            self.e("", "Name or '(' expected")
            self.t.next()
            return False
        # prefix done.

        isvar = False

        if t in {'[', '.'}:
            self.t.next()
            self.index()
            isvar = True

        elif t in {'(', '{', ':'} or tt is TokenType.str:
            self.t.next()
            self.call()
            isvar = False

        elif exp:
            self.t.next()
            return False
        else:
            if name:
                best_match = self.e_set(cond, False)
                if best_match != "":
                    self._e.report(self.t.line, "Typo in '" + self.t.get_t +
                                   "' - should probably be '" + best_match +
                                   "'.")
                    self.t.next()
                    raise EndOfScopeException(best_match)

                best_match = self.e_set({"do", "while", "repeat", "if", "for",
                                         "function", "local"}, False)

                if best_match != "":
                    self._e.report(self.t.line, "Typo in '" + self.t.get_t +
                                   "' - should probably be '" + best_match +
                                   "'.")
                    self.t.set_t(best_match, TokenType.key)
                    return False

            self.t.next()
            self.e("", "'[', '.', '(', '{', ':' or a string expected")

        while True:
            if self.t.get_t in {'[', '.'}:
                self.index()
                isvar = True

            elif self.t.get_t in {'(', '{', ':'} \
                    or self.t.get_tt is TokenType.str:
                self.call()
                isvar = False

            else:
                return isvar

    def chunk(self, cond: set) -> str:
        """
        Parse a Lua chunk.
        :param cond: Set of tokens, which can close this chunk.
        :return: The last token of the chunk.
        """
        broken = False
        while self.t.get_t not in cond:
            if self.t.get_t is None:
                self.e("", "Scope not closed")
                return ""
            if broken:
                return self.e_set(cond, True, "Scope not closed after 'break' "
                                              "or 'return'")
            if self.t.match("break"):
                broken = True
            elif self.t.match("return"):
                broken = True
                if self.t.get_t not in cond and not self.t.empty:
                    self.explist()
            else:
                try:
                    self.stat(cond)
                except EndOfScopeException as e:
                    return e.args[0]
            self.t.match(';')

        temp = self.t.get_t
        self.t.next()
        return temp

    def parser(self):
        """Displays a list of errors or declared functions
        in case of no errors."""
        try:
            self.chunk({"end", None})
        except EllipsisException as e:
            self.e("", e.args[0])

        if self._e.error_count:
            self._e.print_errors()
        else:
            print("No errors found")
            for f in sorted(self._functions):
                print(f, self._functions[f])

    @property
    def t(self):
        """Gets the Tokens object for this class."""
        return self._t
