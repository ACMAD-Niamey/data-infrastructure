from __future__ import annotations

from typing import Type


class ParserRegistry:
    _text_parsers: list[Type] = []
    _json_parsers: list[Type] = []

    @classmethod
    def register_text_parser(cls, parser_cls: Type):
        cls._text_parsers.append(parser_cls)
        return parser_cls

    @classmethod
    def register_json_parser(cls, parser_cls: Type):
        cls._json_parsers.append(parser_cls)
        return parser_cls

    @classmethod
    def get_text_parsers(cls) -> list[Type]:
        return cls._text_parsers

    @classmethod
    def get_json_parsers(cls) -> list[Type]:
        return cls._json_parsers