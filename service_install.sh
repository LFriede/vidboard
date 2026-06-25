#!/usr/bin/env bash
mkdir -p ~/.config/systemd/user/
cp ./vidboard.service ~/.config/systemd/user/vidboard.service
systemctl --user daemon-reload
