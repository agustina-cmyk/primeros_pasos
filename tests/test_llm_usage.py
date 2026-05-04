import json
from datetime import date

from llm_usage import aggregate_weekly_llm_usage, format_weekly_usage_block


def _write_log(dirpath, kind: str, timestamp: str, tokens: int, chars: int) -> None:
    path = dirpath / f"{kind}_input_{timestamp}.json"
    path.write_text(json.dumps({
        "timestamp": timestamp,
        "stats": {"estimated_tokens": tokens, "total_chars": chars},
        "system_prompt": "x",
        "user_message": "y",
    }))


def test_aggregates_within_window(tmp_path):
    _write_log(tmp_path, "recurrence", "20260428_120000", tokens=1000, chars=4000)
    _write_log(tmp_path, "roadmap", "20260429_080000", tokens=2000, chars=8000)
    _write_log(tmp_path, "roadmap", "20260501_185500", tokens=500, chars=2000)

    usage = aggregate_weekly_llm_usage(
        week_start=date(2026, 4, 27),
        week_end=date(2026, 5, 1),
        reports_dir=str(tmp_path),
    )

    assert usage.recurrence.calls == 1
    assert usage.recurrence.tokens == 1000
    assert usage.roadmap.calls == 2
    assert usage.roadmap.tokens == 2500
    assert usage.total_tokens == 3500
    assert usage.total_calls == 3


def test_excludes_files_outside_window(tmp_path):
    _write_log(tmp_path, "recurrence", "20260420_120000", tokens=999, chars=3996)
    _write_log(tmp_path, "roadmap", "20260502_120000", tokens=999, chars=3996)
    _write_log(tmp_path, "roadmap", "20260428_120000", tokens=100, chars=400)

    usage = aggregate_weekly_llm_usage(
        week_start=date(2026, 4, 27),
        week_end=date(2026, 5, 1),
        reports_dir=str(tmp_path),
    )

    assert usage.total_calls == 1
    assert usage.roadmap.tokens == 100


def test_returns_zeros_when_dir_missing(tmp_path):
    missing = tmp_path / "does-not-exist"
    usage = aggregate_weekly_llm_usage(
        week_start=date(2026, 4, 27),
        week_end=date(2026, 5, 1),
        reports_dir=str(missing),
    )
    assert usage.total_tokens == 0
    assert usage.total_calls == 0


def test_ignores_unrelated_files_and_corrupt_json(tmp_path):
    _write_log(tmp_path, "recurrence", "20260428_120000", tokens=100, chars=400)
    (tmp_path / "report_20260428_120000.html").write_text("<html></html>")
    (tmp_path / "roadmap_input_20260428_130000.json").write_text("not json")
    (tmp_path / "random.txt").write_text("x")

    usage = aggregate_weekly_llm_usage(
        week_start=date(2026, 4, 27),
        week_end=date(2026, 5, 1),
        reports_dir=str(tmp_path),
    )
    assert usage.total_calls == 1
    assert usage.recurrence.tokens == 100


def test_format_block_no_calls():
    from llm_usage import WeeklyLlmUsage, AnalyzerUsage
    usage = WeeklyLlmUsage(
        recurrence=AnalyzerUsage(calls=0, tokens=0, chars=0),
        roadmap=AnalyzerUsage(calls=0, tokens=0, chars=0),
    )
    block = format_weekly_usage_block(usage)
    assert "Sin llamadas al LLM esta semana" in block
    assert "🤖" in block


def test_format_block_with_calls():
    from llm_usage import WeeklyLlmUsage, AnalyzerUsage
    usage = WeeklyLlmUsage(
        recurrence=AnalyzerUsage(calls=2, tokens=1500, chars=6000),
        roadmap=AnalyzerUsage(calls=3, tokens=12000, chars=48000),
    )
    block = format_weekly_usage_block(usage)
    assert "Recurrencia: 2 calls" in block
    assert "Roadmap: 3 calls" in block
    assert "13,500" in block
    assert "5 calls" in block
