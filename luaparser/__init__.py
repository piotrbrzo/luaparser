# coding=utf-8

"""Lua parser for CS325."""

from luaparser.lexer import Lexer
from luaparser.parser import Parser
from luaparser.types import ErrorStore


def parse(filename: str):
    """
    Preform lexing and parsing on the given file. Display errors or a list
    of declared functions in case of no errors.
    :param filename: Name of the file to parse.
    """
    e = ErrorStore(filename)
    l = Lexer(e)
    p = Parser(e, l.lexer())

    p.parser()
