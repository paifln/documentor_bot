from __future__ import annotations

from enum import StrEnum


class Language(StrEnum):
    RU = "ru"
    KK = "kk"
    EN = "en"


class Severity(StrEnum):
    """Ordered from worst to best. Used for both rule-engine and AI findings."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    PASS = "pass"

    @property
    def emoji(self) -> str:
        return {
            Severity.CRITICAL: "🔴",
            Severity.ERROR: "🟠",
            Severity.WARNING: "🟡",
            Severity.INFO: "🔵",
            Severity.PASS: "🟢",
        }[self]


class FindingSource(StrEnum):
    RULE_ENGINE = "rule_engine"
    AI = "ai"


class FindingCategory(StrEnum):
    FORMATTING = "formatting"
    STRUCTURE = "structure"
    LANGUAGE = "language"
    STYLE = "style"
    CONTENT = "content"
    REFERENCES = "references"
    SYSTEM = "system"


class CheckStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentStatus(StrEnum):
    RECEIVED = "received"
    VALIDATED = "validated"
    PARSED = "parsed"
    REJECTED = "rejected"
    DELETED = "deleted"


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class WorkType(StrEnum):
    COURSEWORK = "coursework"
    DIPLOMA = "diploma"
    REPORT = "report"  # отчёт по практике
    ESSAY = "essay"  # реферат


class PageOrientation(StrEnum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class Alignment(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    JUSTIFY = "justify"
    ANY = "any"
