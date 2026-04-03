"""Pytest configuration for ASIS backend tests."""

import os

import pytest

# Override settings for tests — use dummy values for required secrets
os.environ.setdefault("JWT_SECRET", "test-secret-key-at-least-32-characters!!")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test as asyncio")
