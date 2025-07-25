#!/bin/bash

set -e
set -E
set -x

is_ubuntu="$(cat /etc/os-release | grep -i ubuntu)"
if [[ $is_ubuntu ]]; then
  sudo apt install python3.11 python3.11-venv python3.11-distutils
  if [[ ! -d .venv ]]; then
    python3.11 -m venv .venv
  fi
  source ./.venv/bin/activate
  if ! ls -ld /usr/bin/google-chrome; then
    wget "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
    sudo apt install -y "./google-chrome-stable_current_amd64.deb"
    rm -rf "./google-chrome-stable_current_amd64.deb"
  fi
  if ! dpkg -s python3-distutils &> /dev/null; then
    sudo apt install -y python3-distutils
  fi
else
  if ! ls -ld /usr/bin/google-chrome; then
    sudo dnf install google-chrome-stable.x86_64
  fi
  if ! rpm -q python3-distutils-extra &> /dev/null; then
    sudo dnf install python3-devel
  fi
fi

pip install -r requirements.txt
if [[ ! -f "config.yml" ]]; then
  cp config_model.yml config.yml
fi

exit 0

