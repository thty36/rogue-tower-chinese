# 自动验证脚本：等待游戏关闭 → 启动带插件的实例 → 点击 中/EN 按钮 → 截图验证
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class M {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint data, UIntPtr extra);
}
'@

function Shot($path) {
  $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
  $bmp.Save($path)
  $g.Dispose(); $bmp.Dispose()
}

$out = 'C:\Users\fanchengpeng\.zcode\workspace\default\rogue-tower-cn\docs'
# 1. 等游戏关闭（最多 25 分钟）
$waited = 0
while ($waited -lt 1500) {
  $p = Get-Process 'Rogue Tower' -ErrorAction SilentlyContinue
  if (-not $p) { break }
  Start-Sleep -Seconds 10
  $waited += 10
}
if (Get-Process 'Rogue Tower' -ErrorAction SilentlyContinue) {
  Write-Output 'TIMEOUT: game still running, skip test'
  exit 0
}
Write-Output 'game closed, launching modded instance'
# 2. 启动
Start-Process -FilePath 'D:\Steam\steamapps\common\Rogue Tower\Rogue Tower.exe' -WorkingDirectory 'D:\Steam\steamapps\common\Rogue Tower'
Start-Sleep -Seconds 35
# 激活游戏窗口（点击标题栏区域避免干扰菜单）— 先把鼠标移到窗口中部激活
[M]::SetCursorPos(1280, 400) | Out-Null
Start-Sleep -Seconds 2
Shot "$out\toggle_test_1_zh.png"
Write-Output 'shot1 saved'
# 3. 点击右上角 中/EN 按钮（2560x1440 下按钮中心约 (2519, 22)）
Start-Sleep -Seconds 1
[M]::SetCursorPos(2519, 22) | Out-Null
Start-Sleep -Milliseconds 400
[M]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero)   # LEFTDOWN
Start-Sleep -Milliseconds 60
[M]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero)   # LEFTUP
Write-Output 'clicked toggle (to EN)'
Start-Sleep -Seconds 3
Shot "$out\toggle_test_2_en.png"
Write-Output 'shot2 saved'
# 4. 再点一次切回中文
[M]::SetCursorPos(2519, 22) | Out-Null
Start-Sleep -Milliseconds 400
[M]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
[M]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero)
Write-Output 'clicked toggle (back to ZH)'
Start-Sleep -Seconds 3
Shot "$out\toggle_test_3_zh.png"
Write-Output 'shot3 saved'
# 5. 关闭测试实例
Stop-Process -Name 'Rogue Tower' -Force -ErrorAction SilentlyContinue
Write-Output 'test instance closed'
