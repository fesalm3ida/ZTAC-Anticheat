"""Backend SIMULADO — usado quando o app não roda no Windows.

O scan de memória real exige Windows (kernel32/ntdll). Em ambiente de
desenvolvimento (WSL/Linux) este backend gera dados realistas — sempre com o
mesmo formato de `ScanReport` — para que login, dashboard, API e visualização
de resultados sejam testáveis de ponta a ponta sem um processo do jogo.

Seleção automática em `scanner/__init__.py`: em `nt` usa o scanner real;
em qualquer outro SO usa este simulado.
"""
from __future__ import annotations

import os
import random

from .base import Finding, new_report, ScannerBase
from ..config import TARGET_PROCESS_NAMES

# Processo "simulado" que chamamos de hl.exe — alvo típico do lab CS 1.6.
_FAKE_PROCESS = {
    "name": "hl.exe",
    "pid": 4242,
    "title": "Counter-Strike",
    "path": r"C:\Program Files (x86)\Steam\steamapps\common\Half-Life\hl.exe",
}


class SimulatedScanner(ScannerBase):
    """Gera dataset sintético para desenvolvimento/UI.

    `anomalous` (padrão True) simula um processo com o cheat v8 injetado; com
    `anomalous=False` simula um processo limpo para validar o veredito LIMPO.
    """

    def __init__(self, anomalous: bool = True, seed: int | None = None,
                 no_process: bool = False) -> None:
        self.anomalous = anomalous
        self.no_process = no_process
        self._rng = random.Random(seed)
        self.mode = "demo"

    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        return os.name != "nt"

    def list_processes(self) -> list[dict]:
        if self.no_process:
            return []
        proc = dict(_FAKE_PROCESS)
        # PID um pouco "vivo" para parecer a cada chamada
        proc["pid"] = _FAKE_PROCESS["pid"] + self._rng.randint(-3, 3)
        proc["simulated"] = True
        return [proc]

    # ------------------------------------------------------------------
    def scan(self, pid: int | None = None) -> "object":
        if self.no_process:
            report = new_report({}, simulated=True)
            report.verdict = "sem_processo"
            report.warning = (
                "Não foi encontrado processo do Counter-Strike conhecido "
                f"({', '.join(TARGET_PROCESS_NAMES)}). "
                "Inicie o jogo e tente novamente."
            )
            return report

        proc = dict(_FAKE_PROCESS)
        if pid:
            proc["pid"] = pid
        proc["simulated"] = True

        report = new_report(proc, simulated=True)
        report.modules_checked = self._rng.randint(38, 52)

        if self.anomalous:
            self._add_anomalies(report)
        else:
            self._add_clean_findings(report)

        report.compute_verdict()
        return report

    # ------------------------------------------------------------------
    # Ajudantes de dados sintéticos
    # ------------------------------------------------------------------
    def _add_anomalies(self, report) -> None:
        # --- Estágio A: módulos injetados ---------------------------------
        report.add_finding(Finding(
            stage="A",
            severity="critical",
            title="Módulo de wallhack injetado",
            detail="wallhack.dll carregado fora do diretório do jogo/sistema.",
            evidence=["wallhack.dll", r"C:\Temp\wallhack.dll"],
        ))
        report.add_finding(Finding(
            stage="A",
            severity="high",
            title="Módulo de injeção hook_v8.dll",
            detail="DLL do vetor SetWindowsHookEx localizada no processo.",
            evidence=["hook_v8.dll", r"C:\Users\Public\hook_v8.dll"],
        ))
        report.add_finding(Finding(
            stage="A",
            severity="medium",
            title="DLL fora de raiz confiável",
            detail="Módulo carregado de diretório temporário, padrão de payload.",
            evidence=["x7f3a9b.dll", r"C:\Users\Public\AppData\Local\Temp"],
        ))

        # --- Estágio B: detours no opengl32.dll ----------------------------
        report.add_finding(Finding(
            stage="B",
            severity="critical",
            title="Detour inline em wglSwapBuffers",
            detail="Primeiro byte 0xE9 (jmp rel32) — hook clássico do v8.",
            evidence=["wglSwapBuffers", "mem= E9 __ __ __ | disk= 8B __ __ __"],
        ))
        report.add_finding(Finding(
            stage="B",
            severity="high",
            title="Patch em glEnable",
            detail="Bytes divergem entre a imagem em disco e a memória.",
            evidence=["glEnable", "bytes_diff=1 (12/16 bytes iguais)"],
        ))
        report.add_finding(Finding(
            stage="B",
            severity="medium",
            title="Divergência em glDepthFunc",
            detail="Divergência isolada; verificar. Sinal de hook suave/hotpatch.",
            evidence=["glDepthFunc", "mem[0]=55 disk[0]=55 (diverge no byte 6)"],
        ))

        # --- Estágio C: artefatos e strings ---------------------------------
        report.add_finding(Finding(
            stage="C",
            severity="high",
            title="Arquivo de log do aimbot presente",
            detail=r"C:\Temp\Aimbot_Debug.txt existe em disco.",
            evidence=[r"C:\Temp\Aimbot_Debug.txt"],
        ))
        report.add_finding(Finding(
            stage="C",
            severity="medium",
            title="String característica 'AIMBOT PRONTO'",
            detail="Assinatura do cheater encontrada na memória do processo.",
            evidence=["'AIMBOT PRONTO' @ 0x17F3A20"],
        ))
        report.add_finding(Finding(
            stage="C",
            severity="medium",
            title="String 'hk_wglSwapBuffers'",
            detail="Nome do hook do wallhack v8 presente em memória.",
            evidence=["'hk_wglSwapBuffers' @ 0x1A0C410"],
        ))
        report.add_finding(Finding(
            stage="C",
            severity="low",
            title="String 'ForceWallhack'",
            detail="Flag de configuração do wallhack no espaço do processo.",
            evidence=["'ForceWallhack' @ 0x24BE9E0"],
        ))

    def _add_clean_findings(self, report) -> None:
        report.add_finding(Finding(
            stage="A",
            severity="ok",
            title="Nenhum módulo suspeito",
            detail="Todos os módulos carregados estão em raízes confiáveis.",
            evidence=["0 módulos na lista negra / fora de raiz confiável"],
        ))
        report.add_finding(Finding(
            stage="B",
            severity="ok",
            title="opengl32.dll íntegro",
            detail="Nenhum export com detour (mem[0]=E9) ou divergência disco×memória.",
            evidence=["38 exports verificados"],
        ))
        report.add_finding(Finding(
            stage="C",
            severity="ok",
            title="Nenhum artefato/string de cheat",
            detail="Nenhum log em C:\\Temp nem assinatura conhecida em memória.",
            evidence=["0 achados"],
        ))
