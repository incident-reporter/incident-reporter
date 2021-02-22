
import datetime
from typing import Optional

import discord
from discord.ext import commands

from ..storage import Storage
from ..util import is_staff


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
                color=ctx.bot.colorsg['info']
            ).set_footer(
                text=f'Requested by {ctx.author}',
                icon_url=ctx.author.avatar_url
            ))

    @commands.command(help='Change the timezone displayed in incidents')
    @is_staff()
    async def timezone(self, ctx: commands.Context, tz: str = None):
        storage = ctx.bot.get_storage(ctx.guild)  # type: Storage
        if tz is None:
            offset = await storage.get_float('timezone', default=0)
            tzinfo = datetime.timezone(datetime.timedelta(seconds=offset))
            time = ctx.message.created_at.replace(tzinfo=tzinfo)
            str = time.strftime('UTC%z')
            return await ctx.send(embed=discord.Embed(
                description=f'Current timezone is: {str}',
                color=ctx.bot.colorsg['info']
            ))

        try:
            time = datetime.datetime.strptime(tz, 'UTC%z')
        except ValueError:
            return await ctx.send(embed=discord.Embed(
                description=(
                    f'Invalid timezone: {tz!r}\n\n'
                    f'- Make sure the timezone starts with UTC\n'
                    f'- Make sure you don\'t forget the + or -\n\n'
                    f'Examples:\n'
                    f'- `UTC+0100` CET\n'
                    f'- `UTC-0700` PDT\n'
                ),
                color=ctx.bot.colorsg['failure']
            ))

        offset = time.tzinfo.utcoffset(time).total_seconds()
        await storage.set('timezone', offset)

        str = time.strftime('UTC%z')
        return await ctx.send(embed=discord.Embed(
            description=f'Timezone set to: {str}',
            color=ctx.bot.colorsg['success']
        ))


def setup(bot: commands.Bot):
    bot.add_cog(Config())
