
import datetime
import json

import discord
from discord.ext import commands

from ..storage import Storage
from ..util import is_staff


STATE_OUTAGE = 'Outage'
STATE_PARTIAL_OUTAGE = 'Partial Outage'
STATE_MAINTENANCE = 'Maintenance'
STATE_UPDATE = 'Update'
STATE_RESOLVED = 'Resolved'

EMOJIS = {
    STATE_OUTAGE: '<:outage:812640646937706547>',
    STATE_PARTIAL_OUTAGE: '<:partial:812640663539679302>',
    STATE_MAINTENANCE: '<:partial:812640663539679302>',
    STATE_UPDATE: ':memo:',
    STATE_RESOLVED: '<:resolved:812640676701143050>'
}
COLORS = {
    STATE_OUTAGE: 0xff0000,
    STATE_PARTIAL_OUTAGE: 0xfaa61a,
    STATE_MAINTENANCE: 0xfaa61a,
    STATE_RESOLVED: 0x00ff00
}


class Incidents(commands.Cog):
    async def update_incident(self, ctx: commands.Context, state: str,
                              incident: int, message: str):
        gstorage = ctx.bot.get_storage(ctx.guild)  # type: Storage
        storage = gstorage / 'incident' / str(incident)

        if not await storage.exists('channel'):
            return await ctx.send(embed=discord.Embed(
                description='No incident with that id exists.',
                color=ctx.bot.colorsg['failure']
            ))

        channel = ctx.guild.get_channel(await storage.get_int('channel'))
        if channel is None:
            return await ctx.send(embed=discord.Embed(
                description="The channel this incident belonged to, "
                            "doesn't exist anymore.",
                color=ctx.bot.colorsg['failure']
            ))

        updates = storage.as_list('updates')
        await updates.append(json.dumps(
            (state, message, ctx.message.created_at.isoformat())
        ))

        updates = [json.loads(x) for x in await updates.copy()]
        message = '\n\n'.join([
            f'{EMOJIS[state]} **{state}**: {message}\n'
            f'*{await self.format_time(gstorage, when)}*'
            for state, message, when in updates
        ])

        resolved = updates[-1][0] == STATE_RESOLVED
        title = ':hammer_pick: ' + (
            'Resolved incident' if resolved else 'Ongoing incident'
        )
        color = COLORS[STATE_OUTAGE]
        for state, _, _ in updates:
            if state in COLORS:
                color = COLORS[state]
        embed = discord.Embed(
            title=title,
            description=message,
            color=color,
            timestamp=datetime.datetime.fromisoformat(
                updates[-1][2] if resolved else updates[0][2]
            )
        ).set_footer(text=f'Incident #{incident} | ' + (
            'Incident resolved at ' if resolved else
            'Incident started at '
        ))

        messageid = await storage.get_int('message')
        if messageid is None:
            content = None
            pingroles = [int(x) async for x in gstorage.as_set('ping')]
            if pingroles:
                content = 'New incident: ' \
                          + ', '.join(f'<@&{x}>' for x in pingroles)

            message = await channel.send(content=content, embed=embed)
            await storage.set('message', message.id)
        else:
            # we don't have access to the message object and fetching it
            # would be an unneeded api call, so just use the discord.py's
            # underlying http library
            try:
                await ctx.bot.http.edit_message(channel.id, messageid,
                                                embed=embed.to_dict())
            except discord.NotFound:
                # the message was deleted
                return await ctx.send(embed=discord.Embed(
                    description='My incident message has been deleted.',
                    color=ctx.bot.colorsg['failure']
                ))

        # we were successful
        await ctx.message.add_reaction('👍')

    @staticmethod
    async def format_time(storage: Storage, time: str):
        time = datetime.datetime.fromisoformat(time)
        offset = await storage.get_float('timezone', default=0)
        tzinfo = datetime.timezone(datetime.timedelta(seconds=offset))

        format = '%Y-%m-%d %H:%M:%S (UTC%z)'
        print(time, time.astimezone(tzinfo), offset, tzinfo)
        return time.astimezone(tzinfo).strftime(format)

    @commands.command(help='Create a new incident')
    @is_staff()
    async def new(self, ctx: commands.Context, channel: discord.TextChannel,
                  state: str, *, message: str):
        return await self.create_new(ctx, channel, state, message)

    @commands.command(help='Create a new incident in the default channel')
    @is_staff()
    async def default(self, ctx: commands.Context, state: str, *,
                      message: str):
        storage = ctx.bot.get_storage(ctx.guild)  # type: Storage

        channelid = await storage.get_int('defaultchannel')
        if channelid is None:
            prefix = (await ctx.bot.get_command_prefix(ctx.bot,
                                                       ctx.message))[0]
            return await ctx.send(embed=discord.Embed(
                description=(
                    f"You haven't send any default channel, use "
                    f"`{prefix}setdefault #channel` to set it."
                ),
                color=ctx.bot.colorsg['failure']
            ))

        channel = ctx.guild.get_channel(channelid)
        if channel is None:
            prefix = (await ctx.bot.get_command_prefix(ctx.bot,
                                                       ctx.message))[0]
            return await ctx.send(embed=discord.Embed(
                description=(
                    f"The default channel no longer exists, use "
                    f"`{prefix}setdefault #channel` to set a new one."
                ),
                color=ctx.bot.colorsg['failure']
            ))

        return await self.create_new(ctx, channel, state, message)

    @commands.command(help='Set the default channel for the default command')
    @is_staff()
    async def setdefault(self, ctx: commands.Context,
                         channel: discord.TextChannel = None):
        storage = ctx.bot.get_storage(ctx.guild)  # type: Storage

        if channel is None:
            channelid = await storage.get_int('defaultchannel')
            if channelid is None:
                return await ctx.send(embed=discord.Embed(
                    description='No default channel set.',
                    color=ctx.bot.colorsg['failure']
                ))
            return await ctx.send(embed=discord.Embed(
                description=f'The default channel is <#{channelid}>',
                color=ctx.bot.colorsg['success']
            ))

        await storage.set('defaultchannel', channel.id)
        prefix = (await ctx.bot.get_command_prefix(ctx.bot, ctx.message))[0]
        return await ctx.send(embed=discord.Embed(
            description=(
                f'The default channel has been set to {channel.mention}!\n\n'
                f'You can now use `{prefix}default` instead of `{prefix}new`.'
            ),
            color=ctx.bot.colorsg['success']
        ))

    async def create_new(self, ctx: commands.Context,
                         channel: discord.TextChannel, state: str,
                         message: str):
        if not channel.permissions_for(ctx.guild.me).send_messages:
            return await ctx.send(embed=discord.Embed(
                description=(
                    f"I'm missing the **send messages** permission "
                    f"in {channel.mention}.\n"
                    f"Correct my permissions and try again!"
                ),
                color=ctx.bot.colorsg['failure']
            ))
        allowed_states = STATE_OUTAGE, STATE_PARTIAL_OUTAGE, STATE_MAINTENANCE
        if state not in allowed_states:
            prefix = (await ctx.bot.get_command_prefix(ctx.bot,
                                                       ctx.message))[0]
            return await ctx.send(embed=discord.Embed(
                description=(
                    f'State must either be in {allowed_states!r}, '
                    f'not {state!r}. '
                    f'*(case sensitive)*\n\n'
                    f'- `{prefix}new #status-updates Outage Bot offline`\n'
                    f'- `{prefix}new #status-updates "Partial Outage" '
                    f'Several shards offline`\n'
                    f'- `{prefix}new #status-updates Maintenance Bot '
                    f'maintenance; expect downtime`'
                ),
                color=ctx.bot.colorsg['failure']
            ))

        storage = ctx.bot.get_storage(ctx.guild)  # type: Storage
        incident = await storage.increment('incidents')
        await storage.set(f'incident:{incident}:channel', channel.id)
        await self.update_incident(ctx, state, incident, message)

        prefix = (await ctx.bot.get_command_prefix(ctx.bot, ctx.message))[0]
        await ctx.send(embed=discord.Embed(
            title=f'Incident {incident} created!',
            description=(
                f'The incident id is **{incident}**.\n\n'
                f'You can now use commands to update the incident.\n'
                f'- `{prefix}update {incident} An awesome update.`\n'
                f'- `{prefix}resolve {incident} The issue has been resolved.`'
            ),
            color=ctx.bot.colorsg['success']
        ))

    @commands.command(help='Add an outage update to an incident')
    @is_staff()
    async def outage(self, ctx: commands.Context, incident: int, *,
                     message: str):
        await self.update_incident(ctx, STATE_OUTAGE, incident, message)

    @commands.command(name='partial-outage', aliases=['partial'],
                      help='Add a partial outage update to an incident')
    @is_staff()
    async def partial_outage(self, ctx: commands.Context, incident: int, *,
                             message: str):
        await self.update_incident(ctx, STATE_PARTIAL_OUTAGE, incident,
                                   message)

    @commands.command(help='Add a maintenance update to an incident')
    @is_staff()
    async def maintenance(self, ctx: commands.Context, incident: int, *,
                          message: str):
        await self.update_incident(ctx, STATE_MAINTENANCE, incident, message)

    @commands.command(help='Add an update to an incident')
    @is_staff()
    async def update(self, ctx: commands.Context, incident: int, *,
                     message: str):
        await self.update_incident(ctx, STATE_UPDATE, incident, message)

    @commands.command(help='Resolve an incident')
    @is_staff()
    async def resolve(self, ctx: commands.Context, incident: int, *,
                      message: str):
        await self.update_incident(ctx, STATE_RESOLVED, incident, message)


def setup(bot: commands.Bot):
    bot.add_cog(Incidents())
