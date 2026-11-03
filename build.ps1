[CmdletBinding()]
param(
    [switch]$SoloEmpaquetar
)

$ErrorActionPreference = 'Stop'
$sourceRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$distDirectory = Join-Path $sourceRoot 'dist'
$exePath = Join-Path $distDirectory 'AnalizadorFase1.exe'
$zipPath = Join-Path $distDirectory 'Entrega_Fase1.zip'
$temporaryRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$temporaryPrefix = $temporaryRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
$workDirectory = [IO.Path]::GetFullPath((Join-Path $temporaryRoot ('AnalizadorFase1-' + [Guid]::NewGuid().ToString('N'))))
if (-not $workDirectory.StartsWith($temporaryPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'La carpeta temporal quedó fuera de la ubicación prevista.'
}
$packageDirectory = Join-Path $workDirectory 'Entrega_Fase1'
$temporaryZip = Join-Path $workDirectory 'Entrega_Fase1.zip'
$candidateExe = Join-Path $workDirectory 'AnalizadorFase1.exe'

try {
    New-Item -ItemType Directory -Path $workDirectory | Out-Null
    New-Item -ItemType Directory -Force -Path $distDirectory | Out-Null

    if (-not $SoloEmpaquetar) {
        $frameworkCompiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
        if (-not (Test-Path -LiteralPath $frameworkCompiler)) {
            $frameworkCompiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
        }
        if (-not (Test-Path -LiteralPath $frameworkCompiler)) {
            throw 'No se encontró el compilador de .NET Framework de Windows.'
        }
        $frameworkDirectory = Split-Path -Parent $frameworkCompiler
        $compilerArgs = @(
            '/nologo', '/target:winexe', '/optimize+',
            "/lib:$frameworkDirectory",
            "/reference:$(Join-Path $frameworkDirectory 'System.Windows.Forms.dll')",
            "/reference:$(Join-Path $frameworkDirectory 'System.Drawing.dll')",
            "/out:$candidateExe",
            (Join-Path $sourceRoot 'AnalysisCore.cs'),
            (Join-Path $sourceRoot 'AnalizadorFase1.cs')
        )
        & $frameworkCompiler @compilerArgs
        if ($LASTEXITCODE -ne 0) { throw "La compilación de la aplicación falló: $LASTEXITCODE" }

        $testExePath = Join-Path $workDirectory 'AnalizadorFase1.CoreTests.exe'
        $testArgs = @(
            '/nologo', '/target:exe', '/optimize+',
            "/out:$testExePath",
            (Join-Path $sourceRoot 'AnalysisCore.cs'),
            (Join-Path $sourceRoot 'verificacion\tests\AnalysisCoreTests.cs')
        )
        & $frameworkCompiler @testArgs
        if ($LASTEXITCODE -ne 0) { throw "La compilación de pruebas falló: $LASTEXITCODE" }
        & $testExePath (Join-Path $sourceRoot 'verificacion\tests\Plantilla.ens') (Join-Path $sourceRoot 'verificacion\ejemplos')
        if ($LASTEXITCODE -ne 0) { throw "Las pruebas fallaron: $LASTEXITCODE" }

        $guiTestExePath = Join-Path $workDirectory 'AnalizadorFase1.GuiSmokeTests.exe'
        Copy-Item -LiteralPath (Join-Path $sourceRoot 'instrucciones_equipo.txt') -Destination $workDirectory
        $guiTestArgs = @(
            '/nologo', '/target:exe', '/optimize+', '/main:GuiSmokeTests',
            "/lib:$frameworkDirectory",
            "/reference:$(Join-Path $frameworkDirectory 'System.Windows.Forms.dll')",
            "/reference:$(Join-Path $frameworkDirectory 'System.Drawing.dll')",
            "/out:$guiTestExePath",
            (Join-Path $sourceRoot 'AnalysisCore.cs'),
            (Join-Path $sourceRoot 'AnalizadorFase1.cs'),
            (Join-Path $sourceRoot 'verificacion\tests\GuiSmokeTests.cs')
        )
        & $frameworkCompiler @guiTestArgs
        if ($LASTEXITCODE -ne 0) { throw "La compilación de la prueba de interfaz falló: $LASTEXITCODE" }
        & $guiTestExePath
        if ($LASTEXITCODE -ne 0) { throw "La prueba de interfaz falló: $LASTEXITCODE" }
    }
    elseif (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
        throw 'No existe dist/AnalizadorFase1.exe. Ejecuta build.ps1 sin -SoloEmpaquetar para compilarlo.'
    }
    else {
        Copy-Item -LiteralPath $exePath -Destination $candidateExe
    }

    New-Item -ItemType Directory -Path $packageDirectory | Out-Null
    Copy-Item -LiteralPath $candidateExe -Destination $packageDirectory
    foreach ($name in @('AnalysisCore.cs', 'AnalizadorFase1.cs', 'instrucciones_equipo.txt')) {
        Copy-Item -LiteralPath (Join-Path $sourceRoot $name) -Destination $packageDirectory
    }
    Compress-Archive -Path (Join-Path $packageDirectory '*') -DestinationPath $temporaryZip -CompressionLevel Optimal
    $zipSize = (Get-Item -LiteralPath $temporaryZip).Length
    if ($zipSize -gt 5MB) {
        throw ("El ZIP excede 5 MB: {0:N0} bytes." -f $zipSize)
    }
    Copy-Item -LiteralPath (Join-Path $sourceRoot 'instrucciones_equipo.txt') -Destination $distDirectory -Force
    Copy-Item -LiteralPath $candidateExe -Destination $exePath -Force
    Copy-Item -LiteralPath $temporaryZip -Destination $zipPath -Force
    Write-Output ("Ejecutable: {0}" -f $exePath)
    Write-Output ("ZIP: {0} ({1:N0} bytes)" -f $zipPath, $zipSize)
}
finally {
    $resolvedWork = [IO.Path]::GetFullPath($workDirectory)
    if (-not $resolvedWork.StartsWith($temporaryPrefix, [StringComparison]::OrdinalIgnoreCase) -or
        -not ([IO.Path]::GetFileName($resolvedWork)).StartsWith('AnalizadorFase1-', [StringComparison]::Ordinal)) {
        throw 'Se rechazó eliminar una carpeta temporal fuera del destino previsto.'
    }
    if (Test-Path -LiteralPath $resolvedWork) {
        Remove-Item -LiteralPath $resolvedWork -Recurse -Force
    }
}
