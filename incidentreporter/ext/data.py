
import discord
from discord.ext import commands

from ..storage import Storage


class Data(commands.Cog):
    @commands.command(
        help='All data related to this guild is deleted and the bot leaves '
             'the guild',
        name='data-delete'
    )
    @commands.has_permissions(administrator=True)
    async def data_delete(self, ctx: commands.Context, *, args: str = None):
        if args != 'confirm':
            return await ctx.send(
                embed=discord.Embed(
                    description=(
                        'This will remove all data related to this guild and '
                        'the bot will immediately leave the guild.\n\n'
                        'This **cannot** be undone.\n\n'
                        'Use `data-delete confirm` to confirm this.'
                    ),
                    color=ctx.bot.config.colors['failure']
                )
            )

        stor = ctx.bot.storage  # type: Storage

        keys = []
        async for key in stor.scan(f'guild:{ctx.guild.id}:*'):
            keys.append(key)

        if keys:
            await stor.delete(*keys)

        await ctx.send('All data deleted, thanks for using me and bye :heart:')
        await ctx.guild.leave()


def setup(bot: commands.Bot):
    bot.add_cog(Data())
