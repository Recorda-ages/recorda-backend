#!/bin/bash
# Cole este script em "Advanced details > User data" ao criar a EC2
# (Ubuntu Server 24.04 LTS, arquitetura 64-bit Arm).
# Cria swap de 2 GB, instala Docker + Compose e clona o repositório em /opt/recorda-backend.
set -euxo pipefail

# Swap de 2 GB (proteção contra falta de memória)
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

apt-get update
apt-get install -y docker.io docker-compose-v2 git
systemctl enable --now docker

git clone -b dev https://github.com/Recorda-ages/recorda-backend /opt/recorda-backend
cp /opt/recorda-backend/deploy/.env.prod.example /opt/recorda-backend/deploy/.env.prod
chmod 600 /opt/recorda-backend/deploy/.env.prod
