import time
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class Capacity:
    current: int
    total: int


@dataclass(frozen=True, slots=True)
class Progress:
    current: int
    total: int


class Duration(int):
    def __new__(cls, duration: int):
        return super().__new__(cls, duration)

    @classmethod
    def from_now(cls, timestamp: TimeStamp) -> Self:
        return cls(timestamp - TimeStamp.now())

    @classmethod
    def to_now(cls, timestamp: TimeStamp) -> Self:
        return cls(TimeStamp.now() - timestamp)

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"


class TimeStamp(int):
    def __new__(cls, timestamp: int):
        return super().__new__(cls, timestamp)

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"

    @classmethod
    def now(cls) -> Self:
        return cls(int(time.time()))
