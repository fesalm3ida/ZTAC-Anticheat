#include <windows.h>
#include <gl/gl.h>
#include <stdio.h>
#include <tlhelp32.h>
#include <time.h>

// ========== LOG COM TIMESTAMP ==========
void Log(const char* msg) {
    FILE* f = fopen("C:\\Temp\\Wallhack_Debug.txt", "a");
    if (f) {
        SYSTEMTIME st;
        GetLocalTime(&st);
        fprintf(f, "[%02d:%02d:%02d.%03d] %s\n", 
                st.wHour, st.wMinute, st.wSecond, st.wMilliseconds, msg);
        fclose(f);
    }
}

// ========== VARIÁVEIS GLOBAIS ==========
FARPROC g_Original[8] = {NULL};
bool g_bWallhackActive = false;
int g_keyWallhack = VK_HOME;
int g_frameCount = 0;
bool g_bIsDrawingModel = false;

enum {
    IDX_WGLSWAPBUFFERS = 0,
    IDX_WGLMAKECURRENT = 1,
    IDX_GLBEGIN = 2,
    IDX_GLEND = 3,
    IDX_GLENABLE = 4,
    IDX_GLDISABLE = 5,
    IDX_GLDEPTHFUNC = 6,
    IDX_GLSTENCILFUNC = 7
};

// ========== DETOUR ==========
void* DetourFunction(PBYTE src, const PBYTE dst, const int len) {
    PBYTE jmp = (PBYTE)VirtualAlloc(NULL, len + 5, MEM_COMMIT, PAGE_EXECUTE_READWRITE);
    if (!jmp) return NULL;
    
    DWORD dwback;
    VirtualProtect(src, len, PAGE_EXECUTE_READWRITE, &dwback);
    
    memcpy(jmp, src, len);
    jmp += len;
    
    jmp[0] = 0xE9;
    *(DWORD*)(jmp + 1) = (DWORD)(src + len - jmp) - 5;
    
    src[0] = 0xE9;
    *(DWORD*)(src + 1) = (DWORD)(dst - src) - 5;
    
    for (int i = 5; i < len; i++) src[i] = 0x90;
    
    VirtualProtect(src, len, dwback, &dwback);
    return (jmp - len);
}

// ========== FUNÇÃO PARA FORÇAR WALLHACK ==========
void ForceWallhack() {
    if (!g_bWallhackActive) return;
    
    HGLRC current = wglGetCurrentContext();
    if (!current) return;
    
    // 1. Desativa depth test
    glDisable(GL_DEPTH_TEST);
    
    // 2. Força depth function a sempre passar
    glDepthFunc(GL_ALWAYS);
    
    // 3. Desativa escrita no depth buffer
    glDepthMask(GL_FALSE);
    
    // 4. Desativa culling
    glDisable(GL_CULL_FACE);
    
    // 5. Força polígonos a aparecerem na frente
    glEnable(GL_POLYGON_OFFSET_FILL);
    glPolygonOffset(-1.0f, -1.0f);
    
    // 6. Desativa stencil test
    glDisable(GL_STENCIL_TEST);
    
    // 7. Desativa alpha test
    glDisable(GL_ALPHA_TEST);
    
    static bool logged = false;
    if (!logged) {
        Log("ForceWallhack: todas as configurações aplicadas");
        logged = true;
    }
}

// ========== HOOK GLSTENCILFUNC ==========
void WINAPI hk_glStencilFunc(GLenum func, GLint ref, GLuint mask) {
    static int callCount = 0;
    callCount++;
    
    if (g_bWallhackActive && callCount % 100 == 0) {
        char msg[256];
        sprintf(msg, "hk_glStencilFunc: #%d func=0x%X", callCount, func);
        Log(msg);
    }
    
    // Bloqueia stencil test se wallhack ativo
    if (g_bWallhackActive) {
        glDisable(GL_STENCIL_TEST);
        return;
    }
    
    if (g_Original[IDX_GLSTENCILFUNC]) {
        ((void (WINAPI*)(GLenum, GLint, GLuint))g_Original[IDX_GLSTENCILFUNC])(func, ref, mask);
    }
}

// ========== HOOK GLBEGIN ==========
void WINAPI hk_glBegin(GLenum mode) {
    static int callCount = 0;
    callCount++;
    
    // Modos de modelo no CS 1.6 (GL_TRIANGLE_STRIP, GL_TRIANGLE_FAN, GL_QUADS, GL_POLYGON)
    bool isModelMode = (mode == 0x0005 || mode == 0x0006 || mode == 0x0007 || mode == 0x0009);
    
    if (isModelMode) {
        g_bIsDrawingModel = true;
        
        if (g_bWallhackActive) {
            ForceWallhack();
            
            if (callCount % 100 == 0) {
                char msg[256];
                sprintf(msg, "hk_glBegin: WALLHACK APLICADO mode=0x%X #%d", mode, callCount);
                Log(msg);
            }
        }
    }
    
    if (g_Original[IDX_GLBEGIN]) {
        ((void (WINAPI*)(GLenum))g_Original[IDX_GLBEGIN])(mode);
    }
}

// ========== HOOK GLEND ==========
void WINAPI hk_glEnd() {
    g_bIsDrawingModel = false;
    
    if (g_Original[IDX_GLEND]) {
        ((void (WINAPI*)())g_Original[IDX_GLEND])();
    }
}

// ========== HOOK GLENABLE ==========
void WINAPI hk_glEnable(GLenum cap) {
    // Bloqueia reativação de depth/stencil/cull durante desenho de modelo
    if (g_bWallhackActive && g_bIsDrawingModel) {
        if (cap == GL_DEPTH_TEST || cap == GL_STENCIL_TEST || cap == GL_CULL_FACE) {
            return;
        }
    }
    
    if (g_Original[IDX_GLENABLE]) {
        ((void (WINAPI*)(GLenum))g_Original[IDX_GLENABLE])(cap);
    }
}

// ========== HOOK GLDISABLE ==========
void WINAPI hk_glDisable(GLenum cap) {
    // Não bloqueamos disables, apenas monitoramos
    if (g_bWallhackActive && cap == GL_DEPTH_TEST && g_bIsDrawingModel) {
        // O jogo está tentando desativar depth test, mas vamos manter nosso estado
        static int warnCount = 0;
        if (warnCount++ % 100 == 0) {
            Log("hk_glDisable: depth test sendo desativado (ignorado)");
        }
    }
    
    if (g_Original[IDX_GLDISABLE]) {
        ((void (WINAPI*)(GLenum))g_Original[IDX_GLDISABLE])(cap);
    }
}

// ========== HOOK GLDEPTHFUNC ==========
void WINAPI hk_glDepthFunc(GLenum func) {
    if (g_bWallhackActive) {
        // Força GL_ALWAYS quando wallhack ativo
        if (g_Original[IDX_GLDEPTHFUNC]) {
            ((void (WINAPI*)(GLenum))g_Original[IDX_GLDEPTHFUNC])(GL_ALWAYS);
        }
        return;
    }
    
    if (g_Original[IDX_GLDEPTHFUNC]) {
        ((void (WINAPI*)(GLenum))g_Original[IDX_GLDEPTHFUNC])(func);
    }
}

// ========== HOOK WGL_MAKE_CURRENT ==========
BOOL WINAPI hk_wglMakeCurrent(HDC hdc, HGLRC hglrc) {
    static int callCount = 0;
    callCount++;
    
    BOOL result = FALSE;
    
    if (g_Original[IDX_WGLMAKECURRENT])
        result = ((BOOL (WINAPI*)(HDC, HGLRC))g_Original[IDX_WGLMAKECURRENT])(hdc, hglrc);
    
    // Quando ativa novo contexto e wallhack ativo, aplica configurações
    if (result && hglrc && g_bWallhackActive) {
        ForceWallhack();
        static bool logged = false;
        if (!logged) {
            Log("hk_wglMakeCurrent: configurações aplicadas no novo contexto");
            logged = true;
        }
    }
    
    return result;
}

// ========== HOOK WGL_SWAP_BUFFERS ==========
BOOL WINAPI hk_wglSwapBuffers(HDC hdc) {
    g_frameCount++;
    
    if (g_bWallhackActive) {
        ForceWallhack();
    }
    
    if (g_frameCount % 100 == 0) {
        char msg[256];
        sprintf(msg, "hk_wglSwapBuffers: frame %d active=%d", g_frameCount, g_bWallhackActive);
        Log(msg);
    }
    
    if (g_Original[IDX_WGLSWAPBUFFERS])
        return ((BOOL (WINAPI*)(HDC))g_Original[IDX_WGLSWAPBUFFERS])(hdc);
    return FALSE;
}

// ========== INSTALAR HOOKS VIA DETOUR ==========
bool InstallDetour(const char* dllName, const char* funcName, int index, FARPROC hook) {
    HMODULE hDll = GetModuleHandleA(dllName);
    if (!hDll) {
        char msg[256];
        sprintf(msg, "DLL %s não carregada", dllName);
        Log(msg);
        return false;
    }
    
    FARPROC originalFunc = GetProcAddress(hDll, funcName);
    if (!originalFunc) {
        char msg[256];
        sprintf(msg, "Função %s não encontrada", funcName);
        Log(msg);
        return false;
    }
    
    g_Original[index] = originalFunc;
    
    char msg[256];
    sprintf(msg, "Instalando detour em %s!%s em 0x%p", dllName, funcName, originalFunc);
    Log(msg);
    
    DetourFunction((PBYTE)originalFunc, (PBYTE)hook, 5);
    
    sprintf(msg, "  Detour instalado com sucesso!");
    Log(msg);
    return true;
}

// ========== THREAD PARA VERIFICAR TECLA ==========
DWORD WINAPI KeyThread(LPVOID lpParam) {
    Log("KeyThread: iniciada");
    int lastKeyState = 0;
    
    while (true) {
        int keyState = GetAsyncKeyState(g_keyWallhack);
        if ((keyState & 1) && !lastKeyState) {
            g_bWallhackActive = !g_bWallhackActive;
            Log(g_bWallhackActive ? ">>> WALLHACK COMPLETO ATIVADO! <<<" : ">>> WALLHACK DESATIVADO! <<<");
            
            if (g_bWallhackActive) {
                ForceWallhack();
            }
        }
        lastKeyState = keyState & 1;
        Sleep(50);
    }
    return 0;
}

// ========== THREAD DE INICIALIZAÇÃO ==========
DWORD WINAPI InitThread(LPVOID lpParam) {
    Log("=== INÍCIO DA INICIALIZAÇÃO ===");
    Log("Aguardando 15 segundos para o jogo estabilizar...");
    
    for (int i = 0; i < 15; i++) {
        Sleep(1000);
        if (i % 5 == 0) {
            char msg[64];
            sprintf(msg, "  Aguardando... %d/15 segundos", i);
            Log(msg);
        }
    }
    
    int successCount = 0;
    
    if (InstallDetour("opengl32.dll", "wglSwapBuffers", IDX_WGLSWAPBUFFERS, (FARPROC)hk_wglSwapBuffers))
        successCount++;
    
    if (InstallDetour("opengl32.dll", "wglMakeCurrent", IDX_WGLMAKECURRENT, (FARPROC)hk_wglMakeCurrent))
        successCount++;
    
    if (InstallDetour("opengl32.dll", "glBegin", IDX_GLBEGIN, (FARPROC)hk_glBegin))
        successCount++;
    
    if (InstallDetour("opengl32.dll", "glEnd", IDX_GLEND, (FARPROC)hk_glEnd))
        successCount++;
    
    if (InstallDetour("opengl32.dll", "glEnable", IDX_GLENABLE, (FARPROC)hk_glEnable))
        successCount++;
    
    if (InstallDetour("opengl32.dll", "glDisable", IDX_GLDISABLE, (FARPROC)hk_glDisable))
        successCount++;
    
    if (InstallDetour("opengl32.dll", "glDepthFunc", IDX_GLDEPTHFUNC, (FARPROC)hk_glDepthFunc))
        successCount++;
    
    if (InstallDetour("opengl32.dll", "glStencilFunc", IDX_GLSTENCILFUNC, (FARPROC)hk_glStencilFunc))
        successCount++;
    
    char msg[256];
    sprintf(msg, "Total: %d hooks instalados com sucesso!", successCount);
    Log(msg);
    
    if (successCount > 0) {
        CreateThread(NULL, 0, KeyThread, NULL, 0, NULL);
    }
    
    Log("=== INICIALIZAÇÃO COMPLETA ===");
    Log("Wallhack completo ativo: depth test desativado, depthFunc=ALWAYS, depthMask=FALSE, cull desativado, polygon offset");
    return 0;
}

// ========== DLL MAIN ==========
BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID lpReserved) {
    if (reason == DLL_PROCESS_ATTACH) {
        CreateDirectoryA("C:\\Temp", NULL);
        
        FILE* f = fopen("C:\\Temp\\Wallhack_Debug.txt", "w");
        if (f) {
            fprintf(f, "=== WALLHACK DLL CARREGADA ===\n");
            fclose(f);
        }
        
        Log("DLL_PROCESS_ATTACH");
        DisableThreadLibraryCalls(hModule);
        CreateThread(NULL, 0, InitThread, NULL, 0, NULL);
    }
    return TRUE;
}