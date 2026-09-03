"""Base do scanner — modelos de dados e interface comum.

Todos os backends de varredura (Windows real, simulado) implementam a classe
`ScannerBase` e devolvem um `ScanReport`, que a API serializa para o frontend.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Finding:
    """Um único achado de um estágio de detecção."""

    stage: str            # 'A' | 'B' | 'C'
    severity: str         # 'ok' | 'low' | 'medium' | 'high' | 'critical'
    title: str            # título curto
    detail: str           # explicação
    evidence: list = field(default_factory=list)  # evidências p/ exibição

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScanReport:
    """Resultado consolidado de uma varredura.

    `simulated` indica que o scan não leu um processo real (modo demo, quando
    o app não está rodando no Windows).

    `warning` carrega um aviso não-fatal (ex.: processo do jogo não encontrado).
    Quando isso ocorre, `verdict` vale `"sem_processo"` e a varredura não
    prossegue — o frontend exibe o aviso em destaque.
    """

    timestamp: str
    simulated: bool = False
    process: dict = field(default_factory=dict)     # nome, pid, título, caminho
    verdict: str = "limpo"                          # limpo | suspeito | hackeado | sem_processo
    score: int = 0                                  # 0..100
    modules_checked: int = 0
    warning: str | None = None                      # aviso não-fatal
    findings: list = field(default_factory=list)    # list[Finding.to_dict()]
    raw: dict = field(default_factory=dict)         # dados estendidos

    def add_finding(self, finding: Finding) -> None:
        self.findings.append(finding.to_dict())

    def compute_verdict(self) -> None:
        """Recalcula veredito e score a partir das evidências."""
        from .signatures import MAX_SCORE, SEVERITY_WEIGHT

        score = 0
        for f in self.findings:
            score += SEVERITY_WEIGHT.get(f["severity"], 0)

        # HACKEADO exige cheat ATIVO no processo:
        #   - Estágio A critical: módulo de cheat conhecido carregado (ex.: wallhack.dll)
        #   - Estágio B critical: detour inline confirmado (mem[0]==E9 e disco não é E9)
        # Apenas artefatos / indícios (logs no disco, strings, divergências, supostos
        # patches) => SUSPEITO, não HACKEADO.
        active = any(f["stage"] == "A" and f["severity"] == "critical"
                     for f in self.findings)
        active = active or any(f["stage"] == "B" and f["severity"] == "critical"
                               for f in self.findings)

        if active:
            verdict = "hackeado"
        elif score > 0:
            verdict = "suspeito"
        else:
            verdict = "limpo"

        self.score = min(score, MAX_SCORE)
        self.verdict = verdict

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_report(process: dict, simulated: bool = False) -> ScanReport:
    """Cria um relatório com timestamp, pronto para receber findings."""
    return ScanReport(
        timestamp=datetime.now().isoformat(timespec="seconds"),
        simulated=simulated,
        process=process,
    )


class ScannerBase(ABC):
    """Interface comum de todos os backends de varredura."""

    @abstractmethod
    def list_processes(self) -> list[dict]:
        """Lista os processos do jogo candidatos (nome, pid, título)."""

    @abstractmethod
    def scan(self, pid: int | None = None) -> ScanReport:
        """Executa a varredura e devolve um ScanReport."""

    @abstractmethod
    def is_available(self) -> bool:
        """True se o backend consegue rodar neste host (SO/permissões)."""
