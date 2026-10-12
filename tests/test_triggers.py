import pytest

from bot.triggers import (
    LOVE_PHRASES,
    calls_bot_by_name,
    devops_topic,
    love_phrase,
    mentions_krasovska,
)


@pytest.mark.parametrize(
    "text",
    [
        "Красовська задала домашку",
        "КРАСОВСЬКА",
        "у красовської сьогодні пара",
        "передай Красовській привіт",
        "Красовською всі задоволені",
        "красовская",
        "Krasovska is the best",
    ],
)
def test_mentions_krasovska(text: str) -> None:
    assert mentions_krasovska(text)


def test_mentions_krasovska_ignores_other_text() -> None:
    assert not mentions_krasovska("красота, а не деплой")


@pytest.mark.parametrize(
    "text",
    [
        "мрдевопс, що таке kubernetes?",
        "МР ДЕВОПС ти тут?",
        "mrDevOps, скажи щось",
        "mr_devops як справи",
        "містер девопс, поясни ci",
        "Мр.Девопс привіт",
    ],
)
def test_calls_bot_by_name(text: str) -> None:
    assert calls_bot_by_name(text)


def test_calls_bot_by_name_ignores_plain_devops() -> None:
    assert not calls_bot_by_name("девопс знову все поламав")


def test_love_phrase_is_from_pool() -> None:
    assert love_phrase() in LOVE_PHRASES


@pytest.mark.parametrize(
    ("text", "topic"),
    [
        ("у нас знову впав докер", "docker"),
        ("под у crashloop", "kubernetes"),
        ("хто задеплоїв у пʼятницю?", "деплой"),
        ("пайплайн червоний", "ci/cd"),
        ("terraform apply все поламав", "інфраструктура"),
        ("сервер ліг", "інфраструктура"),
        ("глянь логи", "моніторинг"),
        ("на проді все горить", "прод"),
        ("я девопс, мені можна", "девопс"),
    ],
)
def test_devops_topic_detects_keywords(text: str, topic: str) -> None:
    assert devops_topic(text) == topic


@pytest.mark.parametrize(
    "text",
    ["хто йде на піцу?", "моя подруга прийде", "купив продукти", "подивись фільм", "ок"],
)
def test_devops_topic_ignores_regular_chat(text: str) -> None:
    assert devops_topic(text) is None
