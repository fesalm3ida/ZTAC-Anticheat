"""Assinaturas de detecção — derivadas do anti-cheat v8.

Estas constantes espelham exatamente o que os módulos do laboratório v8
(hook_v8.dll, wallhack.dll, aimbot_v8.dll, main_v8.dll) produzem em runtime.
São usadas pelos três estágios de detecção:

  Estágio A — módulos injetados (lista negra + heurística de caminho)
  Estágio B — detours inline no opengl32.dll (disco x memória)
  Estágio C — artefatos (logs em C:\\Temp) e strings na memória
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Estágio A — módulos do projeto v8 (lista negra explícita do laboratório)
# ---------------------------------------------------------------------------
KNOWN_CHEAT_MODULES = {
    "hook_v8.dll",
    "wallhack.dll",
    "aimbot_v8.dll",
    "main_v8.dll",
    "wallhack_v8.dll",
    "aimbot.dll",
    "hook.dll",
}

# Substrings de caminho consideradas "raiz confiável" (o módulo é legítimo)
TRUSTED_PATH_MARKERS = (
    "\\steam\\",
    "\\system32\\",
    "\\syswow64\\",
)

# ---------------------------------------------------------------------------
# Estágio B — funções do opengl32.dll que o main_v8.cpp hooka
# ---------------------------------------------------------------------------
OPENGL_HOOK_TARGETS = {
    "wglSwapBuffers",
    "wglMakeCurrent",
    "glBegin",
    "glEnd",
    "glEnable",
    "glDisable",
    "glDepthFunc",
    "glStencilFunc",
}

# Código de detour inline usado pelo v8 (E9 + rel32) — primeiro byte
INLINE_HOOK_BYTE = 0xE9

# Número de bytes comparados entre disco e memória por export
EXPORT_BYTES_TO_COMPARE = 16

# ---------------------------------------------------------------------------
# Estágio C — strings características na memória do processo
# ---------------------------------------------------------------------------
KNOWN_MEMORY_SIGNATURES = (
    "AIMBOT PRONTO",
    "AIMBOT ATIVADO",
    "WALLHACK DLL CARREGADA",
    "WALLHACK COMPLETO ATIVADO",
    "ForceWallhack",
    "hk_wglSwapBuffers",
    "Aimbot_Debug.txt",
    "Wallhack_autotarget_Debug.txt",
    "Wallhack_Debug.txt",
    "hook_v8.dll",
    "wallhack.dll",
)

# Arquivos de log gravados pelos módulos v8 em C:\Temp
KNOWN_LOG_FILES = (
    r"C:\Temp\Aimbot_Debug.txt",
    r"C:\Temp\Wallhack_Debug.txt",
    r"C:\Temp\Wallhack_autotarget_Debug.txt",
)

# ---------------------------------------------------------------------------
# Peso (score) e severidade por tipo de achado — usados no veredito
# ---------------------------------------------------------------------------
SEVERITY_WEIGHT = {
    "ok": 0,
    "low": 8,
    "medium": 20,
    "high": 40,
    "critical": 55,
}

MAX_SCORE = 100
