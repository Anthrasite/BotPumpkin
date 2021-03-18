PYTHON = python3.9
PIP = pip3.9

.PHONY = help setup run update install_python3.9

help:
	@echo "The following make commands are supported:"
	@echo "  - setup: Setup the bot"
	@echo "  - run: Start the bot"
	@echo "  - update: Stop the bot, update it, and start the bot"
	@echo "  - install_python3.9: Installs Python3.9, which is required to run the bot"

setup:
	$(PIP) install -r requirements.txt
	@if ! test -f ".env"; then \
		printf "%s\n" "# .env" "DISCORD_TOKEN=" "ACCESS_KEY=" "SECRET_KEY=" "EC2_REGION=" "INSTANCE_ID=" > .env; \
	fi

run:
	screen -d -m -S BotPumpkin $(PYTHON) botpumpkin/bot.py

update:
	@if screen -list | grep -q "BotPumpkin"; then \
		screen -S BotPumpkin -X quit; \
	fi

	@if git pull; then \
		$(PIP) install -r requirements.txt
		screen -d -m -S BotPumpkin $(PYTHON) botpumpkin/bot.py; \
	else \
		@echo "Update failed: Unable to update repository"; \
	fi

install_python3.9:
	sudo apt update
	sudo apt upgrade -y
	sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev
	cd /tmp
	wget https://www.python.org/ftp/python/3.9.2/Python-3.9.2.tgz
	tar xvf Python-3.9.2.tgz
	cd Python-3.9.2
	./configure --enable-optimizations --with-ensurepip=install
	make -j 8
	sudo make altinstall
	python3.9 -m pip install --upgrade pip