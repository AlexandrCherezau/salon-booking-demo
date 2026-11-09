"""Server-rendered admin page (local demo, no auth). All values are escaped."""

from collections import Counter
from datetime import date
from html import escape

from .catalog import MASTERS_BY_ID, SERVICES_BY_ID

WEEKDAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")
MONTHS = ("янв", "фев", "мар", "апр", "мая", "июн",
          "июл", "авг", "сен", "окт", "ноя", "дек")


def _human_day(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1]}, {WEEKDAYS[d.weekday()]}"


def _row(b: dict) -> str:
    service = SERVICES_BY_ID.get(b["service_id"])
    master = MASTERS_BY_ID.get(b["master_id"])
    end = b["start_hour"] + b["hours"]
    cells = (
        f'<td class="num">#{b["id"]}</td>',
        f'<td><b>{escape(_human_day(b["day"]))}</b><br>'
        f'<span class="muted">{b["start_hour"]:02d}:00–{end:02d}:00</span></td>',
        f'<td>{escape(b["client_name"])}<br><span class="muted">{escape(b["phone"])}</span></td>',
        f'<td>{escape(service.title if service else b["service_id"])}</td>',
        f'<td>{escape(master.name if master else b["master_id"])}</td>',
        f'<td class="num">{service.price if service else 0:,} ₽</td>'.replace(",", " "),
        f'<td class="muted">{escape(b["comment"]) or "—"}</td>',
    )
    return "<tr>" + "".join(cells) + "</tr>"


def render_admin(bookings: list[dict]) -> str:
    total = sum(SERVICES_BY_ID[b["service_id"]].price
                for b in bookings if b["service_id"] in SERVICES_BY_ID)
    per_master = Counter(b["master_id"] for b in bookings)
    chips = "".join(
        f'<span class="chip">{escape(MASTERS_BY_ID[m].name)} · {n}</span>'
        for m, n in per_master.most_common() if m in MASTERS_BY_ID)
    rows = "".join(_row(b) for b in bookings) or (
        '<tr><td colspan="7" class="empty">Пока нет ни одной записи</td></tr>')
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Записи — Лён (демо)</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600&family=Manrope:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/admin.css">
</head><body>
<header class="bar"><a href="/" class="logo">Лён<span>·</span></a>
<span class="tag">Панель администратора · демо без авторизации</span></header>
<main>
<div class="head"><h1>Журнал записей</h1>
<div class="stats"><div><b>{len(bookings)}</b><span>записей</span></div>
<div><b>{total:,} ₽</b><span>сумма по прайсу</span></div></div></div>
<div class="chips">{chips}</div>
<div class="table-wrap"><table>
<thead><tr><th>№</th><th>Когда</th><th>Клиент</th><th>Услуга</th><th>Мастер</th><th>Цена</th><th>Комментарий</th></tr></thead>
<tbody>{rows}</tbody></table></div>
</main></body></html>""".replace(f"{total:,} ₽", f"{total:,} ₽".replace(",", " "))
