import asyncio
import discord
import discord.ext.context
from discord.ext.context import ctx

async def next_message(timeout=60, channel = "", retries=3):
    # TODO: In the future we have to make sure author of report matches message id
    # this is how we seperate different people talking to the same bot
    def check(m: discord.Message):
        if channel != "":
            return m.channel.name == channel and m.author.name != "Group 2 Bot"
            # return True
        else:
            return True
    
    # if channel == "":
    try:
        msg = await ctx.bot.wait_for('message', check=check, timeout= 60.0)

    except asyncio.TimeoutError:
        await ctx.channel.send("No message was sent going to cancel report")
        return None
    else:
        await ctx.channel.send("Recorded: " + msg.content)
        return msg
        
    # elif channel == "mod":
    #     try:
    #         msg = await ctx.bot.wait_for('message', check=check, timeout= 60.0)
    #         # print(msg)
    #         # print(msg.channel)
    #         if msg.channel.name != "group-2-mod":
    #             if (retries >= 0):
    #                 next_message(channel="mod", retries = retries - 1)
    #             else:
    #                 raise(Exception("Mismatched mod group"))

    #     except asyncio.TimeoutError:
    #         await ctx.channel.send("No message was sent going to cancel report")
    #         return None
    #     except Exception as e:
    #         print(f"Error occurred: {e}")
    #     else:
    #         await ctx.channel.send("Recorded: " + msg.content)
    #         return msg