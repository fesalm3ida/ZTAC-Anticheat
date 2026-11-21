#include <windows.h>

extern "C" __declspec(dllexport) LRESULT CALLBACK HookProc(int nCode, WPARAM wParam, LPARAM lParam) {
    static bool injected = false;

    if (!injected) {
        // Caminho absoluto da wallhack.dll - AJUSTE CONFORME NECESSÁRIO
        HMODULE hMod = LoadLibraryA("C:\\Temp\\wallhack.dll");
        if (hMod) {
            injected = true;
        }
    }

    return CallNextHookEx(NULL, nCode, wParam, lParam);
}

extern "C" __declspec(dllexport) void DummyFunction() {}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID lpReserved) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hModule);
    }
    return TRUE;
}