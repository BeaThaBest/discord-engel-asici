# Discord Engel Aşıcı

Global anayasa geçerlidir. Bu repo, Discord engelini yalnız Discord alan adları için ByeDPI ile aşan sistemin tek kaynağıdır: `ortak/` (alan listesi, PAC üretici, HTTP CONNECT köprüsü, platformdan bağımsız), `motor/` (sabit ByeDPI sürümü ve derleme), `mac/` (LaunchAgent kurulumu), `windows/` (Görev Zamanlayıcı kurulumu, `ortak/hizmet.py` tek süreç). Çalışma kopyası `~/Library/Application Support/DiscordEngelAsici/` altındadır, repo değil.

## Kabul komutları

* `python3 -m unittest discover -s tests`
* `motor/derle-mac.sh`
* `mac/kur.sh`
* `launchctl list | grep discord-engel-asici`
* `curl -s -o /dev/null -w '%{http_code}\n' -x socks5h://127.0.0.1:1080 https://discord.com/api/v9/gateway`
* `bash motor/derle-windows.sh` ve `file motor/bin/ciadpi.exe` (PE32+ x86-64)
* Windows (PC'de): `powershell -NoProfile -ExecutionPolicy Bypass -File windows\kur.ps1`, sonra `schtasks /query /tn DiscordEngelAsici /v /fo list` ve `curl.exe -s -o NUL -w "%{http_code}" -x socks5h://127.0.0.1:1080 https://discord.com/api/v9/gateway` (200)
