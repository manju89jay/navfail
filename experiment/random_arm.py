"""Random arm (EXPERIMENT.md section 6): uniform draws from the allowlist, seeded."""
import random

from experiment.allowlist import SETTINGS


class RandomProposer:
    """Each proposal draws 1 to 3 distinct settings, values uniform in range."""

    def __init__(self, seed):
        self.seed = seed
        self._rng = random.Random(seed)

    def propose(self, history):
        n = self._rng.randint(1, 3)
        settings = self._rng.sample(sorted(SETTINGS), n)
        changes = {}
        for setting in settings:
            spec = SETTINGS[setting]
            changes[setting] = round(self._rng.uniform(spec["min"], spec["max"]), 4)
        return {"changes": changes, "reason": f"random draw (seed {self.seed})"}
