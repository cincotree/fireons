#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"
INITIAL_USER="${INITIAL_USER:-ubuntu}"
NEW_USER="${NEW_USER:-deploy}"
TIMEZONE="${TIMEZONE:-UTC}"

echo "==> Linode Server Hardening Script"
echo "    Server: $SERVER_IP"
echo "    New user: $NEW_USER"
echo ""

read -p "This will harden the server and disable root SSH access. Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

LOCAL_PUB_KEY=$(cat "${SSH_KEY}.pub" 2>/dev/null || cat "$HOME/.ssh/id_ed25519.pub" 2>/dev/null || cat "$HOME/.ssh/id_rsa.pub" 2>/dev/null)
if [ -z "$LOCAL_PUB_KEY" ]; then
    echo "Error: No SSH public key found. Please ensure ${SSH_KEY}.pub exists."
    exit 1
fi

echo "==> Connecting to server and applying hardening..."

ssh -i "$SSH_KEY" "$INITIAL_USER@$SERVER_IP" "sudo bash -s" << REMOTE_SCRIPT
set -euo pipefail

echo "==> Updating system packages..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

echo "==> Setting timezone to $TIMEZONE..."
timedatectl set-timezone '$TIMEZONE'

echo "==> Setting hostname to $SERVER_HOSTNAME..."
hostnamectl set-hostname '$SERVER_HOSTNAME'

echo "==> Creating limited user account: $NEW_USER..."
if id "$NEW_USER" &>/dev/null; then
    echo "    User $NEW_USER already exists, skipping creation"
else
    adduser --disabled-password --gecos "" '$NEW_USER'
    usermod -aG sudo '$NEW_USER'
    echo '$NEW_USER ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/$NEW_USER
    chmod 440 /etc/sudoers.d/$NEW_USER
fi

echo "==> Creating application directory..."
mkdir -p /opt/fireons
chown -R $NEW_USER:$NEW_USER /opt/fireons

echo "==> Setting up SSH key for $NEW_USER..."
mkdir -p /home/$NEW_USER/.ssh
echo '$LOCAL_PUB_KEY' > /home/$NEW_USER/.ssh/authorized_keys
chmod 700 /home/$NEW_USER/.ssh
chmod 600 /home/$NEW_USER/.ssh/authorized_keys
chown -R $NEW_USER:$NEW_USER /home/$NEW_USER/.ssh

echo "==> Installing and configuring UFW firewall..."
apt-get install -y ufw

ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

echo "y" | ufw enable
ufw status

echo "==> Installing and configuring Fail2Ban..."
apt-get install -y fail2ban

cat > /etc/fail2ban/jail.local << 'FAIL2BAN_CONF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
backend = systemd

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 24h
FAIL2BAN_CONF

systemctl enable fail2ban
systemctl restart fail2ban

echo "==> Hardening SSH configuration..."
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#*ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*UsePAM.*/UsePAM yes/' /etc/ssh/sshd_config

if ! grep -q "^PermitRootLogin" /etc/ssh/sshd_config; then
    echo "PermitRootLogin no" >> /etc/ssh/sshd_config
fi
if ! grep -q "^PasswordAuthentication" /etc/ssh/sshd_config; then
    echo "PasswordAuthentication no" >> /etc/ssh/sshd_config
fi

sshd -t && echo "SSH config syntax OK"

systemctl restart ssh

echo "==> Installing automatic security updates..."
apt-get install -y unattended-upgrades
dpkg-reconfigure -f noninteractive unattended-upgrades

echo "==> Hardening complete!"
REMOTE_SCRIPT

echo ""
echo "==> Server hardening complete!"
echo ""
echo "IMPORTANT: Test SSH access with the new user before closing this terminal:"
echo "    ssh -i $SSH_KEY $NEW_USER@$SERVER_IP"
echo ""
echo "If successful, update deploy scripts to use '$NEW_USER' instead of 'root'."
echo ""
echo "Security measures applied:"
echo "  - System packages updated"
echo "  - Limited user '$NEW_USER' created with sudo access"
echo "  - SSH: Root login disabled, password auth disabled"
echo "  - UFW firewall: Only ports 22, 80, 443 open"
echo "  - Fail2Ban: Bans IPs after 3 failed SSH attempts for 24h"
echo "  - Automatic security updates enabled"
