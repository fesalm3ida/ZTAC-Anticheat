"""Scanner REAL — Windows (varre memória de processo do jogo).

Implementa os três estágios do anti-cheat v8 usando chamadas diretas à
`kernel32` (ctypes), sem injetar nada:

  Estágio A — enumera módulos (CreateToolhelp32Snapshot) e classifica os que
              estão fora do diretório do jogo/sistema, com lista negra explícita.
  Estágio B — parseia o opengl32.dll do disco (PE) e compara os primeiros bytes
              de cada export com os bytes NA MEMÓRIA do processo. `mem[0]=0xE9`
              = detour inline (assinatura do v8); bytes divergentes = suspeita.
  Estágio C — checa logs em C:\\Temp e varre a memória legível por strings.

Somente roda em Windows (`os.name == 'nt'`).
"""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

from .base import Finding, new_report, ScannerBase
from .pe_parser import PeImage
from .signatures import (
    EXPORT_BYTES_TO_COMPARE,
    INLINE_HOOK_BYTE,
    KNOWN_CHEAT_MODULES,
    KNOWN_LOG_FILES,
    KNOWN_MEMORY_SIGNATURES,
    OPENGL_HOOK_TARGETS,
    TRUSTED_PATH_MARKERS,
)

from ..config import TARGET_PROCESS_NAMES

# ---------------------------------------------------------------------------
# Constantes do Windows
# ---------------------------------------------------------------------------
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

TH32CS_SNAPPROCESS = 0x02
TH32CS_SNAPMODULE = 0x08
TH32CS_SNAPMODULE32 = 0x10

MEM_COMMIT = 0x1000
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80

MAX_PATH = 260

if os.name == "nt":
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
else:  # permitir importar o módulo em SO não-Windows (para lint/testes)
    kernel32 = None


# ---------------------------------------------------------------------------
# Estruturas para ctypes
# ---------------------------------------------------------------------------
class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ubyte)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * MAX_PATH),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", ctypes.c_wchar * 256),
        ("szExePath", ctypes.c_wchar * MAX_PATH),
    ]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("Allignment", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("Allignment2", wintypes.DWORD),
    ]


class SYSTEM_INFO(ctypes.Structure):
    _fields_ = [
        ("wProcessorArchitecture", wintypes.WORD),
        ("wReserved", wintypes.WORD),
        ("dwPageSize", wintypes.DWORD),
        ("lpMinimumApplicationAddress", ctypes.c_void_p),
        ("lpMaximumApplicationAddress", ctypes.c_void_p),
        ("dwActiveProcessorMask", ctypes.c_void_p),
        ("dwNumberOfProcessors", wintypes.DWORD),
        ("dwProcessorType", wintypes.DWORD),
        ("dwAllocationGranularity", wintypes.DWORD),
        ("wProcessorLevel", wintypes.WORD),
        ("wProcessorRevision", wintypes.WORD),
    ]


if kernel32:
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.restype = wintypes.BOOL


# ---------------------------------------------------------------------------
# Utilidades de baixo nível
# ---------------------------------------------------------------------------
def _open_process(pid: int) -> int:
    return kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                                False, pid)


def _enum_processes() -> list[dict]:
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == INVALID_HANDLE:
        return []
    entries = []
    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    try:
        if kernel32.Process32FirstW(snap, ctypes.byref(pe)):
            while True:
                entries.append({
                    "pid": pe.th32ProcessID,
                    "name": pe.szExeFile,
                })
                if not kernel32.Process32NextW(snap, ctypes.byref(pe)):
                    break
    finally:
        kernel32.CloseHandle(snap)
    return entries


def _enum_modules(pid: int) -> list[dict]:
    snap = kernel32.CreateToolhelp32Snapshot(
        TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap == INVALID_HANDLE:
        snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE32, pid)
    if snap == INVALID_HANDLE:
        return []
    mods = []
    me = MODULEENTRY32W()
    me.dwSize = ctypes.sizeof(MODULEENTRY32W)
    try:
        if kernel32.Module32FirstW(snap, ctypes.byref(me)):
            while True:
                mods.append({
                    "name": me.szModule,
                    "path": me.szExePath,
                    "base": me.modBaseAddr,
                    "size": me.modBaseSize,
                })
                if not kernel32.Module32NextW(snap, ctypes.byref(me)):
                    break
    finally:
        kernel32.CloseHandle(snap)
    return mods


INVALID_HANDLE = ctypes.c_void_p(-1).value


def _read_mem(hproc: int, addr: int, size: int) -> bytes | None:
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t(0)
    ok = kernel32.ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, size,
                                    ctypes.byref(read))
    if not ok or read.value == 0:
        return None
    return buf.raw[:read.value]


def _virtual_query(hproc: int, addr: int, mbi: MEMORY_BASIC_INFORMATION) -> int:
    return kernel32.VirtualQueryEx(hproc, ctypes.c_void_p(addr),
                                   ctypes.byref(mbi), ctypes.sizeof(mbi))


# ---------------------------------------------------------------------------
# Estágio A — classificação de módulos
# ---------------------------------------------------------------------------
def _classify_module(mod: dict, game_dir: str, trusted_roots: list[str]) -> dict:
    path = mod["path"].lower()
    name = os.path.basename(path)
    root = game_dir.lower().rstrip("\\") + "\\" if game_dir.lower() else ""

    if name in KNOWN_CHEAT_MODULES:
        return {"level": 2, "status": "ALTA",
                "reason": "artefato conhecido do projeto v8"}
    if root and path.startswith(root):
        return {"level": 0, "status": "OK", "reason": "diretório do jogo"}
    for trusted in trusted_roots:
        if path.startswith(trusted.lower()):
            return {"level": 0, "status": "OK", "reason": "raiz confiável"}
    for marker in TRUSTED_PATH_MARKERS:
        if marker in path:
            return {"level": 0, "status": "OK", "reason": "instalação Steam"}

    reason = "local não confiável"
    high = False
    base_noext = os.path.splitext(name)[0]
    in_temp = "\\temp\\" in path or "appdata\\local\\temp" in path
    if in_temp:
        high = True
        reason += " + diretório temp"
    if _is_hex_random(base_noext):
        high = True
        reason += " + nome hex aleatório"

    return {"level": 2 if high else 1,
            "status": "ALTA" if high else "SUSPEITO",
            "reason": reason}


def _is_hex_random(name: str) -> bool:
    if len(name) < 6:
        return False
    return all(c in "0123456789abcdef" for c in name.lower())


# ---------------------------------------------------------------------------
# Estágio C — scan de strings na memória
# ---------------------------------------------------------------------------
def _scan_memory_strings(hproc: int) -> list[tuple[str, int]]:
    si = SYSTEM_INFO()
    kernel32.GetSystemInfo(ctypes.byref(si))
    addr = int(si.lpMinimumApplicationAddress or 0)
    max_addr = int(si.lpMaximumApplicationAddress or 0)
    chunk = 1 << 20
    hits: list[tuple[str, int]] = []
    needles = [s.lower().encode() for s in KNOWN_MEMORY_SIGNATURES]

    mbi = MEMORY_BASIC_INFORMATION()
    while addr < max_addr:
        if _virtual_query(hproc, addr, mbi) == 0:
            break
        if mbi.State == MEM_COMMIT and mbi.RegionSize > 0:
            prot = mbi.Protect & 0xFF
            readable = prot in (
                PAGE_READONLY, PAGE_READWRITE, PAGE_WRITECOPY,
                PAGE_EXECUTE_READ, PAGE_EXECUTE_READWRITE, PAGE_EXECUTE_WRITECOPY,
            )
            if readable:
                base = int(mbi.BaseAddress)
                total = int(mbi.RegionSize)
                done = 0
                while done < total:
                    want = min(chunk, total - done)
                    data = _read_mem(hproc, base + done, want)
                    if data:
                        low = data.lower()
                        for i, needle in enumerate(needles):
                            if needle in low:
                                hits.append((KNOWN_MEMORY_SIGNATURES[i],
                                             base + done + low.find(needle)))
                    done += want
        addr = int(mbi.BaseAddress) + int(mbi.RegionSize)
    return hits


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------
class WindowsScanner(ScannerBase):
    """Scanner real de processo do Windows (CS 1.6)."""

    def __init__(self) -> None:
        self._game_dir = ""
        self.mode = "real"

    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        return os.name == "nt" and kernel32 is not None

    def list_processes(self) -> list[dict]:
        if not self.is_available():
            return []
        procs = _enum_processes()
        out = []
        for p in procs:
            name_l = p["name"].lower()
            if name_l in TARGET_PROCESS_NAMES:
                out.append({"name": p["name"], "pid": p["pid"],
                            "title": "", "path": p["name"]})
        return out

    # ------------------------------------------------------------------
    def scan(self, pid: int | None = None) -> "object":
        if not self.is_available():
            report = new_report({}, simulated=True)
            report.verdict = "indisponivel"
            report.add_finding(Finding(
                stage="S",
                severity="medium",
                title="Scanner indisponível",
                detail=("O scan real de memória só roda no Windows. "
                        "Inicie este servidor no Windows ou use o modo demo."),
            ))
            report.compute_verdict()
            return report

        # localizar processo
        target = None
        if pid:
            # valida o PID contra os processos conhecidos do jogo
            procs = self.list_processes()
            for p in procs:
                if p["pid"] == pid:
                    target = p
                    break
            if target is None:
                report = new_report({}, simulated=False)
                report.verdict = "sem_processo"
                report.warning = (
                    f"Não foi encontrado o processo indicado (pid {pid}). "
                    "Ele pode ter sido encerrado — limpe o processo e tente "
                    "novamente para detectar automaticamente."
                )
                return report
        else:
            procs = self.list_processes()
            if not procs:
                report = new_report({}, simulated=False)
                report.verdict = "sem_processo"
                report.warning = (
                    "Não foi encontrado processo do Counter-Strike conhecido "
                    f"({', '.join(TARGET_PROCESS_NAMES)}). "
                    "Inicie o jogo e tente novamente."
                )
                return report
            target = procs[0]

        report = new_report(target, simulated=False)
        hproc = _open_process(target["pid"])
        if not hproc:
            report.verdict = "indisponivel"
            report.warning = (
                "Não foi possível abrir o processo para leitura de memória. "
                "Execute o servidor com os mesmos privilégios do jogo (ou como "
                "administrador)."
            )
            report.add_finding(Finding(
                stage="S", severity="medium",
                title="Não foi possível abrir o processo",
                detail=("OpenProcess falhou. Execute com os mesmos privilégios "
                        "do jogo (ou como administrador)."),
            ))
            report.compute_verdict()
            return report

        try:
            self._stage_a(hproc, report)
            self._stage_b(hproc, report)
            self._stage_c(hproc, report)
        finally:
            kernel32.CloseHandle(hproc)

        report.compute_verdict()
        return report

    # ------------------------------------------------------------------
    def _trusted_roots(self) -> list[str]:
        roots = []
        windir = ctypes.create_unicode_buffer(MAX_PATH)
        kernel32.GetSystemDirectoryW(windir, MAX_PATH)
        sysdir = windir.value
        roots.append(sysdir + "\\")
        roots.append(os.path.join(sysdir, "..", ""))          # raiz do Windows
        if sysdir.lower().endswith("system32"):
            roots.append(os.path.join(sysdir, "..", "SysWOW64") + "\\")
        return roots

    def _stage_a(self, hproc: int, report) -> None:
        mods = _enum_modules(report.process["pid"])
        report.modules_checked = len(mods)

        # detecta diretório do jogo a partir do próprio exe (ou engine.dll)
        game_dir = self._game_dir
        if not game_dir:
            for m in mods:
                bn = os.path.basename(m["path"]).lower()
                if bn in ("engine.dll",) + TARGET_PROCESS_NAMES:
                    game_dir = os.path.dirname(m["path"])
                    break
        self._game_dir = game_dir

        # Detecção direcionada: apenas módulos do projeto v8 (ex.: wallhack.dll).
        # A heurística genérica "fora de raiz confiável" foi removida porque
        # gerava falsos positivos com DLLs legítimas (WinSxS, vendor, AV).
        suspicious = []
        for m in mods:
            bn = os.path.basename(m["path"]).lower()
            if bn in KNOWN_CHEAT_MODULES:
                suspicious.append((m, bn))

        if not suspicious:
            report.add_finding(Finding(
                stage="A", severity="ok", title="Nenhum módulo de cheat",
                detail=f"{len(mods)} módulos carregados; nenhum da lista de cheat.",
                evidence=[f"0 módulos da lista de cheat"],
            ))
            return

        for m, bn in suspicious:
            report.add_finding(Finding(
                stage="A", severity="critical",
                title=f"Módulo de cheat injetado: {m['name']}",
                detail=f"{m['name']} é artefato conhecido do projeto v8 (wallhack).",
                evidence=[m["name"], m["path"]],
            ))

    def _stage_b(self, hproc: int, report) -> None:
        mods = _enum_modules(report.process["pid"])
        # A detecção de detour é "positiva" (critical → HACKEADO) apenas quando
        # uma DLL de cheat conhecida está carregada no processo. Um detour órfão
        # (sem o módulo de cheat carregado) é tratado como SUSPEITO, não trapaça ativa.
        cheat_loaded = any(
            os.path.basename(mm["path"]).lower() in KNOWN_CHEAT_MODULES
            for mm in mods
        )
        opengl = [m for m in mods
                  if os.path.basename(m["path"]).lower() == "opengl32.dll"]
        if not opengl:
            report.add_finding(Finding(
                stage="B", severity="ok", title="opengl32.dll não carregado",
                detail="Módulo de OpenGL não presente; nada a verificar.",
            ))
            return

        m = opengl[0]
        img = PeImage.from_file(m["path"])
        if not img:
            report.add_finding(Finding(
                stage="B", severity="low", title="opengl32.dll ilegível no disco",
                detail="Não foi possível parsear a imagem; checagem de bytes pulada.",
            ))
            return

        exports = img.exports()
        base = int(m["base"])
        detections = []
        for e in exports:
            if not e.name or e.rva == 0:
                continue
            if e.name not in OPENGL_HOOK_TARGETS:
                continue  # só analisa os alvos reais do wallhack (opengl32)
            foff = img.rva_to_offset(e.rva)
            if foff < 0 or foff + EXPORT_BYTES_TO_COMPARE > len(img.data):
                continue
            disk = img.data[foff:foff + EXPORT_BYTES_TO_COMPARE]
            mem = _read_mem(hproc, base + e.rva, EXPORT_BYTES_TO_COMPARE)
            if not mem:
                continue
            # Detour real = mem[0]==E9 e o disco NÃO é E9. Jump nativo (stub de
            # opengl32 que já começa com E9) NÃO é contado como hook.
            # Patch no prólogo = byte de entrada diverge do disco.
            # Divergência "fina" (só bytes posteriores, típico de relocação) não conta.
            inline_hook = mem[0] == INLINE_HOOK_BYTE and disk[0] != INLINE_HOOK_BYTE
            entry_patch = mem[0] != disk[0]
            if inline_hook or entry_patch:
                detections.append((e.name, mem, disk, inline_hook, entry_patch))

        # agrega: o achado mais grave primeiro
        if not detections:
            report.add_finding(Finding(
                stage="B", severity="ok", title="opengl32.dll íntegro",
                detail=f"{len(exports)} exports de alvo verificados sem hook/patch.",
                evidence=[f"{len(exports)} exports verificados"],
            ))
            return

        for name, mem, disk, inline_hook, entry_patch in detections:
            positive = inline_hook and cheat_loaded   # só positivo com a DLL de cheat carregada
            sev = "critical" if positive else "high"
            label = ("Detour inline" if positive
                     else ("Detour (suspeito)" if inline_hook else "Patch no prólogo"))
            title = f"{label} em {name} (alvo do wallhack v8)"
            detail = ("Primeiro byte 0xE9 (jmp rel32) com DLL de cheat carregada."
                      if positive
                      else "Byte de entrada parece alterado, mas não há DLL de cheat "
                           "carregada — trata-se de suspeita, não de trapaça ativa.")
            report.add_finding(Finding(
                stage="B", severity=sev, title=title, detail=detail,
                evidence=[
                    name,
                    f"mem={mem[:4].hex(' ')} | disk={disk[:4].hex(' ')}",
                    "alvo do wallhack v8",
                ],
            ))

    def _stage_c(self, hproc: int, report) -> None:
        # artefatos de log
        artifacts = []
        for log in KNOWN_LOG_FILES:
            if os.path.exists(log):
                artifacts.append(("log", log))
        if artifacts:
            for kind, path in artifacts:
                report.add_finding(Finding(
                    stage="C", severity="high",
                    title="Arquivo de log do cheat presente",
                    detail=path,
                    evidence=[path],
                ))
        else:
            report.add_finding(Finding(
                stage="C", severity="ok", title="Nenhum log de cheat",
                detail="Nenhum arquivo conhecido em C:\\Temp.",
            ))

        # strings na memória
        hits = _scan_memory_strings(hproc)
        if hits:
            for sig, addr in hits[:6]:
                report.add_finding(Finding(
                    stage="C", severity="medium",
                    title=f"String '{sig}' na memória",
                    detail=f"Assinatura do cheat em 0x{addr:X}.",
                    evidence=[f"'{sig}' @ 0x{addr:X}"],
                ))
        else:
            report.add_finding(Finding(
                stage="C", severity="ok", title="Nenhuma string de cheat",
                detail=f"{len(KNOWN_MEMORY_SIGNATURES)} assinaturas ausentes.",
            ))
