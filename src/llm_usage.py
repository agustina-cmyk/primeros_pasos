"""Agregación de uso de LLM a partir de los logs en `reports/`.

Cada llamada de los analizadores (recurrencia y roadmap) deja un archivo
`reports/{recurrence|roadmap}_input_YYYYMMDD_HHMMSS.json` con `stats`. Este
módulo lee esos logs y suma tokens/chars para una ventana de fechas.
"""

import json
import os
import re
from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, List


_FILENAME_RE = re.compile(r"^(recurrence|roadmap)_input_(\d{8})_\d{6}\.json$")


@dataclass(frozen=True)
class AnalyzerUsage:
    calls: int
    tokens: int
    chars: int


@dataclass(frozen=True)
class WeeklyLlmUsage:
    recurrence: AnalyzerUsage
    roadmap: AnalyzerUsage

    @property
    def total_tokens(self) -> int:
        return self.recurrence.tokens + self.roadmap.tokens

    @property
    def total_calls(self) -> int:
        return self.recurrence.calls + self.roadmap.calls


def aggregate_weekly_llm_usage(
    week_start: date,
    week_end: date,
    reports_dir: str = "reports",
) -> WeeklyLlmUsage:
    """Suma tokens/chars de los logs LLM con fecha en `[week_start, week_end]`.

    El timestamp del filename es UTC (`YYYYMMDD_HHMMSS`). Comparamos por fecha
    UTC contra el rango local — la diferencia de TZ vs Argentina (UTC-3) es
    despreciable a nivel de resumen semanal.
    """
    by_kind: Dict[str, List[dict]] = {"recurrence": [], "roadmap": []}

    if not os.path.isdir(reports_dir):
        return _empty_usage()

    week_start_str = week_start.strftime("%Y%m%d")
    week_end_str = week_end.strftime("%Y%m%d")

    for filename in os.listdir(reports_dir):
        match = _FILENAME_RE.match(filename)
        if not match:
            continue
        kind, date_str = match.group(1), match.group(2)
        if not (week_start_str <= date_str <= week_end_str):
            continue
        path = os.path.join(reports_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        stats = data.get("stats") or {}
        if not isinstance(stats, dict):
            continue
        by_kind[kind].append(stats)

    return WeeklyLlmUsage(
        recurrence=_sum(by_kind["recurrence"]),
        roadmap=_sum(by_kind["roadmap"]),
    )


def format_weekly_usage_block(usage: WeeklyLlmUsage) -> str:
    """Devuelve el bloque markdown listo para appendear al weekly del CPO."""
    lines = ["", "", "---", "🤖 **LLM usage (semana)**"]
    if usage.total_calls == 0:
        lines.append("- Sin llamadas al LLM esta semana.")
        return "\n".join(lines)

    if usage.recurrence.calls:
        lines.append(
            f"- Recurrencia: {usage.recurrence.calls} calls · "
            f"~{usage.recurrence.tokens:,} tokens ({usage.recurrence.chars:,} chars)"
        )
    if usage.roadmap.calls:
        lines.append(
            f"- Roadmap: {usage.roadmap.calls} calls · "
            f"~{usage.roadmap.tokens:,} tokens ({usage.roadmap.chars:,} chars)"
        )
    lines.append(f"- **Total: ~{usage.total_tokens:,} tokens** ({usage.total_calls} calls)")
    return "\n".join(lines)


def _sum(stats_list: Iterable[dict]) -> AnalyzerUsage:
    tokens = 0
    chars = 0
    calls = 0
    for s in stats_list:
        tokens += int(s.get("estimated_tokens") or 0)
        chars += int(s.get("total_chars") or 0)
        calls += 1
    return AnalyzerUsage(calls=calls, tokens=tokens, chars=chars)


def _empty_usage() -> WeeklyLlmUsage:
    empty = AnalyzerUsage(calls=0, tokens=0, chars=0)
    return WeeklyLlmUsage(recurrence=empty, roadmap=empty)
