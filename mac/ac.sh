#!/bin/bash
# kapat.sh sonrasi tekrar acar. Kalici kurulum icin kur.sh kullan.
UID_NUM="$(id -u)"
LA="$HOME/Library/LaunchAgents"
for e in com.discord-engel-asici com.discord-engel-asici-dl com.discord-engel-asici-pac com.discord-engel-asici-bridge com.discord-engel-asici-env; do
  launchctl bootstrap "gui/$UID_NUM" "$LA/$e.plist" 2>/dev/null || true
done
sleep 2
networksetup -setautoproxyurl Wi-Fi "http://127.0.0.1:1099/proxy.pac"
networksetup -setautoproxystate Wi-Fi on
echo "ACILDI."
