"""Static catalogue of the demo salon: services, masters, working hours."""

from dataclasses import dataclass

OPEN_HOUR = 10
CLOSE_HOUR = 20  # last slot starts at CLOSE_HOUR - duration
BOOKING_HORIZON_DAYS = 30


@dataclass(frozen=True)
class Service:
    id: str
    title: str
    category: str
    price: int
    hours: int  # duration in whole one-hour slots
    note: str


@dataclass(frozen=True)
class Master:
    id: str
    name: str
    role: str
    years: int
    services: tuple[str, ...]
    bio: str


SERVICES: tuple[Service, ...] = (
    Service("cut-women", "Женская стрижка", "Волосы", 2400, 1, "с мытьём и укладкой"),
    Service("cut-men", "Мужская стрижка", "Волосы", 1600, 1, "машинка и ножницы"),
    Service("color", "Окрашивание в один тон", "Волосы", 5200, 2, "краситель без аммиака"),
    Service("airtouch", "Airtouch / балаяж", "Волосы", 9800, 3, "включая тонирование"),
    Service("manicure", "Маникюр с покрытием", "Ногти", 2200, 1, "гель-лак, 300+ оттенков"),
    Service("pedicure", "Педикюр SMART", "Ногти", 2900, 1, "диски, без замачивания"),
    Service("brows", "Брови: форма и окрашивание", "Лицо", 1300, 1, "хна или краска"),
    Service("care", "Уходовая процедура для лица", "Лицо", 3500, 1, "очищение и маска по типу кожи"),
)

MASTERS: tuple[Master, ...] = (
    Master("anna", "Анна Белова", "Колорист, стилист", 9,
           ("cut-women", "color", "airtouch"),
           "Любит натуральные оттенки и мягкие переходы."),
    Master("ilya", "Илья Соколов", "Барбер, стилист", 6,
           ("cut-men", "cut-women"),
           "Короткие стрижки, фейды, укладка за пять минут."),
    Master("vera", "Вера Ким", "Мастер ногтевого сервиса", 7,
           ("manicure", "pedicure"),
           "Аккуратная кутикула и покрытие, которое держится."),
    Master("olga", "Ольга Миронова", "Бровист, косметолог", 11,
           ("brows", "care"),
           "Подбирает форму бровей под черты лица."),
)

SERVICES_BY_ID = {s.id: s for s in SERVICES}
MASTERS_BY_ID = {m.id: m for m in MASTERS}
