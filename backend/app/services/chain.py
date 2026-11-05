"""Pattern: Iterator (base for both Chain of Responsibility pipelines).

``ChainLink`` stores the successor and makes the whole chain iterable from
any link, so handlers are walked with a plain ``for`` loop instead of
recursion, and a chain can be inspected or reordered in tests.
"""
from typing import Iterator


class ChainLink:
    def __init__(self) -> None:
        self._next = None

    def then(self, following):
        self._next = following
        return following

    def __iter__(self) -> Iterator:
        link = self
        while link is not None:
            yield link
            link = link._next
