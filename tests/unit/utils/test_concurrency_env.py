"""Tests for P2c: ORKA_MAX_CONCURRENT_REQUESTS / ORKA_TIMEOUT_SECONDS wiring."""

from __future__ import annotations

import pytest

from orka.utils.concurrency import (
    ConcurrencyManager,
    default_max_concurrency,
    default_timeout_seconds,
)


def test_max_concurrency_default(monkeypatch):
    monkeypatch.delenv("ORKA_MAX_CONCURRENT_REQUESTS", raising=False)
    assert default_max_concurrency() == 10


def test_max_concurrency_from_env(monkeypatch):
    monkeypatch.setenv("ORKA_MAX_CONCURRENT_REQUESTS", "37")
    assert default_max_concurrency() == 37


def test_max_concurrency_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("ORKA_MAX_CONCURRENT_REQUESTS", "not-a-number")
    assert default_max_concurrency() == 10
    monkeypatch.setenv("ORKA_MAX_CONCURRENT_REQUESTS", "0")
    assert default_max_concurrency() == 10


def test_timeout_default(monkeypatch):
    monkeypatch.delenv("ORKA_TIMEOUT_SECONDS", raising=False)
    assert default_timeout_seconds() == 300.0


def test_timeout_from_env(monkeypatch):
    monkeypatch.setenv("ORKA_TIMEOUT_SECONDS", "12.5")
    assert default_timeout_seconds() == 12.5


def test_timeout_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("ORKA_TIMEOUT_SECONDS", "abc")
    assert default_timeout_seconds() == 300.0


def test_manager_uses_env(monkeypatch):
    monkeypatch.setenv("ORKA_MAX_CONCURRENT_REQUESTS", "3")
    mgr = ConcurrencyManager()  # None -> resolve from env
    assert mgr.max_concurrency == 3
    assert mgr.semaphore._value == 3


def test_manager_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("ORKA_MAX_CONCURRENT_REQUESTS", "3")
    mgr = ConcurrencyManager(max_concurrency=8)
    assert mgr.max_concurrency == 8
