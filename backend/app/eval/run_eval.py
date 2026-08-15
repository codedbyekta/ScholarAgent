"""
Reproducible evaluation command, runnable from the terminal without the
frontend or even the FastAPI server running:

    cd backend
    python -m app.eval.run_eval

Prints the aggregate metrics to stdout and saves the full run to SQLite
(and to a timestamped JSON file), exactly like the "Run Evaluation"
button in the frontend does via POST /api/eval/run - both paths call the
exact same run_full_evaluation() function, so results are reproducible
either way.
"""

import json
import logging
import os
import sys

from app.core.logging_config import setup_logging
from app.db.sqlite_db import init_db
from app.eval.eval_engine import run_full_evaluation

setup_logging()
logger = logging.getLogger(__name__)


def main():
    init_db()
    result = run_full_evaluation()

    if result["not_evaluated_reason"]:
        print(f"\nNOT EVALUATED: {result['not_evaluated_reason']}\n")
        sys.exit(1)

    os.makedirs("./app/data/eval_reports", exist_ok=True)
    report_path = f"./app/data/eval_reports/{result['run_id']}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("\n" + "=" * 60)
    print(f"Evaluation run: {result['run_id']}")
    print("=" * 60)
    for k, v in result["aggregate"].items():
        print(f"{k:35s}: {v}")
    print("=" * 60)
    print(f"Full report saved to: {report_path}")


if __name__ == "__main__":
    main()
