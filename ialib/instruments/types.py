from typing import Any, Protocol


class InstrumentInterface(Protocol):
    def write(self, data: str) -> Any:
        ...

    def read(self) -> str:
        ...

    def query(self, data: str) -> str:
        ...
