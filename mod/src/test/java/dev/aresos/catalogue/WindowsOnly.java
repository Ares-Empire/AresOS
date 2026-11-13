package dev.aresos.catalogue;

/**
 * Why some Windows catalogue tests run only on Windows (brief 29): they exercise a Windows-only path of the mod,
 * which never runs on AresOS. They still run unchanged on Windows.
 */
final class WindowsOnly {
    /** They build Start Menu shortcuts with PowerShell (WScript.Shell) and run the PowerShell discovery script. */
    static final String POWERSHELL = "Windows only: needs PowerShell for shortcut fixtures and app discovery";
    /** Notepad's known paths are resolved with the host's path rules; elsewhere C:\Windows\notepad.exe is relative. */
    static final String WINDOWS_PATHS = "Windows only: Notepad's known paths resolve with a Windows host's path rules";

    private WindowsOnly() { }
}
