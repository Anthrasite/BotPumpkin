import sys
import os
import random
import time
import datetime
import logging
import json
import asyncio
import discord
import boto3
from discord.ext import commands
from dotenv import load_dotenv

# -------------------------------------------------
# Initialization
# -------------------------------------------------

# Load private keys into the environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(name)s:%(message)s",
    handlers = [
        logging.FileHandler(filename = "discord.log", encoding = "utf-8", mode = "w"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Setup the bot configuration reader/writer
class BotConfiguration:
	def __init__(self):
		with open("server.json", "r") as file:
			self.__config = json.load(file)

	def get(self, key):
		return self.__config[key]

	def set(self, key, value):
		self.__config[key] = value
		with open("server.json", "w") as file:
			json.dump(self.__config, file)
config = BotConfiguration()

# Initialize the bot
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix = config.get("Prefix"), case_insensitive = True, help_command = None, intents = intents)

# Print a status message once the bot is initialized
@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user}")


# -------------------------------------------------
# Help command
# -------------------------------------------------

@bot.command()
async def help(ctx, helpType):
	helpType = helpType.lower()
	if (helpType == "server"):
		await print_server_help(ctx)
	elif (helpType == "groovy"):
		await print_groovy_help(ctx)
	elif (helpType == "sesh"):
		await print_sesh_help(ctx)
	else:
		await print_general_help(ctx)

@help.error
async def help_error(ctx, error):
	if isinstance(error, commands.MissingRequiredArgument):
		await print_general_help(ctx)

async def print_server_help(ctx):
	image = discord.File(f"Icons/{config.get('CurrentGame')}.png", "icon.png")
	embed = discord.Embed(title = f"Connecting to the {config.get('CurrentGame')} Server:", description = config.get("CurrentGameHelp"), color = int(config.get("Color"), 0))
	embed.set_thumbnail(url = "attachment://icon.png")
	await ctx.send(file = image, embed = embed)

async def print_groovy_help(ctx):
	groovy = None
	for user in bot.users:
		if user.name == "Groovy":
			groovy = user
			break

	embed = discord.Embed(description = f"Groovy is a bot for playing music in the voice channels. See [here](https://groovy.bot/commands?prefix=-) for a full list of commands.", color = int(config.get("Color"), 0))
	embed.add_field(name = "`-play [search_query]`", value = "Adds the song to the queue, and starts playing it if nothing is playing", inline = False)
	embed.add_field(name = "`-play`", value = "Starts playing the queue", inline = False)
	embed.add_field(name = "`-pause`", value = "Pauses the current song (saves the position in the song)", inline = False)
	embed.add_field(name = "`-stop`", value = "Stops the current song (doesn't save the position in the song", inline = False)
	embed.add_field(name = "`-next`", value = "Skips to the next song", inline = False)
	embed.add_field(name = "`-back`", value = "Skips to the previous song", inline = False)
	embed.add_field(name = "`-queue`", value = "Displays the queue contents", inline = False)
	embed.add_field(name = "`-clear`", value = "Empties the queue", inline = False)
	embed.add_field(name = "`-jump [track_position]`", value = "Jumps to a specific point in the queue", inline = False)
	embed.add_field(name = "`-shuffle`", value = "Shuffles the queue", inline = False)
	embed.add_field(name = "`-move [track_position], [new_position]`", value = "Moves a song from one position to another in the queue", inline = False)
	embed.add_field(name = "`-saved queues`", value = "Displays your saved queues", inline = False)
	embed.add_field(name = "`-saved queues create [queue_name]`", value = "Creates the current queue as a new saved queue", inline = False)
	embed.add_field(name = "`-saved queues load [queue_name]`", value = "Loads all the songs from a saved queue into the current queue", inline = False)
	embed.add_field(name = "`-saved queues delete [queue_name]`", value = "Deletes a saved queue", inline = False)
	if groovy != None:
		embed.set_author(name = groovy.name, icon_url = groovy.avatar_url)
	else:
		embed.set_author(name = "Groovy")
	await ctx.send(embed = embed)

async def print_sesh_help(ctx):
	sesh = None
	for user in bot.users:
		if user.name == "sesh":
			sesh = user
			break

	embed = discord.Embed(description = f"sesh is a bot for planning hangouts and running polls. See [here](https://sesh.fyi/manual/) for a full list of commands.", color = int(config.get("Color"), 0))
	embed.add_field(name = "`!create [event_description] [time_description]`", value = "Creates a new event with the given event description at the given time", inline = False)
	embed.add_field(name = "`!poll [poll_name] [poll_options]`", value = "Creates a new poll with the given name and options", inline = False)
	embed.add_field(name = "`!list`", value = "Lists all future scheduled events", inline = False)
	embed.add_field(name = "`!delete`", value = "Allows you to select an event to delete", inline = False)
	embed.add_field(name = "`!delete [search_query]`", value = "Searches for an event with a matching name and confirms whether to delete it", inline = False)
	if sesh != None:
		embed.set_author(name = sesh.name, icon_url = sesh.avatar_url)
	else:
		embed.set_author(name = "sesh")
	await ctx.send(embed = embed)

async def print_general_help(ctx):
	embed = discord.Embed(description = "BotPumpkin is a custom bot for starting and stopping our game server, and for doing some other fun and useful things.", color = int(config.get("Color"), 0))
	embed.add_field(name = "`.slap`", value = "Let BotPumpkin teach someone else a lesson", inline = False)
	embed.add_field(name = "`.serverstart`", value = "Starts our game server", inline = False)
	embed.add_field(name = "`.serverstop`", value = "Stops our game server", inline = False)
	embed.add_field(name = "`.help server`", value = "Displays information about how to connect to the game server once it is running", inline = False)
	embed.add_field(name = "`.help Groovy`", value = "Displays commonly used commands for Groovy", inline = False)
	embed.add_field(name = "`.help sesh`", value = "Displays commonly used commands for sesh", inline = False)
	embed.set_author(name = bot.user.name, icon_url = bot.user.avatar_url)
	await ctx.send(embed = embed)

# -------------------------------------------------
# Slap command
# -------------------------------------------------

# Gets BotPumpkin to slap the specified user (usually)
@bot.command()
async def slap(ctx, *, member: discord.Member):
	if random.randint(1, 100) == 100:
		await send_simple_embed(ctx, f"{bot.user.mention} slapped {random.choice(ctx.guild.members).mention} instead!")
	await send_simple_embed(ctx, f"{bot.user.mention} slapped {member.mention}!")

# If the specified user cannot be found, slap the user who asked instead
@slap.error
async def slap_error(ctx, error):
	if isinstance(error, commands.BadArgument):
		await send_simple_embed(ctx, f"{bot.user.mention} didn\"t know who to slap, so {ctx.author.mention} was slapped instead!")
	elif isinstance(error, commands.MissingRequiredArgument):
		await send_simple_embed(ctx, f"{bot.user.mention} slapped {ctx.author.mention}!")


# -------------------------------------------------
# Server management commands
# -------------------------------------------------

# Holds the necessary configuration information for an AWS instance
class InstanceState:
	def __init__(self, instance):
		self.state = instance["State"]["Name"]
		self.imageId = instance["ImageId"]
		if "PublicIpAddress" in instance:
			self.publicIpAddress = instance["PublicIpAddress"]
		else:
			self.publicIpAddress = ""
		logging.info(f"Instance {self.imageId} is currently in state {self.state}")

# Performs necessary management of an AWS instance
class AWSInstanceManager:
	# Create the AWS connection
	def __init__(self):
		self.__client = boto3.client("ec2", aws_access_key_id = os.getenv("ACCESS_KEY"), aws_secret_access_key = os.getenv("SECRET_KEY"), region_name = os.getenv("EC2_REGION"))

	# Gets all instances on the AWS client
	def get_instance_list(self):
		response = self.__client.describe_instances(InstanceIds = [ os.getenv("INSTANCE_ID") ])
		return response["Reservations"][0]["Instances"]

	# Starts an instance and queries it until it"s running
	async def start_instance(self):
		self.__client.start_instances(InstanceIds = [ os.getenv("INSTANCE_ID") ])
		return await self.__query_instance("running")

	# Stops an instance and queries it until it has stopped
	async def stop_instance(self):
		self.__client.stop_instances(InstanceIds = [ os.getenv("INSTANCE_ID") ])
		return await self.__query_instance("stopped")

	# Queries the instance, sleeping for 3 seconds between each query, until the instance has the desired state
	async def __query_instance(self, desiredState):
		instanceState = None
		state = ""
		while not (state == desiredState):
			await asyncio.sleep(3)
			instanceState = InstanceState(self.get_instance_list()[0])
			state = instanceState.state
		return instanceState

instanceLock = asyncio.Lock()

# Starts the AWS instance
@bot.command(name = "startserver")
@commands.has_role(config.get('ServerStartRole'))
async def start_server(ctx):
	if instanceLock.locked():
		await send_simple_embed(ctx, f"Unable to run this command until the server has finished starting or stopping.")
		return

	async with instanceLock:
		# Ensure the instance exists
		instanceManager = AWSInstanceManager()
		instanceList = instanceManager.get_instance_list()
		if len(instanceList) == 0:
			await send_simple_embed(ctx, "Error occurred while starting the server (ERR:InstanceNotFound).")
			return

		# Start the instance if it's stopped, or send a message otherwise
		instanceState = InstanceState(instanceList[0])
		if instanceState.state == "running" or instanceState.state == "pending":
			await send_simple_embed(ctx, f"The server is already running. Connect to `{instanceState.publicIpAddress}:{config.get('ServerPort')}` to join the fun!")
		elif instanceState.state == "stopped" or instanceState.state == "stopping":
			progressMessage = await send_simple_embed(ctx, f"Starting the {config.get('CurrentGame')} server...")
			instanceState = await instanceManager.start_instance()
			await progressMessage.delete()
			await send_simple_embed(ctx, f"The {config.get('CurrentGame')} server is starting. Connect to `{instanceState.publicIpAddress}:{config.get('ServerPort')}` to join the fun!")
		else:
			await send_simple_embed(ctx, f"Error occurred while starting the {config.get('CurrentGame')} server (ERR:UnknownInstanceState:{instanceState.state}).")

		await bot.change_presence(activity = discord.Game(config.get('CurrentGame')))

# If the user calling the command doesn't have the "Server Manager" role, inform them they need it
@start_server.error
async def start_server_error(ctx, error):
	if isinstance(error, commands.MissingRole):
		await send_simple_embed(ctx, f"You must have the {config.get('ServerStartRole')} role to run this command.")

# Stops the AWS instance
@bot.command(name = "stopserver")
async def stop_server(ctx):
	if instanceLock.locked():
		await send_simple_embed(ctx, f"Unable to run this command until the server has finished starting or stopping.")
		return

	async with instanceLock:
		# Ensure the instance exists
		instanceManager = AWSInstanceManager()
		instanceList = instanceManager.get_instance_list()
		if len(instanceList) == 0:
			await send_simple_embed(ctx, "Error occurred while stopping the server (ERR:InstanceNotFound).")
			return

		# Stop the instance if it's running, or send a message otherwise
		instanceState = InstanceState(instanceList[0])
		if instanceState.state == "running" or instanceState.state == "pending":
			progressMessage = await send_simple_embed(ctx, f"Stopping the {config.get('CurrentGame')} server...")
			instanceState = await instanceManager.stop_instance()
			await progressMessage.delete()
			await send_simple_embed(ctx, f"The {config.get('CurrentGame')} server has been stopped. Thanks for playing!")
		elif instanceState.state == "stopped" or instanceState.state == "stopping":
			await send_simple_embed(ctx, f"The {config.get('CurrentGame')} server has already been stopped.")
		else:
			await send_simple_embed(ctx, f"Error occurred while stopping the {config.get('CurrentGame')} server (ERR:UnknownInstanceState:{state}).")

		await bot.change_presence(activity = None)


# -------------------------------------------------
# Utility functions & classes
# -------------------------------------------------

async def send_simple_embed(ctx,  message):
	return await ctx.send(embed = discord.Embed(description = message, color = int(config.get("Color"), 0)))


# -------------------------------------------------
# Start the bot
# -------------------------------------------------

bot.run(os.getenv("DISCORD_TOKEN"))