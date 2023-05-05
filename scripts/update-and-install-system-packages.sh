#!/bin/bash

# A script for use in Docker containers to install debian packages with
# minimal cruft. Adapted from https://pythonspeed.com/articles/system-packages-docker/

set -euo pipefail
# Tell apt-get we're never going to be able to give manual 
# feedback:
export DEBIAN_FRONTEND=noninteractive

apt-get update
# Install security updates
apt-get -y upgrade
# Install packages
apt-get -y install --no-install-recommends $@
# Delete cached files we don't need anymore
apt-get clean
rm -rf /var/lib/apt/lists/*
