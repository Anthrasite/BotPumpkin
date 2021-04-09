# BotPumpkin
A simple Discord bot which includes commands for starting and stopping an AWS instance for hosting a game server.

The commands supported by this bot include:
* `slap <user>`: Prints a simple `@BotPumpkin slapped <user>` message, with a small chance to slap someone else instead.
* `server start <game>`: Starts the specified game server on a configured AWS instance.
* `server stop`: Stops the game server running on a configured AWS instance, and then stops the instance itself.
* `server change <game>`: Stops the game server running on a configured AWS instance and starts a different one.
* `server status`: Returns status information about the AWS instance and the game running on it. Will return more detailed technical information for admins.
* `server disable`: Disables all server commands temporarily to allow for maintenance of the AWS instance (admin only).
* `server enable`: Enables server commands after they were temporarily disabled (admin only).
* `help Groovy`: Displays commonly used commands for the Groovy bot.
* `help sesh`: Displays commonly used commands for the sesh bot.

## Setup
To setup BotPumpkin, first run `make install` (or `make install-dev` for a development environment). This will install the required dependencies and will create a .env file in the root directory. This file should be configured with the following values:
```
# .env
DISCORD_TOKEN=<the token for the Discord bot>

ACCESS_KEY=<an AWS access key>
SECRET_KEY=<the secret access key for the AWS access key>
EC2_REGION=<the region where the AWS instance you wish to start/stop is being hosted>
INSTANCE_ID=<the id of the AWS instance you wish to start/stop>
```

All other configuration is done using the config.json file found in the botpumpkin directory, which contains a set of initial configuration values by default.
