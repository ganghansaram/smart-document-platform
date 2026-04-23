New-NetFirewallRule -DisplayName "SDP Web (Port 80)" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow -Profile Private -Description "Smart Document Platform"
Write-Host "Done! Press any key to close..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
