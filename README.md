# Discord Laptop dashboard

This Flask app is the private dashboard for the Debian laptop. It is **not** a GitHub Pages site: it must run on the laptop (or another trusted server with access to it). The public repository contains no password, token, or `.env` file.

## Install on Debian

```bash
sudo apt install python3-venv nginx
cd /opt/shardnote.net/discordlaptop
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env
```

Create a password hash (paste the output as `DASHBOARD_PASSWORD_HASH`):

```bash
.venv/bin/python -c "from werkzeug.security import generate_password_hash as h; print(h('choose-a-long-password'))"
```

Test it locally with `.venv/bin/gunicorn --bind 127.0.0.1:8123 app:app`.

## Allow only the required power actions

Use `sudo visudo -f /etc/sudoers.d/discord-laptop` and replace `YOUR_LINUX_USER`:

```sudoers
YOUR_LINUX_USER ALL=(root) NOPASSWD: /usr/bin/systemctl reboot, /usr/bin/systemctl poweroff
```

Do not grant blanket passwordless sudo.

## Publish it

Run Gunicorn through a systemd service and reverse-proxy it through Nginx on `discordlaptop.shardnote.net`. Enable HTTPS before setting `COOKIE_SECURE=true` (the default). If Cloudflare is used, point the DNS record to the reverse proxy or tunnel—not to GitHub Pages. GitHub stores the source; the Debian device serves the live authenticated controls.

