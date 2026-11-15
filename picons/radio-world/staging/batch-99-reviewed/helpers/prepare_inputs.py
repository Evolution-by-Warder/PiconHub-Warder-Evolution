"""Apply the reviewed batch 99 artwork using the established picon renderer."""
import runpy
import sys
from pathlib import Path

batch = Path(__file__).resolve().parents[1]
previous = batch.parent / "batch-98-reviewed" / "helpers" / "prepare_inputs.py"
runner = runpy.run_path(str(previous))["main"]
context = runner.__globals__


def check_identity(row):
    evidence = context["read"](batch / "official-source-evidence.json")
    candidate, = [item for item in evidence["candidates"] if item["station"] == row["station"]]
    publisher = row["publisher"]
    assert publisher["source"] == candidate["publisher_source"]
    assert publisher["name"] == candidate["publisher_name"]
    assert publisher["streams"] == [candidate["station"]["url"]]
    assert row["original"] == candidate["original"]
    assert row["image"] == publisher["logo"] == candidate["original"]["url"]


context["check_identity"] = check_identity
runner(int(sys.argv[1]))
