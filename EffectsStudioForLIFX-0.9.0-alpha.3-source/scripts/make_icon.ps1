$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

$projectRoot = Split-Path -Parent $PSScriptRoot
$outputPath = Join-Path $projectRoot "assets\lifx-effects-studio.ico"
$bitmap = [System.Drawing.Bitmap]::new(256, 256)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.Clear([System.Drawing.Color]::FromArgb(11, 12, 19))

$bodyBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(29, 32, 45))
$graphics.FillEllipse($bodyBrush, 34, 34, 188, 188)

$greenPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(105, 232, 228), 30)
$amberPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(246, 107, 213), 30)
$redPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(255, 214, 107), 30)
foreach ($pen in @($greenPen, $amberPen, $redPen)) {
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
}
$graphics.DrawLine($greenPen, 96, 72, 96, 184)
$graphics.DrawLine($amberPen, 128, 104, 128, 184)
$graphics.DrawLine($redPen, 160, 145, 160, 184)

$icon = [System.Drawing.Icon]::FromHandle($bitmap.GetHicon())
$stream = [System.IO.File]::Open($outputPath, [System.IO.FileMode]::Create)
try {
    $icon.Save($stream)
} finally {
    $stream.Dispose()
    $icon.Dispose()
    $greenPen.Dispose()
    $amberPen.Dispose()
    $redPen.Dispose()
    $bodyBrush.Dispose()
    $graphics.Dispose()
    $bitmap.Dispose()
}

Write-Output "Created $outputPath"
