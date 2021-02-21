
from typing import Optional

import discord
from discord.ext import commands


class Config(commands.Cog):
    @commands.command(help='Change the prefix of the bot.')
    @commands.has_permissions(manage_guild=True)
    async def prefix(self, ctx: commands.Context, *, prefix: Optional[str]):
        if prefix:  # new prefix
            if len(prefix) > 32:
                await ctx.send(embed=discord.Embed(
                    description='Sorry, that prefix is too long. '
                                'It can not be longer than 32 characters.',
                    color=ctx.bot.colorsg['failure']
                ).set_footer(
                    text=f'Requested by {ctx.author}',
                    icon_url=ctx.author.avatar_url
                ))
            else:
                stor = ctx.bot.get_storage(ctx.guild)
                await stor.set('prefix', prefix)
                await ctx.send(embed=discord.Embed(
                    description=f'Prefix updated :ok_hand:\n'
                                f'It is now: {prefix}',
                    color=ctx.bot.colorsg['success']
                ).set_footer(
                    text=f'Requested by {ctx.author}',
                    icon_url=ctx.author.avatar_url
                ))
        else:
            prefix = (await ctx.bot.get_command_prefix(ctx.bot, ctx.message))
            await ctx.send(embed=discord.Embed(
                description=f'My current prefix is: {prefix[0]}',
                color=ctx.bot.colorsg['success']
            ).set_footer(
                text=f'Requested by {ctx.author}',
                icon_url=ctx.author.avatar_url
            ))


def setup(bot: commands.Bot):
    bot.add_cog(Config())
