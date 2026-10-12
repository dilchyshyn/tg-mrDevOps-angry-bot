from typing import Any

import pytest

from bot.classifier import Classifier, Verdict, parse_verdict


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"devops": true, "topic": "docker"}', Verdict(True, "docker")),
        ('Ось відповідь: {"devops": true, "topic": " k8s "}', Verdict(True, "k8s")),
        ('{"devops": false, "topic": ""}', Verdict(False, "")),
        ('{"devops": "yes"}', Verdict(False, "")),
        ('{"devops": true, "topic": 42}', Verdict(True, "")),
        ("немає json взагалі", Verdict(False, "")),
        ('{"devops": true, "topic": "x"', Verdict(False, "")),
        ("[1, 2, 3]", Verdict(False, "")),
        ("", Verdict(False, "")),
    ],
)
def test_parse_verdict(raw: str, expected: Verdict) -> None:
    assert parse_verdict(raw) == expected


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModels:
    def __init__(self, result: str | Exception) -> None:
        self._result = result
        self.calls: list[dict[str, Any]] = []

    async def generate_content(self, **kwargs: Any) -> _FakeResponse:
        self.calls.append(kwargs)
        if isinstance(self._result, Exception):
            raise self._result
        return _FakeResponse(self._result)


class _FakeAio:
    def __init__(self, result: str | Exception) -> None:
        self.models = _FakeModels(result)


class _FakeClient:
    def __init__(self, result: str | Exception) -> None:
        self.aio = _FakeAio(result)


async def test_classify_uses_llm_verdict() -> None:
    classifier = Classifier(_FakeClient('{"devops": true, "topic": "deploy"}'), "model")  # type: ignore[arg-type]
    assert await classifier.classify("катимо в пʼятницю") == Verdict(True, "deploy")


async def test_classify_api_error_is_negative() -> None:
    classifier = Classifier(_FakeClient(RuntimeError("boom")), "model")  # type: ignore[arg-type]
    assert await classifier.classify("будь-що") == Verdict(False, "")


async def test_classify_disables_thinking() -> None:
    client = _FakeClient('{"devops": true, "topic": "k8s"}')
    await Classifier(client, "model").classify("под впав")  # type: ignore[arg-type]
    config = client.aio.models.calls[0]["config"]
    assert config.thinking_config.thinking_budget == 0
