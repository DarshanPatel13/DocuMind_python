"""Paid end-to-end eval run as a pytest (opt-in: RUN_EVALS=1 + stack running)."""
from __future__ import annotations

import os

import pytest


@pytest.mark.evals
@pytest.mark.skipif(os.getenv("RUN_EVALS") != "1", reason="set RUN_EVALS=1 to run paid evals")
def test_eval_suite_meets_thresholds() -> None:
    from evals.run import main

    assert main([]) == 0
