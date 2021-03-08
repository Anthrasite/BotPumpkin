# BotPumpkin
A simple Discord bot which includes commands for starting and stopping an AWS instance for hosting a game server.

The commands supported by this bot include:
* `slap <user>`: Prints a simple _"@BotPumpkin slapped <user>"_ message, with a small chance to slap someone else instead.
* `serverstart`: Starts an AWS instance.
* `serverstop`: Stops an AWS instance.
* `help server`: Displays information about how to connect to the game server on the AWS instance once it is running.
* `help Groovy`: Displays commonly used commands for the Groovy bot.
* `help sesh`: Displays commonly used commands for the sesh bot.

## Setup
To configure BotPumpkin, create a .env file in the root directory of the project as follows:
```
# .env
DISCORD_TOKEN=<the token for the Discord bot>

ACCESS_KEY=<an AWS access key>
SECRET_KEY=<the secret access key for the AWS access key>
EC2_REGION=<the region where the AWS instance you wish to start/stop is being hosted>
INSTANCE_ID=<the id of the AWS instance you wish to start/stop>
```