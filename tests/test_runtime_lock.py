"""Prevent two EdgeSight processes from racing on one model/store session."""
from __future__ import annotations

import importlib
import inspect
import tempfile
import unittest
from pathlib import Path


class RuntimeLockTests(unittest.TestCase):
    def test_only_one_process_can_own_a_store_database_lock(self):
        main_module = importlib.import_module("src.main")
        acquire = getattr(main_module, "acquire_runtime_lock", None)
        self.assertTrue(callable(acquire), "EdgeSight must refuse duplicate writers for the same storage DB")

        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "edgesight.db")
            first = acquire(db_path)
            try:
                with self.assertRaises(RuntimeError):
                    acquire(db_path)
            finally:
                first.close()

            second = acquire(db_path)
            second.close()

    def test_live_process_lock_can_be_probed_without_blocking(self):
        main_module = importlib.import_module("src.main")
        probe = getattr(main_module, "runtime_lock_is_held", None)
        acquire = getattr(main_module, "acquire_runtime_lock", None)
        self.assertTrue(callable(probe), "secondary model audits must detect a live edge owner")
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "edgesight.db")
            self.assertFalse(probe(db_path))
            lock = acquire(db_path)
            try:
                self.assertTrue(probe(db_path))
            finally:
                lock.close()

    def test_same_store_is_exclusive_even_when_profiles_use_different_databases(self):
        main_module = importlib.import_module("src.main")
        acquire = main_module.acquire_runtime_lock
        self.assertIn(
            "store_id",
            inspect.signature(acquire).parameters,
            "native/Docker profiles for one store must share the same process lock",
        )
        with tempfile.TemporaryDirectory() as directory:
            first = acquire(str(Path(directory) / "docker.db"), store_id="store_mumbai_001")
            try:
                with self.assertRaises(RuntimeError):
                    acquire(str(Path(directory) / "native.db"), store_id="store_mumbai_001")
                other_store = acquire(str(Path(directory) / "other.db"), store_id="store_checkout_002")
                other_store.close()
            finally:
                first.close()


if __name__ == "__main__":
    unittest.main()
