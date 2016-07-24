#!/usr/bin/env python3
# coding=utf-8

from luaparser import parse

if __name__ == "__main__":
    import sys

    try:
        filename = sys.argv[1]
    except IndexError:
        print("Give filename:")
        filename = input()

    try:
        parse(filename)
    except FileNotFoundError:
        print("File does not exist")
