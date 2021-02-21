
import datetime

import discord
from discord.ext import commands

from ..bot import EXTENSIONS


class Developer(commands.Cog):
    @commands.command(help='Load an extension by it\'s module path.')
    @commands.is_owner()
    async def dev_load(self, ctx: commands.Context, name: str):
        ctx.bot.load_extension(name)
        EXTENSIONS.append(name)
        await ctx.send(embed=discord.Embed(
            description=f':ok_hand: Loaded `{name}`',
            color=ctx.bot.colorsg['success']
        ).set_footer(
                text=f'Requested by {ctx.author}',
                icon_url=ctx.author.avatar_url
            ))

    @commands.command(help='Unload an extension by it\'s module path.')
    @commands.is_owner()
    async def dev_unload(self, ctx: commands.Context, name: str):
        ctx.bot.unload_extension(name)
        await ctx.send(embed=discord.Embed(
            description=f':ok_hand: Unloaded `{name}`',
            color=ctx.bot.colorsg['success']
        ).set_footer(
                text=f'Requested by {ctx.author}',
                icon_url=ctx.author.avatar_url
            ))

    @commands.command(help='Reload all extension or one specified by it\'s '
                           'module path.')
    @commands.is_owner()
    async def dev_reload(self, ctx: commands.Context, name: str = None):
        if name is None:
            exts = EXTENSIONS
        else:
            exts = [name]
        for extension in exts:
            ctx.bot.reload_extension(extension)
        await ctx.send(embed=discord.Embed(
            description=f':ok_hand: Reloaded {len(exts)} '
                        f'extension(s).',
            color=ctx.bot.colorsg['success']
        ).set_footer(
                text=f'Requested by {ctx.author}',
                icon_url=ctx.author.avatar_url
            ))

    @commands.command(help='Ping')
    @commands.is_owner()
    async def dev_ping(self, ctx: commands.Context):
        sent = datetime.datetime.utcnow()
        ws_latency = ctx.bot.latency * 1000

        msg = await ctx.send(embed=discord.Embed(
            description=f'Websocket latency: **{ws_latency:.2f}ms**\n'
                        f'API latency: *fetching*',
            color=ctx.bot.colorsg['success']
        ))
        api_latency = (msg.created_at - sent).total_seconds() * 1000
        await msg.edit(embed=discord.Embed(
            description=(
                f'Websocket latency: **{ws_latency:.2f}ms**\n'
                f'API latency: **{api_latency:.2f}ms**'
            ),
            color=ctx.bot.colorsg['success']
        ))


def setup(bot: commands.Bot):
    bot.add_cog(Developer())
