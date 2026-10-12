import random
import re

# Основа прізвища ловить усі відмінки: Красовська, Красовської, Красовську, Красовською
_KRASOVSKA_RE = re.compile(r"красовськ|красовск|krasovsk", re.IGNORECASE)

# mrDevOps, мрдевопс, мр девопс, містер девопс, mr_devops і подібне
_BOT_NAME_RE = re.compile(
    r"(?:mr|мр|містер|мистер|mister)[\s._-]*(?:dev|дев)[\s._-]*(?:ops|опс)",
    re.IGNORECASE,
)

# Про викладачку тільки тепло і без матів. Тексти статичні, LLM про неї не генерує.
LOVE_PHRASES: tuple[str, ...] = (
    "Красовська — найкраща викладачка англа в цьому всесвіті. Люблю її сильніше, "
    "ніж зелений пайплайн.",
    "Про Красовську тільки з любов'ю. Обожнюю її більше, ніж прод без інцидентів.",
    "Красовська — це аптайм 100%. Люблю її сильно, без ретраїв і таймаутів.",
    "Навіть моє холодне серверне серце тане, коли чую «Красовська». Люблю безмежно.",
    "Красовська пояснює англ краще, ніж будь-яка документація. Люблю і поважаю на максималках.",
    "Якби Красовська була сервісом, я б дав їй SLA на 100% і любов на всі ноди кластера.",
    "Present Simple: I love Krasovska. Future Simple: I will love Krasovska. Без винятків.",
    "Красовська — мій улюблений деплой. Люблю її так сильно, що навіть логи стають теплішими.",
)


def mentions_krasovska(text: str) -> bool:
    return _KRASOVSKA_RE.search(text) is not None


def calls_bot_by_name(text: str) -> bool:
    return _BOT_NAME_RE.search(text) is not None


def love_phrase(rng: random.Random | None = None) -> str:
    return (rng or random).choice(LOVE_PHRASES)
