# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'token.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    token = json.load(f)['discord']

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='.', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_member_join(member):
    if member.bot:
        m = re.search("Group (\d+) Bot", member.name)
        if not m:
            return
        group_role = discord.utils.get(member.guild.roles, name="Group " + str(m.group(1)))
        if not group_role:
            return
        await member.add_roles(group_role)


# todo: require staff role
@bot.command(name='roles', help='Create x group roles.')
@commands.has_any_role('@staff')
async def create_roles(ctx, num):
    guild = ctx.guild
    for i in range(1, int(num) + 1):
        await guild.create_role(name="Group " + str(i))
    await ctx.send(f'Created roles for groups 1-{num}.')

@bot.command(name='channels', help='Create group and group-mod channels in the specified category.')
@commands.has_any_role('@staff')
async def create_channels(ctx, cat):
    guild = ctx.guild
    for c in guild.categories:
        if c.name == cat:
            category = c
    
    m = re.search("Group Channels (\d+)-(\d+)", cat)
    for i in range(int(m.group(1)), int(m.group(2)) + 1):
        group_role = discord.utils.get(guild.roles, name="Group "+str(i))
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True),
            group_role: discord.PermissionOverwrite(read_messages=True)
        }
        await guild.create_text_channel(f'group-{i}', category=category, overwrites=overwrites)
        await guild.create_text_channel(f'group-{i}-mod', category=category, overwrites=overwrites)
    
    await ctx.send(f'Created channels for groups {m.group(1)}-{m.group(2)}.')

@bot.command(name='clear', help='Clear all messages sent in this channel.')
async def clear(ctx):
    check_func = lambda msg: not msg.pinned
    await ctx.message.delete()
    await ctx.channel.purge(limit=100, check=check_func)
    await ctx.send(f'{num} messages deleted.', delete_after=5)

@bot.command(name='join', help='Get the role for group x. Usage: .join #')
async def join_group(ctx, num):
    for guild in bot.guilds:
        if not "CS 152" in guild.name:
            continue
        if guild.get_member(ctx.author.id):
            member = guild.get_member(ctx.author.id)
            group_role = discord.utils.get(guild.roles, name="Group " + num)
            if group_role:
                await member.add_roles(group_role)
                await ctx.send("You have been given the Group " + num + " role in the CS 152 Discord server.")
            else:
                await ctx.send("I'm sorry, that group role doesn't exist.")

@bot.command(name='leave', help='Remove the role for group x. Usage: .leave #')
async def leave_group(ctx, num):
    for guild in bot.guilds:
        if not "CS 152" in guild.name:
            continue
        if guild.get_member(ctx.author.id):
            member = guild.get_member(ctx.author.id)
            group_role = discord.utils.get(guild.roles, name="Group " + num)
            if group_role:
                await member.remove_roles(group_role)
                await ctx.send("The Group " + num + " role has been removed.")
            else:
                await ctx.send("I'm sorry, that group role doesn't exist.")

@bot.command(name='ping', help='pong')
async def ping_pong(ctx):
    await ctx.send("pong")

bot.run(token)
