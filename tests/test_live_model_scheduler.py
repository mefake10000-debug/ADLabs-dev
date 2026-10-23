"""Concurrency guarantees for independent live model passes."""
from __future__ import annotations

import threading
import unittest

from src.main import EdgePipeline


class LiveModelSchedulerTests(unittest.TestCase):
    def test_independent_model_inferences_run_concurrently(self):
        runner = getattr(EdgePipeline, "_run_independent_model_jobs", None)
        self.assertTrue(callable(runner), "live edge must schedule independent slow models concurrently")
        barrier = threading.Barrier(2)
        thread_ids = {}

        def job(name):
            thread_ids[name] = threading.get_ident()
            barrier.wait(timeout=2)
            return f"{name}-done"

        result = runner({"pose": lambda: job("pose"), "products": lambda: job("products")}, max_workers=2)
        self.assertEqual(result, {"pose": "pose-done", "products": "products-done"})
        self.assertNotEqual(thread_ids["pose"], thread_ids["products"])

    def test_one_model_failure_does_not_discard_successful_model_results(self):
        runner = getattr(EdgePipeline, "_run_independent_model_jobs", None)
        self.assertTrue(callable(runner), "live edge must isolate independent model failures")

        def unavailable_model():
            raise RuntimeError("weights unavailable")

        result = runner({"pose": lambda: 17, "products": unavailable_model}, max_workers=2)
        self.assertEqual(result, {"pose": 17})


if __name__ == "__main__":
    unittest.main()
