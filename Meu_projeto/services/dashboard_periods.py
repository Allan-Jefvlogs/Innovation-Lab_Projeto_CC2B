"""Calendário do gráfico: dias civis e meses em São Paulo, sem dados simulados."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


SP = ZoneInfo("America/Sao_Paulo")
PERIODS = {"7d": "Últimos 7 dias", "30d": "Últimos 30 dias", "12m": "Últimos 12 meses"}


def month_start(year: int, month: int, offset: int = 0) -> datetime:
    index = year * 12 + month - 1 + offset
    return datetime(index // 12, index % 12 + 1, 1, tzinfo=SP)


def period_bounds(period: str = "7d", now: datetime | None = None) -> tuple[str, str]:
    if period not in PERIODS:
        raise ValueError("Período inválido.")
    current = (now or datetime.now(SP)).astimezone(SP)
    if period == "12m":
        start, end = month_start(current.year, current.month, -11), month_start(current.year, current.month, 1)
    else:
        days = 7 if period == "7d" else 30
        start = datetime.combine(current.date() - timedelta(days=days - 1), datetime.min.time(), SP)
        end = datetime.combine(current.date() + timedelta(days=1), datetime.min.time(), SP)
    return start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat()


def expected_keys(period: str, date_from: str, date_to: str) -> list[str]:
    if period not in PERIODS:
        raise ValueError("Período inválido.")
    start = datetime.fromisoformat(date_from.replace("Z", "+00:00")).astimezone(SP)
    end = datetime.fromisoformat(date_to.replace("Z", "+00:00")).astimezone(SP)
    if start.hour or start.minute or start.second or start.microsecond:
        raise ValueError("Início deve ser meia-noite local.")
    if period == "12m":
        if start.day != 1 or end != month_start(start.year, start.month, 12):
            raise ValueError("Intervalo mensal inválido.")
        return [month_start(start.year, start.month, i).strftime("%Y-%m") for i in range(12)]
    days = 7 if period == "7d" else 30
    if end != start + timedelta(days=days):
        raise ValueError("Intervalo diário inválido.")
    return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]


def timestamp_milliseconds(value: str) -> int:
    """Transporte explícito para inputs timestamp do Xano; exige timezone."""
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.tzinfo is None:
        raise ValueError("Timestamp sem timezone.")
    return int(instant.timestamp() * 1000)
