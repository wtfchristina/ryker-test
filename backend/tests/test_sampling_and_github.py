from datetime import datetime, timezone
import uuid
import pytest
from app.services.github_collector import GitHubAuditCollector
from app.services.sampler import AICPASamplingEngine

def test_aicpa_sampling_sizing_and_reproducibility():
    # 1. Generate synthetic population of 120 merged PRs
    synthetic_prs = [
        {"pr_number": i, "title": f"feat: change #{i}", "author": f"dev_{i % 5}"}
        for i in range(1, 121)
    ]

    # AICPA rule: 120 population falls into medium/large tier (target 20)
    expected_size = AICPASamplingEngine.calculate_sample_size(len(synthetic_prs))
    assert expected_size == 20

    # 2. Select sample with deterministic seed
    seed = "alpha-engagement-2026-CC8.1"
    run_1 = AICPASamplingEngine.select_reproducible_sample(synthetic_prs, sample_seed=seed)
    
    # 3. Repeat with same seed: MUST yield exact same items for audit reproducibility
    run_2 = AICPASamplingEngine.select_reproducible_sample(synthetic_prs, sample_seed=seed)
    
    assert run_1["sample_size"] == 20
    assert run_1["selected_sample"] == run_2["selected_sample"]
    print(f"\n[SAMPLE SELECTED] {run_1['sample_size']} items chosen deterministically.")

def test_github_observation_window_filtering():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 6, 30, tzinfo=timezone.utc)

    mock_raw_prs = [
        {"number": 101, "title": "In Window", "merged_at": "2026-03-15T12:00:00Z", "user": {"login": "alice"}},
        {"number": 102, "title": "Before Window", "merged_at": "2025-12-15T12:00:00Z", "user": {"login": "bob"}},
        {"number": 103, "title": "After Window", "merged_at": "2026-07-05T12:00:00Z", "user": {"login": "charlie"}},
        {"number": 104, "title": "Unmerged PR", "merged_at": None, "user": {"login": "dan"}},
    ]

    filtered = GitHubAuditCollector.filter_merged_prs_in_window(mock_raw_prs, start, end)

    assert len(filtered) == 1
    assert filtered[0]["pr_number"] == 101
    print("\n[WINDOW FILTER] Non-observation items successfully excluded.")
