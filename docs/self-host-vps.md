---
type: Guide
title: Self-host Hisab on a VPS
description: One copy-paste prompt for a coding agent that takes a server from nothing to a Hisab agent replying on WhatsApp, asking the human only for information and decisions.
tags: [self-host, vps, docker, guide]
timestamp: 2026-09-20T00:00:00Z
---

# Self-host Hisab on a VPS

[Run it for real](../README.md#run-it-for-real) runs Hisab on your own machine, which has to stay on. A small server keeps it running all the time. Everything below is one prompt: paste it into Claude Code, Codex, Cursor or any coding agent that can run commands. The agent does the work itself, and stops to ask you when it needs information or a decision. It asks before every `sudo` command, and it never asks you to paste a key into the chat.

What you need before you start:

- The API key of your WhatsApp agent (README, *Run it for real*, step 1) and one model key, OpenRouter or Gemini.
- A server, or an account with any VPS provider. Hisab needs no inbound port, domain or TLS certificate, because it long-polls WhatsApp and has no webhook. 1 vCPU, 1 GB RAM and 10 GB of disk is plenty. The RAM figure is an estimate, not a measured minimum. The image build compiles nothing: every Python dependency installs as a prebuilt wheel on x86_64 and arm64, and hledger comes from Debian's package. A strict check of the sample ledger peaks under 50 MB. Most of the 1 GB is headroom for the OS, the Docker daemon and `apt`.

```text
Set up Hisab (https://github.com/mhmzdev/hisab-whatsapp) on a Linux server so my WhatsApp agent replies from it. Work through the steps below in order. Do everything you can yourself, and stop to ask me only where a step says ASK or where you need information or a decision. Before every sudo command, show it to me and wait for my yes. If sudo needs a password you cannot type, give me the command to run myself and wait.

1. ASK which VPS provider I use, or whether I already have a server. If I have none, tell me what to create on the provider I name: a current Ubuntu LTS or Debian stable server, SSH key login (no password login), and the smallest plan with at least 1 vCPU, 1 GB RAM and 10 GB of disk. Do not recommend a provider. Wait until I say it exists.
2. ASK how to reach it: the IP address, the SSH user, and whether you are running on my machine (then run every server command over ssh <user>@<ip>) or on the server itself (then run them directly). Check that you can connect and run a command.
3. Check the OS and version (cat /etc/os-release) and the CPU architecture. Install git, then Docker Engine with the compose plugin from Docker's official apt repository, following https://docs.docker.com/engine/install/ for the distro you found. Enable Docker on boot: sudo systemctl enable --now docker. ASK whether to add my user to the docker group so docker runs without sudo. That group is root-equivalent, and I must log in again afterwards. If I say no, run docker with sudo and ask each time. Check docker compose version.
4. Clone the repo into ~/hisab-whatsapp and work only from there. Copy .env.example to .env and config.example.yaml to config.yaml. Do not ask me to paste a key into this chat. Tell me to open ~/hisab-whatsapp/.env on the server myself and fill in WHATSAPP_TOKEN (my WhatsApp agent's API key) and either OPENROUTER_API_KEY or GEMINI_API_KEY (one is enough; the config uses whichever is set), then run chmod 600 .env. Wait until I say it is done. Then check that the lines are filled without printing them, for example: grep -cE '^(WHATSAPP_TOKEN|OPENROUTER_API_KEY|GEMINI_API_KEY)=.+' .env counts the filled lines (2 or more is right).
5. ASK my timezone as an IANA name (for example Asia/Karachi) and my currency code (PKR unless I say otherwise). Set timezone: and ledger: currency: in config.yaml. Leave everything else at its default. The server clock is usually UTC and can stay UTC, because Hisab reads its dates only from timezone in config.yaml. Tell me to give the same currency code when setup asks for it in WhatsApp.
6. ASK whether Hisab, or anything else, already polls this WhatsApp agent: my laptop, another server, a terminal. If it does, I must stop it before you continue. Two pollers on one agent token fight over the cursor (HTTP 409) and take each other's messages. Wait until I confirm it is stopped.
7. Start it: docker compose up -d --build. Use docker compose directly, not make selfhost, which also starts a landing page this server does not need. Read docker compose logs --tail 50 until you see a line that starts "Polling WhatsApp.". If it says WHATSAPP_TOKEN is empty, or keeps logging "poll: ... exiting" and restarting, the WhatsApp key line needs fixing. If it logs "another poller is using this agent (HTTP 409)", another instance is still running. In either case tell me which one it is and wait.
8. Tell me to send my WhatsApp agent a message ("hi" is enough). Read the logs again and confirm an "in" line and an "out" line for that message. If the out line carries an error, tell me whether my model key line needs fixing. Then tell me that setup happens in WhatsApp: it asks, in English and Urdu, whether the ledger is personal or for a shop. The language I answer in becomes the language for the rest of setup.
9. Tell me that Hisab opens no port and needs no domain or TLS, because it long-polls WhatsApp and has no webhook. ASK whether to set a firewall that allows inbound SSH only. On yes: allow SSH first (sudo ufw allow OpenSSH, or the port sshd actually listens on), then sudo ufw enable, in that order so the SSH session is never cut. Then confirm a new SSH connection still works. If ufw is missing, ask before installing it. Mention that my provider may have its own firewall panel that can do the same.
10. Explain where my data lives. The ledger is plain text in ~/hisab-whatsapp/vault/ on the server (hisab.md, accounts.md, rules.md, the quarter files, settings.json). The message store (offset, message map, setup state) lives in the hisab-data Docker volume. To get the ledger out, I can send export-ledger to my agent and the folder comes back as a ZIP, or copy or sync vault/ with a tool of my choosing. ASK which I want, if any, and set up only what I pick.
11. Leave me the update commands, which keep .env, config.yaml, vault/ and the store:
    cd ~/hisab-whatsapp && git pull && docker compose up -d --build
    docker compose logs -f
    Tell me the container restarts on its own after a crash or a reboot (restart: unless-stopped, Docker enabled on boot). docker compose down stops it and keeps everything.

Rules for the whole run: never print, cat, commit or send the contents of .env, and never ask me for a key in chat. Never run docker compose down -v: it deletes the message store (the poll offset, the message-to-entry map, the setup state), so reply-to-undo on older messages stops working and a setup in progress starts over. Apart from installing git, Docker and the firewall, change nothing on the server outside ~/hisab-whatsapp.
```

Once it replies on WhatsApp, the rest is the README: [what you can send](../README.md#what-you-can-send), and [viewing](../README.md#viewing) the ledger in Obsidian or with `hledger`.
