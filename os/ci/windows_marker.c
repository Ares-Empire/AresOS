/* Original VM-only marker; no Windows executable or artwork is distributed. */
#include <efi.h>
#include <efilib.h>

static void record(CHAR16 *text) {
    Print(L"%s", text);
    for (; *text; text++) {
        unsigned char byte = *text < 128 ? *text : '?';
        __asm__ volatile("outb %0, %1" : : "a"(byte), "Nd"((unsigned short)0x402));
    }
}

EFI_STATUS efi_main(EFI_HANDLE handle, EFI_SYSTEM_TABLE *table) {
    EFI_LOADED_IMAGE *image;
    EFI_GUID global = EFI_GLOBAL_VARIABLE;
    UINT16 current = 0xffff;
    UINTN size = sizeof(current);
    CHAR16 buffer[100];
    InitializeLib(handle, table);
    uefi_call_wrapper(RT->GetVariable, 5, L"BootCurrent", &global, NULL, &size, &current);
    SPrint(buffer, sizeof(buffer), L"ARESOS_WINDOWS_MARKER BootCurrent=%04x\r\n", current);
    record(buffer);
    if (EFI_ERROR(uefi_call_wrapper(BS->HandleProtocol, 3, handle, &LoadedImageProtocol, (VOID **)&image)))
        return EFI_LOAD_ERROR;
    record(L"Device=");
    record(DevicePathToStr(DevicePathFromHandle(image->DeviceHandle)));
    record(L"\r\nFile=");
    record(DevicePathToStr(image->FilePath));
    record(L"\r\nMARKER_BOOT_COMPLETE\r\n");
    uefi_call_wrapper(BS->Stall, 1, 10000000);
    uefi_call_wrapper(RT->ResetSystem, 4, EfiResetShutdown, EFI_SUCCESS, 0, NULL);
    return EFI_SUCCESS;
}
