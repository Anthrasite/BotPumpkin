#!/bin/bash

# Stop BotPumpkin
screen -S BotPumpkin -X quit

# Update BotPumpkin
cd $HOME/BotPumpkin
git pull

# Run BotPumpkin
screen -d -m -S BotPumpkin python3.9 BotPumpkin.py