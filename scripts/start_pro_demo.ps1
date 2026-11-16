param(
    [int]$Port = 8080,
    [switch]$CleanupExisting,
    [switch]$NoAudio
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PcDir = Join-Path $RepoRoot "pc-agent-vision"
$OllamaExe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
$StartedOllamaProc = $null
$WebProc = $null

function Get-HotspotIpv4 {
    $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*" -and
            ($_.InterfaceAlias -match "WLAN|Wi-Fi|WiFi" -or $_.IPAddress -like "192.168.*")
        } |
        Select-Object -ExpandProperty IPAddress
    if ($ips) { return ($ips | Select-Object -First 1) }
    return "127.0.0.1"
}

function Test-OllamaReady {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
        return $resp
    } catch {
        return $null
    }
}

try {
    Write-Host "=== Kurisu Pro One-Click Demo Launcher ===" -ForegroundColor Cyan
    Write-Host "Repo: $RepoRoot"

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        throw "Python executable not found in PATH."
    }

    $localIp = Get-HotspotIpv4
    Write-Host "[1/5] Local LAN/Hotspot IP: $localIp"

    $portBusy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($portBusy) {
        $pids = $portBusy | Select-Object -ExpandProperty OwningProcess -Unique
        if ($CleanupExisting) {
            Write-Host "[2/5] Stopping existing listener PID(s) $($pids -join ', ') on port $Port..." -ForegroundColor Yellow
            foreach ($p in $pids) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
            Start-Sleep -Milliseconds 500
        } else {
            throw "Port $Port is already in use by PID(s) $($pids -join ', '). Re-run with -CleanupExisting to reclaim it."
        }
    } else {
        Write-Host "[2/5] Port $Port is free."
    }

    Write-Host "[3/5] Checking Ollama (127.0.0.1:11434)..."
    $tags = Test-OllamaReady
    if (-not $tags) {
        if (-not (Test-Path $OllamaExe)) {
            throw "Ollama service not running and executable not found at $OllamaExe"
        }
        $StartedOllamaProc = Start-Process -FilePath $OllamaExe -ArgumentList "serve" -WindowStyle Hidden -PassThru
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Milliseconds 500
            $tags = Test-OllamaReady
            if ($tags) { break }
        }
        if (-not $tags) {
            throw "Ollama failed to respond on 127.0.0.1:11434 within 15s."
        }
    }
    $modelNames = @($tags.models | ForEach-Object { $_.name })
    $targetModel = if ($env:KURISU_LLM_MODEL) { $env:KURISU_LLM_MODEL } else { "kurisu:latest" }
    if ($modelNames -notcontains $targetModel) {
        Write-Warning "Configured model '$targetModel' not found in Ollama tags ($($modelNames -join ', '))."
    } else {
        Write-Host "Ollama ready; model '$targetModel' available."
    }

    Write-Host "[4/5] Probing ESP32-S3 via LAN UDP / USB CDC..."
    $usbEsp = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
        Where-Object { $_.InstanceId -match "VID_303A&PID_1001" -or $_.FriendlyName -match "JTAG|ESP32" } |
        Select-Object -First 1
    if ($usbEsp) {
        Write-Host "Physical ESP32-S3 USB CDC detected ($($usbEsp.FriendlyName)); auto USB pairing enabled if token missing."
    } else {
        Write-Host "No ESP32-S3 USB CDC attached (pure Wi-Fi / independent power mode)."
    }

    $probeCode = @"
import json, socket, time
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.settimeout(1.2)
sock.sendto(b'{"cmd":"kurisu_discover"}', ('255.255.255.255', 8890))
try:
    data, addr = sock.recvfrom(1024)
    info = json.loads(data.decode('utf-8', 'ignore'))
    print(f"DISCOVERED: {addr[0]} board_sta_ip={info.get('board_sta_ip')} mode={info.get('mode')}")
except Exception as e:
    print(f"WARN_NO_UDP_BEACON: {e}")
finally:
    sock.close()
"@
    $probeCode | & $pythonCmd.Source -

    Write-Host "[5/5] Starting WebServer on http://$localIp`:$Port (Ctrl+C to stop cleanly)..." -ForegroundColor Green
    $webArgs = @((Join-Path $PcDir "web_server.py"), "--host", "0.0.0.0", "--port", "$Port")
    if ($NoAudio) { $webArgs += "--no-audio" }

    $WebProc = Start-Process -FilePath $pythonCmd.Source -ArgumentList $webArgs -WorkingDirectory $PcDir -NoNewWindow -PassThru
    $WebProc.WaitForExit()
}
finally {
    if ($WebProc -and -not $WebProc.HasExited) {
        Write-Host "`nStopping WebServer PID $($WebProc.Id)..." -ForegroundColor Yellow
        Stop-Process -Id $WebProc.Id -Force -ErrorAction SilentlyContinue
    }
    if ($StartedOllamaProc -and -not $StartedOllamaProc.HasExited) {
        Write-Host "Stopping script-started Ollama PID $($StartedOllamaProc.Id)..." -ForegroundColor Yellow
        Stop-Process -Id $StartedOllamaProc.Id -Force -ErrorAction SilentlyContinue
    }
}
