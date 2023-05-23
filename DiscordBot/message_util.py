import asyncio
import discord
import discord.ext.context
from discord.ext.context import ctx

async def next_message():
    # TODO: In the future we have to make sure author of report matches message id
    # this is how we seperate different people talking to the same bot
    def check(m: discord.Message):
        return True

    try:
        msg = await ctx.bot.wait_for('message', check=check, timeout= 60.0)

    except asyncio.TimeoutError:
        await ctx.channel.send("No message was sent going to cancel report")
        return None
    else:
        await ctx.channel.send("Recorded: " + msg.content)
        return msg