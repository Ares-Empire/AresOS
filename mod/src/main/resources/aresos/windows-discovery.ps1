param([string]$RequestFile, [string]$OutputFile)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class AresIcon {
 [DllImport("shell32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr CommandLineToArgvW(string command, out int count);
 [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr memory);
 public static string[] Arguments(string command) {
  // A placeholder argv[0] keeps executable-name parsing out of the shortcut arguments.
  int count; IntPtr memory = CommandLineToArgvW("aresos-argv.exe " + command, out count);
  if (memory == IntPtr.Zero) throw new System.ComponentModel.Win32Exception();
  try {
   var args = new string[count - 1];
   for (int i = 1; i < count; i++) args[i - 1] = Marshal.PtrToStringUni(Marshal.ReadIntPtr(memory, i * IntPtr.Size));
   return args;
  } finally { LocalFree(memory); }
 }
 [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
 public struct Info { public IntPtr hIcon; public int index; public uint attributes;
 [MarshalAs(UnmanagedType.ByValTStr, SizeConst=260)] public string display;
 [MarshalAs(UnmanagedType.ByValTStr, SizeConst=80)] public string type; }
 [DllImport("shell32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SHGetFileInfo(string path, uint a, out Info i, uint size, uint flags);
 [DllImport("user32.dll")] public static extern bool DestroyIcon(IntPtr icon);
 [DllImport("shell32.dll", CharSet=CharSet.Unicode)] public static extern uint ExtractIconEx(string path, int index, IntPtr[] large, IntPtr[] small, uint count);
}
"@
function Read-Icon($Path, $Location) {
 $handle = [IntPtr]::Zero
 try {
  if ($Location -match '^(.*),(-?[0-9]+)$') {
   $iconPath = [Environment]::ExpandEnvironmentVariables($Matches[1].Trim('"'))
   $large = New-Object IntPtr[] 1; $small = New-Object IntPtr[] 1
   [void][AresIcon]::ExtractIconEx($iconPath, [int]$Matches[2], $large, $small, 1)
   $handle = $large[0]
   if ($small[0] -ne [IntPtr]::Zero) { [void][AresIcon]::DestroyIcon($small[0]) }
  }
  if ($handle -eq [IntPtr]::Zero) {
   $info = New-Object AresIcon+Info
   [void][AresIcon]::SHGetFileInfo($Path, 0, [ref]$info, [Runtime.InteropServices.Marshal]::SizeOf($info), 256)
   $handle = $info.hIcon
  }
  if ($handle -eq [IntPtr]::Zero) { return $null }
  $icon = [Drawing.Icon]::FromHandle($handle); $bitmap = $icon.ToBitmap(); $stream = New-Object IO.MemoryStream
  try { $bitmap.Save($stream, [Drawing.Imaging.ImageFormat]::Png); return [Convert]::ToBase64String($stream.ToArray()) }
  finally { $stream.Dispose(); $bitmap.Dispose(); $icon.Dispose() }
 } catch { return $null }
 finally { if ($handle -ne [IntPtr]::Zero) { [void][AresIcon]::DestroyIcon($handle) } }
}
$request = Get-Content -LiteralPath $RequestFile -Raw -Encoding UTF8 | ConvertFrom-Json
$rows = New-Object 'Collections.Generic.List[object]'
if ($request.PSObject.Properties.Name -contains 'roots') { $roots = $request.roots }
else { $roots = @([Environment]::GetFolderPath('StartMenu'), [Environment]::GetFolderPath('CommonStartMenu')) }
$shell = New-Object -ComObject WScript.Shell
$shellApps = New-Object -ComObject Shell.Application
foreach ($root in $roots) {
 if (-not (Test-Path -LiteralPath $root)) { continue }
 foreach ($file in Get-ChildItem -LiteralPath $root -Filter '*.lnk' -File -Recurse | Sort-Object FullName) {
  $link = $shell.CreateShortcut($file.FullName)
  $aumid = $shellApps.NameSpace($file.DirectoryName).ParseName($file.Name).ExtendedProperty('System.AppUserModel.ID')
  $rows.Add(@{kind='shortcut'; key=$file.FullName.Substring($root.Length).TrimStart('\'); name=$file.BaseName;
    launch=$file.FullName; target=$link.TargetPath; arguments=$link.Arguments; argv=@([AresIcon]::Arguments($link.Arguments));
    workingDirectory=$link.WorkingDirectory; aumid=$aumid; icon=(Read-Icon $file.FullName $link.IconLocation)})
 }
}
if ($request.PSObject.Properties.Name -contains 'uwp') { foreach ($row in $request.uwp) { $rows.Add($row) } }
else {
 $packages = @(Get-AppxPackage)
 $apps = (New-Object -ComObject Shell.Application).NameSpace('shell:::{4234d49b-0245-4df3-b780-3893943456e1}').Items()
 foreach ($app in $apps) {
  $aumid = $app.Path
  if ($aumid -notlike '*!*') { continue }
  $logo = $null
  $package = $packages | Where-Object { $aumid.StartsWith($_.PackageFamilyName + '!') } | Select-Object -First 1
  if ($package) {
   try {
    $manifest = Get-AppxPackageManifest $package
    $application = $manifest.Package.Applications.Application | Where-Object { $aumid.EndsWith('!' + $_.Id) } | Select-Object -First 1
    $relative = $application.VisualElements.Square44x44Logo
    if (-not $relative) { $relative = $manifest.Package.Properties.Logo }
    if ($relative) {
     $path = Join-Path $package.InstallLocation $relative
     if (-not (Test-Path -LiteralPath $path)) {
      $folder = Split-Path $path; $stem = [IO.Path]::GetFileNameWithoutExtension($path)
      $path = (Get-ChildItem -LiteralPath $folder -Filter ($stem + '*.png') | Sort-Object Name | Select-Object -First 1).FullName
     }
     if ($path) { $logo = [Convert]::ToBase64String([IO.File]::ReadAllBytes($path)) }
    }
   } catch { $logo = $null }
  }
  $rows.Add(@{kind='uwp'; key=$aumid; name=$app.Name; icon=$logo})
 }
}
foreach ($entry in $request.configuredIcons) {
 $path = $entry.path
 if (-not [IO.Path]::IsPathRooted($path)) {
  $resolved = Get-Command -Name $path -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($resolved) { $path = $resolved.Source }
 }
 $icon = $null
 if ($entry.extractIcon -and (Test-Path -LiteralPath $path -PathType Leaf)) { $icon = Read-Icon $path '' }
 $rows.Add(@{kind='configured'; key=$entry.id; target=$path; icon=$icon})
}
$json = ConvertTo-Json -InputObject @($rows.ToArray()) -Depth 8
[IO.File]::WriteAllText($OutputFile, $json, (New-Object Text.UTF8Encoding($false)))
