function FindProxyForURL(url, host) {
    if (shExpMatch(host, "*.dl2-*.discordapp.net")) return "SOCKS5 127.0.0.1:1091; SOCKS 127.0.0.1:1091";
    if (host === "updates.discord.com") return "DIRECT";
    if (host === "dl2.discordapp.net" || dnsDomainIs(host, ".dl2.discordapp.net")) return "SOCKS5 127.0.0.1:1091; SOCKS 127.0.0.1:1091";
    if (host === "discordstatus.com" || dnsDomainIs(host, ".discordstatus.com")) return "SOCKS5 127.0.0.1:1080; SOCKS 127.0.0.1:1080";
    if (host === "dl.discordapp.net" || dnsDomainIs(host, ".dl.discordapp.net")) return "SOCKS5 127.0.0.1:1091; SOCKS 127.0.0.1:1091";
    if (host === "discordapp.com" || dnsDomainIs(host, ".discordapp.com")) return "SOCKS5 127.0.0.1:1080; SOCKS 127.0.0.1:1080";
    if (host === "discordapp.net" || dnsDomainIs(host, ".discordapp.net")) return "SOCKS5 127.0.0.1:1080; SOCKS 127.0.0.1:1080";
    if (host === "discord.media" || dnsDomainIs(host, ".discord.media")) return "SOCKS5 127.0.0.1:1080; SOCKS 127.0.0.1:1080";
    if (host === "discord.com" || dnsDomainIs(host, ".discord.com")) return "SOCKS5 127.0.0.1:1080; SOCKS 127.0.0.1:1080";
    if (host === "discord.app" || dnsDomainIs(host, ".discord.app")) return "SOCKS5 127.0.0.1:1080; SOCKS 127.0.0.1:1080";
    if (host === "discord.gg" || dnsDomainIs(host, ".discord.gg")) return "SOCKS5 127.0.0.1:1080; SOCKS 127.0.0.1:1080";
    return "DIRECT";
}
