from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TableContent:
    page: int
    headers: list[str]
    rows: list[list[str]]
    caption: str = ""


@dataclass
class PageContent:
    page: int
    text: str
    images: list[bytes] = field(default_factory=list)
    tables: list[TableContent] = field(default_factory=list)


@dataclass
class ExtractedContent:
    pages: list[PageContent]
    file_type: str


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, file_bytes: bytes) -> ExtractedContent:
        ...
