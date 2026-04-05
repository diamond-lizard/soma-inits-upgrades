"""Type stubs for unidiff -- only the API surface used by this project."""

from collections.abc import Iterable, Iterator

class Line:
    value: str
    is_removed: bool
    is_added: bool
    is_context: bool


class Hunk:
    def __iter__(self) -> Iterator[Line]: ...


class PatchedFile:
    def __iter__(self) -> Iterator[Hunk]: ...


class PatchSet:
    def __iter__(self) -> Iterator[PatchedFile]: ...
    def __init__(self, data: Iterable[str]) -> None: ...
    @classmethod
    def from_filename(
        cls, filename: str, encoding: str = "utf-8",
    ) -> PatchSet: ...
