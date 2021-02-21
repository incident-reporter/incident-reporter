
import discord
from discord.ext import commands

from ..storage import Storage


class Roles(commands.Cog):
    @commands.command(help='Manage roles that can manage incidents')
    @commands.has_permissions(manage_guild=True)
    async def staff(self, ctx: commands.Context, *roles: discord.Role):
        storage = ctx.bot.get_storage(ctx.guild)  # type: Storage
        if roles:
            staffs = storage.as_set('staff')
            added = []
            removed = []
            for role in roles:
                if await staffs.contains(role.id):
                    await staffs.remove(role.id)
                    removed.append(role)
                elif await staffs.len() < 10:
                    await staffs.add(role.id)
                    added.append(role)
                else:
                    break

            message = ''
            if added:
                message += 'Staff roles added: ' \
                           + ', '.join(x.mention for x in added) + '\n'
            if removed:
                message += 'Staff roles removed:' \
                           + ', '.join(x.mention for x in removed) + '\n'

            if len(added) + len(removed) != len(roles):
                message += '\n\n:warning: You can only have 10 staff roles.'

            await ctx.send(embed=discord.Embed(
                description=message,
                color=(
                    ctx.bot.colorsg['success'] if added or removed else
                    ctx.bot.colorsg['failure']
                )
            ))

        else:
            staff = [int(x) async for x in storage.as_set('staff')]
            if staff:
                return await ctx.send(embed=discord.Embed(
                    description=(
                        'Your current staff roles are: '
                        + ', '.join(f'<@&{x}>' for x in staff)
                        + '\n\nSimply call this command with the roles you '
                          'want to add or remove.'
                    ),
                    color=ctx.bot.colorsg['info']
                ))
            else:
                return await ctx.send(embed=discord.Embed(
                    description=(
                        "You currently don\'t have any staff roles added.\n\n"
                        "Call this command with the roles you want to add."
                    ),
                    color=ctx.bot.colorsg['info']
                ))

    @commands.command(help='Manage roles that get pinged for new incidents')
    @commands.has_permissions(manage_guild=True)
    async def pingrole(self, ctx: commands.Context, *roles: discord.Role):
        storage = ctx.bot.get_storage(ctx.guild)  # type: Storage
        if roles:
            pings = storage.as_set('ping')
            added = []
            removed = []
            for role in roles:
                if await pings.contains(role.id):
                    await pings.remove(role.id)
                    removed.append(role)
                elif await pings.len() < 10:
                    await pings.add(role.id)
                    added.append(role)
                else:
                    break

            message = ''
            if added:
                message += 'Pinged roles added: ' \
                           + ', '.join(x.mention for x in added) + '\n'
            if removed:
                message += 'Pinged roles removed:' \
                           + ', '.join(x.mention for x in removed) + '\n'

            if len(added) + len(removed) != len(roles):
                message += '\n\n:warning: You can only have 10 roles that ' \
                           'get pinged.'

            await ctx.send(embed=discord.Embed(
                description=message,
                color=(
                    ctx.bot.colorsg['success'] if added or removed else
                    ctx.bot.colorsg['failure']
                )
            ))

        else:
            pings = [int(x) async for x in storage.as_set('ping')]
            if pings:
                return await ctx.send(embed=discord.Embed(
                    description=(
                        'Your current pinged roles are: '
                        + ', '.join(f'<@&{x}>' for x in pings)
                        + '\n\nSimply call this command with the roles you '
                          'want to add or remove.'
                    ),
                    color=ctx.bot.colorsg['info']
                ))
            else:
                return await ctx.send(embed=discord.Embed(
                    description=(
                        "You currently don\'t have any roles that get pinged "
                        "for new incidents.\n\n"
                        "Call this command with the roles you want to add."
                    ),
                    color=ctx.bot.colorsg['info']
                ))


def setup(bot: commands.Bot):
    bot.add_cog(Roles())
