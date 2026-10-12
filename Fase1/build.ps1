$ErrorActionPreference = 'Stop'

$sourceRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$frameworkCompiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $frameworkCompiler)) {
    $frameworkCompiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
}
if (-not (Test-Path -LiteralPath $frameworkCompiler)) {
    throw 'No se encontró el compilador de .NET Framework de Windows.'
}

$frameworkDirectory = Split-Path -Parent $frameworkCompiler
$distDirectory = Join-Path $sourceRoot 'dist'
$exePath = Join-Path $distDirectory 'AnalizadorFase1.exe'
$testExePath = Join-Path $distDirectory 'AnalizadorFase1.CoreTests.exe'
$guiTestExePath = Join-Path $distDirectory 'AnalizadorFase1.GuiSmokeTests.exe'
$packageDirectory = Join-Path $distDirectory 'Entrega_Fase1'
$zipPath = Join-Path $distDirectory 'Entrega_Fase1.zip'

New-Item -ItemType Directory -Force -Path $distDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $sourceRoot 'instrucciones_equipo.txt') -Destination $distDirectory -Force

$compilerArgs = @(
    '/nologo', '/target:winexe', '/optimize+',
    "/lib:$frameworkDirectory",
    "/reference:$(Join-Path $frameworkDirectory 'System.Windows.Forms.dll')",
    "/reference:$(Join-Path $frameworkDirectory 'System.Drawing.dll')",
    "/out:$exePath",
    (Join-Path $sourceRoot 'AnalysisCore.cs'),
    (Join-Path $sourceRoot 'AnalizadorFase1.cs')
)
& $frameworkCompiler @compilerArgs
if ($LASTEXITCODE -ne 0) { throw "La compilación de la aplicación falló: $LASTEXITCODE" }

$testArgs = @(
    '/nologo', '/target:exe', '/optimize+',
    "/out:$testExePath",
    (Join-Path $sourceRoot 'AnalysisCore.cs'),
    (Join-Path $sourceRoot 'tests\AnalysisCoreTests.cs')
)
& $frameworkCompiler @testArgs
if ($LASTEXITCODE -ne 0) { throw "La compilación de pruebas falló: $LASTEXITCODE" }
& $testExePath
if ($LASTEXITCODE -ne 0) { throw "Las pruebas fallaron: $LASTEXITCODE" }

$guiTestArgs = @(
    '/nologo', '/target:exe', '/optimize+', '/main:GuiSmokeTests',
    "/lib:$frameworkDirectory",
    "/reference:$(Join-Path $frameworkDirectory 'System.Windows.Forms.dll')",
    "/reference:$(Join-Path $frameworkDirectory 'System.Drawing.dll')",
    "/out:$guiTestExePath",
    (Join-Path $sourceRoot 'AnalysisCore.cs'),
    (Join-Path $sourceRoot 'AnalizadorFase1.cs'),
    (Join-Path $sourceRoot 'tests\GuiSmokeTests.cs')
)
& $frameworkCompiler @guiTestArgs
if ($LASTEXITCODE -ne 0) { throw "La compilación de la prueba de interfaz falló: $LASTEXITCODE" }
& $guiTestExePath
if ($LASTEXITCODE -ne 0) { throw "La prueba de interfaz falló: $LASTEXITCODE" }

$sourcePrefix = $sourceRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
$packageFullPath = [IO.Path]::GetFullPath($packageDirectory)
if (-not $packageFullPath.StartsWith($sourcePrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'La carpeta de empaquetado quedó fuera del proyecto.'
}
if (Test-Path -LiteralPath $packageDirectory) {
    Remove-Item -LiteralPath $packageDirectory -Recurse -Force
}
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

New-Item -ItemType Directory -Force -Path (Join-Path $packageDirectory 'tests') | Out-Null
Copy-Item -LiteralPath $exePath -Destination $packageDirectory
Copy-Item -LiteralPath (Join-Path $sourceRoot 'AnalysisCore.cs') -Destination $packageDirectory
Copy-Item -LiteralPath (Join-Path $sourceRoot 'AnalizadorFase1.cs') -Destination $packageDirectory
Copy-Item -LiteralPath (Join-Path $sourceRoot 'instrucciones_equipo.txt') -Destination $packageDirectory
Copy-Item -LiteralPath (Join-Path $sourceRoot 'README.md') -Destination $packageDirectory
Copy-Item -LiteralPath (Join-Path $sourceRoot 'build.ps1') -Destination $packageDirectory
Copy-Item -LiteralPath (Join-Path $sourceRoot 'tests\AnalysisCoreTests.cs') -Destination (Join-Path $packageDirectory 'tests')
Copy-Item -LiteralPath (Join-Path $sourceRoot 'tests\GuiSmokeTests.cs') -Destination (Join-Path $packageDirectory 'tests')
$packageRun = "@echo off`r`nstart `"`" `"%~dp0AnalizadorFase1.exe`"`r`n"
Set-Content -LiteralPath (Join-Path $packageDirectory 'run.bat') -Value $packageRun -Encoding ASCII
Compress-Archive -Path (Join-Path $packageDirectory '*') -DestinationPath $zipPath -CompressionLevel Optimal
$zipSize = (Get-Item -LiteralPath $zipPath).Length
$maxSize = 5MB
if ($zipSize -gt $maxSize) {
    throw ("El ZIP excede 5 MB: {0:N0} bytes." -f $zipSize)
}
Write-Output ("Ejecutable: {0}" -f $exePath)
Write-Output ("ZIP: {0} ({1:N0} bytes)" -f $zipPath, $zipSize)
