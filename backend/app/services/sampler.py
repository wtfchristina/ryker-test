import hashlib
import random
from typing import Any, Dict, List

class AICPASamplingEngine:
    @staticmethod
    def calculate_sample_size(population_count: int) -> int:
        """
        Standard AICPA non-statistical / attribute sample sizing rules
        for automated and manual operating controls:
        - Small (< 10): Test 1-2
        - Medium (10 - 50): Test 5
        - Large (51 - 250): Test 15-25
        - Continuous / High Volume (> 250): Test 25-40
        """
        if population_count <= 0:
            return 0
        elif population_count < 10:
            return min(population_count, 2)
        elif population_count <= 50:
            return 5
        elif population_count <= 250:
            return 20
        else:
            return 30

    @classmethod
    def select_reproducible_sample(
        cls,
        population: List[Dict[str, Any]],
        sample_seed: str,
        target_sample_size: int | None = None,
    ) -> Dict[str, Any]:
        """
        Selects a random sample using a deterministic SHA-256 derived seed.
        The seed must be preserved in the audit workpapers so any peer reviewer
        or regulatory body can reproduce the exact selection.
        """
        total = len(population)
        if total == 0:
            return {"sample_size": 0, "population_size": 0, "sample_items": []}

        sample_size = target_sample_size or cls.calculate_sample_size(total)
        sample_size = min(sample_size, total)

        # Seed the PRNG deterministically using the hash of engagement + control + date
        int_seed = int(hashlib.sha256(sample_seed.encode("utf-8")).hexdigest(), 16)
        rng = random.Random(int_seed)

        selected_indices = sorted(rng.sample(range(total), sample_size))
        selected_items = [population[i] for i in selected_indices]

        return {
            "population_size": total,
            "sample_size": sample_size,
            "sampling_seed_record": sample_seed,
            "selected_sample": selected_items,
        }
