from pathlib import Path


def test_answer_file():
    assert (Path("repo") / "answer.txt").read_text(encoding="utf-8").strip() == "ok"
