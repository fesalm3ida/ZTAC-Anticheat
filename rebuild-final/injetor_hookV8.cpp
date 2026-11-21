#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>
#include <string.h>

DWORD GetProcessId(const char* procname) {
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    PROCESSENTRY32 pe = { sizeof(PROCESSENTRY32) };
    
    if (hSnapshot == INVALID_HANDLE_VALUE) return 0;
    
    if (Process32First(hSnapshot, &pe)) {
        do {
            if (_stricmp(pe.szExeFile, procname) == 0) {
                CloseHandle(hSnapshot);
                return pe.th32ProcessID;
            }
        } while (Process32Next(hSnapshot, &pe));
    }
    CloseHandle(hSnapshot);
    return 0;
}

// Lista de possíveis processos
const char* processNames[] = {
    "hl.exe", "cstrike.exe", "cs.exe", "cs16.exe", "revolution.exe", NULL
};

int main() {
    printf("=== Injetor via Hook v2 ===\n");
    
    DWORD pid = 0;
    const char* foundProcess = NULL;
    
    for (int i = 0; processNames[i] != NULL; i++) {
        pid = GetProcessId(processNames[i]);
        if (pid) {
            foundProcess = processNames[i];
            printf("Processo encontrado: %s (PID: %d)\n", foundProcess, pid);
            break;
        }
    }
    
    if (!pid) {
        printf("Nenhum processo do CS encontrado!\n");
        return 1;
    }
    
    // Pega o ID da thread principal
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (hSnapshot == INVALID_HANDLE_VALUE) {
        printf("Erro ao criar snapshot de threads\n");
        return 1;
    }
    
    DWORD mainThreadId = 0;
    THREADENTRY32 te = { sizeof(THREADENTRY32) };
    
    if (Thread32First(hSnapshot, &te)) {
        do {
            if (te.th32OwnerProcessID == pid) {
                mainThreadId = te.th32ThreadID;
                printf("Thread principal encontrada: %d\n", mainThreadId);
                break;
            }
        } while (Thread32Next(hSnapshot, &te));
    }
    CloseHandle(hSnapshot);
    
    if (!mainThreadId) {
        printf("Não foi possível encontrar thread do processo\n");
        return 1;
    }
    
    // Carrega a DLL de hook
    char dllPath[MAX_PATH];
    GetCurrentDirectoryA(MAX_PATH, dllPath);
    strcat(dllPath, "\\hook_v8.dll");
    
    printf("Carregando DLL: %s\n", dllPath);
    
    HMODULE hHookDll = LoadLibraryA(dllPath);
    if (!hHookDll) {
        printf("Erro ao carregar hook_v8.dll: %d\n", GetLastError());
        return 1;
    }
    printf("✓ DLL carregada com sucesso! Handle: %p\n", hHookDll);
    
    // Obtém o endereço da função hook
    FARPROC hookProc = GetProcAddress(hHookDll, "HookProc");
    if (!hookProc) {
        printf("HookProc não encontrada, tentando HookProc@12...\n");
        hookProc = GetProcAddress(hHookDll, "HookProc@12");
    }
    
    if (!hookProc) {
        printf("Erro: função HookProc não encontrada!\n");
        FreeLibrary(hHookDll);
        return 1;
    }
    
    printf("✓ HookProc encontrada em: %p\n", hookProc);
    
    printf("Instalando hook com SetWindowsHookEx...\n");
    printf("  idHook: WH_GETMESSAGE (3)\n");
    printf("  hookProc: %p\n", hookProc);
    printf("  hMod: %p (hook_dll.dll)\n", hHookDll);
    printf("  threadId: %d\n", mainThreadId);
    
    HHOOK hHook = SetWindowsHookEx(
        WH_GETMESSAGE,
        (HOOKPROC)hookProc,
        hHookDll,
        mainThreadId
    );
    
    DWORD lastError = GetLastError();
    
    if (hHook) {
        printf("✓ Hook instalado com sucesso! Handle: %p\n", hHook);
        
        PostThreadMessage(mainThreadId, WM_NULL, 0, 0);
        
        printf("Aguardando 2 segundos...\n");
        Sleep(2000);
        
        UnhookWindowsHookEx(hHook);
        printf("Hook removido.\n");
    } else {
        printf("✗ Erro ao instalar hook: %d\n", lastError);
        
        printf("\nTentando com WH_CALLWNDPROC...\n");
        hHook = SetWindowsHookEx(
            WH_CALLWNDPROC,
            (HOOKPROC)hookProc,
            hHookDll,
            mainThreadId
        );
        
        lastError = GetLastError();
        if (hHook) {
            printf("✓ Hook WH_CALLWNDPROC instalado!\n");
            UnhookWindowsHookEx(hHook);
        } else {
            printf("✗ Erro: %d\n", lastError);
        }
    }
    
    FreeLibrary(hHookDll);
    
    return 0;
}