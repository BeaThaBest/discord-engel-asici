#!/bin/bash
# Gecici kapatir: PAC kapanir, hizmetler durur, internet normale doner. Geri acmak: ac.sh
UID_NUM="$(id -u)"
networksetup -setautoproxystate Wi-Fi off
for e in com.discord-engel-asici com.discord-engel-asici-dl com.discord-engel-asici-pac com.discord-engel-asici-bridge; do
  launchctl bootout "gui/$UID_NUM/$e" 2>/dev/null || true
done
launchctl unsetenv HTTPS_PROXY
echo "KAPATILDI. Geri acmak icin mac/ac.sh"
