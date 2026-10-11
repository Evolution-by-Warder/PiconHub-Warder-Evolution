"""Regression checks for no-rescan startup and bounded PNG delivery."""
import ast
import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile
import json
import os

APP = Path(__file__).resolve().parent

class DeliveryResumeTests(unittest.TestCase):
    def test_startup_runs_read_only_preflight_and_does_not_schedule_scan(self):
        tree = ast.parse((APP / 'engine.py').read_text(encoding='utf-8'))
        app = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'App')
        init = next(node for node in app.body if isinstance(node, ast.FunctionDef) and node.name == '__init__')
        self.assertTrue(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                            and node.func.attr == 'run_preflight' for node in ast.walk(init)))
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                             and node.func.attr == 'start' for node in ast.walk(init)))
        run_preflight = next(node for node in app.body if isinstance(node, ast.FunctionDef) and node.name == 'run_preflight')
        self.assertTrue(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                            and node.func.id == 'read_only_preflight' for node in ast.walk(run_preflight)))

    def test_launcher_never_calls_self_update(self):
        tree = ast.parse((APP / 'factory_launcher.py').read_text(encoding='utf-8'))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
        self.assertNotIn('attempt_update', [node.func.id for node in calls])

    def test_evidence_attempt_limit(self):
        import factory_png_evidence
        self.assertIn('max_attempts', factory_png_evidence.upload_png_evidence.__code__.co_varnames)

if __name__ == '__main__':
    unittest.main()
