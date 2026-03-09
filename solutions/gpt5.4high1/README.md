#

https://arena.ai/c/019cc991-e7b0-77f4-a07a-8e413ce93ebe

## Запуск

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_windows_bundle.ps1 -Clean
powershell -ExecutionPolicy Bypass -File .\dist\pcontext-windows\windows_install_bundle.ps1 -RestartExplorer
& "$env:LOCALAPPDATA\PContext\app\pcontext-gui.exe"
# .\dist\pcontext-windows\pcontext-gui.exe
```
