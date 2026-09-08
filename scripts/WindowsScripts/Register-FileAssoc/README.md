# Windows 工具脚本集

## 使用方式

1. 打开脚本，改顶部两行参数：
   - $Extension = ".abc" ← 你的扩展名
   - $AppPath = "C:\xxx\app.exe" ← 你的程序路径
2. 右键 PowerShell → 以管理员身份运行
3. cd 到脚本目录，执行 .\Register-FileAssoc.ps1

## 注意事项

- HKLM 写入必须管理员权限，脚本会自动检查
- 改完立即生效，不用重启
- 常见类型（.pdf/.html 等）可能被系统锁，需额外处理

## 常用命令

# 检查是否管理员
([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole("Administrator")

# 刷新文件关联缓存
ie4uinit.exe -show
