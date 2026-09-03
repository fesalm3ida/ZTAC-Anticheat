"""Fábrica de scanner — escolhe o backend correto para o host.

Em Windows (`os.name == 'nt'`) usa o scanner real (`WindowsScanner`, ctypes).
Em qualquer outro SO (ex.: WSL, para desenvolvimento/UI) usa o
`SimulatedScanner`, permitindo testar o pipeline completo sem um processo do
jogo. Para forçar o modo demo no Windows, defina `AC_FORCE_DEMO=1`.
"""
from __future__ import annotations

import os

from .base import ScannerBase, ScanReport, Finding, new_report  # noqa: F401


def create_scanner(force_demo: bool | None = None) -> ScannerBase:
    """Devolve a instância do scanner adequada ao ambiente."""
    force = (os.environ.get("AC_FORCE_DEMO", "") == "1") if force_demo is None else force_demo

    from .windows_scanner import WindowsScanner
    from .simulated_scanner import SimulatedScanner

    win = WindowsScanner()
    if win.is_available() and not force:
        return win
    return SimulatedScanner(anomalous=True)
