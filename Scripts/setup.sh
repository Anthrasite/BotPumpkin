#!/bin/bash

# Update and install packages
sudo apt update
sudo apt upgrade -y
sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev

# Install Python 3.9
cd $HOME
mkdir tmp
cd tmp
wget https://www.python.org/ftp/python/3.9.2/Python-3.9.2.tgz
tar xvf Python-3.9.2.tgz
cd Python-3.9.2
./configure --enable-optimizations --with-ensurepip=install
make -j 8
sudo make altinstall
python3.9 -m pip install --upgrade pip

# Install BotPumpkin
cd ../..
git clone https://github.com/Anthrasite/BotPumpkin.git
cd BotPumpkin
pip3.9 install -r requirements.txt

# Copy/create the .env file to configure the bot
echo Create a .env file in the BotPumpkin directory as detailed in README.md