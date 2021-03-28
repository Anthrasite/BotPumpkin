.PHONY := help install install-dev install-pipenv install-python3.9 install-pip3.9 create-env run stop update
.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z0-9\._-]+:.*#.*' Makefile | sort | awk 'BEGIN {FS = ":.*# "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: # Installs dependencies for running the bot
	@$(MAKE) install-pipenv --no-print-directory
	pipenv install --ignore-pipfile
	@$(MAKE) create-env --no-print-directory

install-dev: # Installs dependencies for running the bot in a development environment
	@$(MAKE) install-pipenv --no-print-directory
	pipenv install --dev
	@$(MAKE) create-env --no-print-directory

install-pipenv:
	@$(MAKE) install-python3.9 --no-print-directory
	pip3.9 install pipenv

install-python3.9:
	@if python3.9 --version >/dev/null 2>&1 ; then \
		echo "python3.9 found. Skipping installation." ; \
	else \
		sudo apt update ; \
		sudo apt upgrade -y ; \
		sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev ; \
		cd /tmp ; \
		wget https://www.python.org/ftp/python/3.9.2/Python-3.9.2.tgz ; \
		tar xvf Python-3.9.2.tgz ; \
		cd Python-3.9.2 ; \
		./configure --enable-optimizations --with-ensurepip=install ; \
		make -j 8 ; \
		sudo make altinstall ; \
	fi

install-pip3.9:
	@if pip3.9 --version >/dev/null 2>&1 ; then \
		echo "pip3.9 found. Skipping installation." ; \
	else \
		python3.9 -m pip install --upgrade pip ; \
	fi

create-env:
	@if ! test -f ".env" ; then \
		printf "%s\n" "# .env" "DISCORD_TOKEN=" "ACCESS_KEY=" "SECRET_KEY=" "EC2_REGION=" "INSTANCE_ID=" > .env ; \
		echo ".env file not found. Template .env file created." ; \
	fi

run: # Runs the bot
	screen -d -m -S BotPumpkin pipenv run python3.9 botpumpkin/bot.py

stop: # Stops the bot
	screen -S BotPumpkin -X quit

update: # Stops the bot, updates it, and starts it again
	@$(MAKE) stop --no-print-directory
	git reset --hard
	git pull
	pipenv install --ignore-pipfile
	@$(MAKE) run --no-print-directory