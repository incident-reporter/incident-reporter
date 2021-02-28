
from discord.ext import commands

from .storage import Storage


class NotStaff(commands.CheckFailure):
    pass


class NotPremium(commands.CheckFailure):
    pass


class GuildBanned(commands.CheckFailure):
    pass


def is_staff():
    async def predicate(ctx: commands.Context):
        if ctx.channel.permissions_for(ctx.author).manage_guild:
            return True
        storage = ctx.bot.get_storage(ctx.guild)  # type: Storage
        roles = set(x.id for x in ctx.author.roles)
        async for role in storage.as_set('staff'):
            if int(role) in roles:
                return True

        raise NotStaff()

    return commands.check(predicate)


def has_premium():
    async def predicate(ctx: commands.Context):
        storage = ctx.bot.get_storage(ctx.guild)  # type: Storage
        if await storage.exists('premium'):
            return True
        raise NotPremium()

    return commands.check(predicate)


def is_guild_banned():
    async def predicate(ctx: commands.Context):
        storage = ctx.bot.get_storage(ctx.guild)  # type: Storage
        reason = await storage.get_str('ban')
        if reason is None:
            return True
        raise GuildBanned(reason)

    return commands.check(predicate)
