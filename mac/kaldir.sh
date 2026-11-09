#!/bin/bash
# Tamamen kaldirir: hizmetler, plistler, Otomasyon symlinkleri, PAC ayari. Calisma klasoru (log, yedek) kalir.
UID_NUM="$(id -u)"
LA="$HOME/Library/LaunchAgents"
OTO="$HOME/Library/Application Support/Otomasyon"
networksetup -setautoproxystate Wi-Fi off
for e in com.discord-engel-asici com.discord-engel-asici-dl com.discord-engel-asici-pac com.discord-engel-asici-bridge com.discord-engel-asici-env; do
  launchctl bootout "gui/$UID_NUM/$e" 2>/dev/null || true
  rm -f "$LA/$e.plist"
done
launchctl unsetenv HTTPS_PROXY
rm -f "$OTO"/Discord\ Engel\ Aşıcı\ *\(Kapatma\)
echo "KALDIRILDI. Internet normale dondu."
