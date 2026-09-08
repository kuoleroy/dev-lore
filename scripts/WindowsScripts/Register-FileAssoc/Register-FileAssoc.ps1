# ============================================================
# 文件格式关联脚本（通用版）
# 用法：填好下面两个变量，右键「以管理员身份运行」即可
# ============================================================

# ====== 你需要填的地方（只改这两行）==========================
$Extension = ".abc"                      # 要关联的扩展名（带点），例如 .md .json .xyz
$AppPath   = "C:\Program Files\MyApp\MyApp.exe"   # 打开该文件的程序完整路径
# ============================================================

$ProgId = "MyApp." + $Extension.TrimStart('.')   # 自定义 ProgID，一般不用改
$Command = "`"$AppPath`" `"%1`""                   # 打开命令（%1 = 双击的文件路径）

# ---------- 权限自检（不是管理员会自动提示，无需手动判断）----------
if (-not ([Security.Principal.WindowsPrincipal] `
          [Security.Principal.WindowsIdentity]::GetCurrent()
         ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "⚠️ 请以「管理员身份」运行本脚本！" -ForegroundColor Red
    pause; exit 1
}

# ---------- 1. 写 ProgID（HKLM 全局 / 改 HKCU 则无需管理员）----------
New-Item -Path "HKLM:\Software\Classes\$ProgId" -Force | Out-Null
New-Item -Path "HKLM:\Software\Classes\$ProgId\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path "HKLM:\Software\Classes\$ProgId\shell\open\command" `
                 -Name "(Default)" -Value $Command
Write-Host "✅ ProgID 已创建：$ProgId  ->  $Command"

# ---------- 2. 扩展名指向 ProgID ----------
New-Item -Path "HKLM:\Software\Classes\$Extension" -Force | Out-Null
Set-ItemProperty -Path "HKLM:\Software\Classes\$Extension" `
                 -Name "(Default)" -Value $ProgId
Write-Host "✅ 扩展名已关联：$Extension  ->  $ProgId"

# ---------- 3. 刷新系统（让资源管理器立即生效）----------
$code = @'
using System;
using System.Runtime.InteropServices;
public class Shell {
    [DllImport("shell32.dll")] public static extern void SHChangeNotify(int w, int l, IntPtr p1, IntPtr p2);
}
'@
Add-Type $code
[Shell]::SHChangeNotify(0x8000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)  # SHCNE_ASSOCCHANGED

Write-Host "`n🎉 完成！双击任意 $Extension 文件即可用 $AppPath 打开。" -ForegroundColor Green
pause
