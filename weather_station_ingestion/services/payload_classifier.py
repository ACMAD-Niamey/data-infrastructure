from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ClassificationResult:
    payload_kind: str
    parser_name: str | None = None
    is_supported: bool = False
    notes: str | None = None


class BasePayloadClassifier(ABC):
    def __init__(
        self,
        notification_content_type: str | None,
        downloaded_content_type: str | None,
        content: bytes,
    ) -> None:
        self.notification_content_type = (notification_content_type or "").lower()
        self.downloaded_content_type = (downloaded_content_type or "").lower()
        self.content = content or b""

    @abstractmethod
    def matches(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def classify(self) -> ClassificationResult:
        raise NotImplementedError


class TextPlainClassifier(BasePayloadClassifier):
    def matches(self) -> bool:
        return (
            "text/plain" in self.downloaded_content_type
            or "text/plain" in self.notification_content_type
        )

    def classify(self) -> ClassificationResult:
        return ClassificationResult(
            payload_kind="text_plain",
            parser_name="text_payload_parser",
            is_supported=True,
            notes="Plain text payload detected.",
        )


class JSONClassifier(BasePayloadClassifier):
    def matches(self) -> bool:
        return (
            "application/json" in self.downloaded_content_type
            or "application/json" in self.notification_content_type
            or "json" in self.downloaded_content_type
            or "json" in self.notification_content_type
        )

    def classify(self) -> ClassificationResult:
        return ClassificationResult(
            payload_kind="json",
            parser_name="json_payload_parser",
            is_supported=True,
            notes="JSON payload detected.",
        )


class BUFRClassifier(BasePayloadClassifier):
    def matches(self) -> bool:
        if self.content[:4] == b"BUFR":
            return True

        return (
            "application/octet-stream" in self.downloaded_content_type
            or "application/octet-stream" in self.notification_content_type
        )

    def classify(self) -> ClassificationResult:
        if self.content[:4] == b"BUFR":
            return ClassificationResult(
                payload_kind="bufr",
                parser_name="bufr_parser",
                is_supported=True,
                notes="BUFR payload detected from content signature.",
            )

        return ClassificationResult(
            payload_kind="binary",
            parser_name=None,
            is_supported=False,
            notes="Generic binary payload detected from content type.",
        )


class BinaryClassifier(BasePayloadClassifier):
    def matches(self) -> bool:
        return bool(self.content) and not self.content[:4] == b"BUFR"

    def classify(self) -> ClassificationResult:
        return ClassificationResult(
            payload_kind="binary",
            parser_name=None,
            is_supported=False,
            notes="Binary payload detected but format is not yet recognized.",
        )


class UnsupportedClassifier(BasePayloadClassifier):
    def matches(self) -> bool:
        return True

    def classify(self) -> ClassificationResult:
        return ClassificationResult(
            payload_kind="unsupported",
            parser_name=None,
            is_supported=False,
            notes="Unsupported or unknown payload format.",
        )


class PayloadClassifierFactory:
    classifiers = [
        TextPlainClassifier,
        JSONClassifier,
        BUFRClassifier,
        BinaryClassifier,
        UnsupportedClassifier,
    ]

    @classmethod
    def classify(
        cls,
        notification_content_type: str | None,
        downloaded_content_type: str | None,
        content: bytes,
    ) -> ClassificationResult:
        for classifier_cls in cls.classifiers:
            classifier = classifier_cls(
                notification_content_type=notification_content_type,
                downloaded_content_type=downloaded_content_type,
                content=content,
            )
            if classifier.matches():
                return classifier.classify()

        return ClassificationResult(
            payload_kind="unsupported",
            parser_name=None,
            is_supported=False,
            notes="No classifier matched the payload.",
        )