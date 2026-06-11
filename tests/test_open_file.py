"""Tests for the /open-file endpoint."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from research_engine.api import app

client = TestClient(app)


def test_open_file_success(monkeypatch):
    """Test opening a valid file in the project root succeeds."""
    # Mock shutil.which to avoid launching real editors
    monkeypatch.setattr(shutil, "which", lambda x: None)

    if sys.platform == "win32":
        monkeypatch.setattr(os, "startfile", lambda x: None)

    # README.md is a valid file in the project root
    response = client.post("/open-file", json={"path": "README.md"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_open_file_not_found():
    """Test opening a non-existent file returns 404."""
    response = client.post("/open-file", json={"path": "non_existent_file.py"})
    assert response.status_code == 404


def test_open_file_path_traversal():
    """Test that path traversal outside project root is blocked with 400."""
    response = client.post("/open-file", json={"path": "../../README.md"})
    assert response.status_code == 400
    assert "Access denied" in response.json()["detail"]


def test_open_file_disallowed_extension(monkeypatch):
    """Test that opening files with disallowed extensions is blocked with 403."""
    # Mock Path.exists and Path.relative_to so it bypasses traversal and exists checks
    monkeypatch.setattr(Path, "exists", lambda self: True)
    monkeypatch.setattr(Path, "relative_to", lambda self, *args, **kwargs: self)

    response = client.post("/open-file", json={"path": "test.exe"})
    assert response.status_code == 403
    assert "opening files of this type is not allowed" in response.json()["detail"]
