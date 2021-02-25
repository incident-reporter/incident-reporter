
import json

import discord
from discord.ext import commands

from .incidents import (
    EMOJIS, COLORS,
    STATE_OPERATIONAL, STATE_OUTAGE, STATE_PARTIAL_OUTAGE, STATE_MAINTENANCE,
    STATE_RESOLVED
)
from ..storage import Storage
from ..util import has_premium


ORDER = (STATE_OUTAGE, STATE_PARTIAL_OUTAGE, STATE_MAINTENANCE, STATE_RESOLVED)


class StatusEmbed(commands.Cog):
    @staticmethod
    async def update_statusembed(ctx: commands.Context, id: int,
                                 incident: bool = False):
        gstorage = ctx.bot.get_storage(ctx.guild)  # type: Storage
        storage = gstorage / 'statusembed' / str(id)

        if not await storage.exists('channel'):
            return await ctx.send(embed=discord.Embed(
                description='No statusembed with that id exists.',
                color=ctx.bot.colorsg['failure']
            ))

        channel = ctx.guild.get_channel(await storage.get_int('channel'))
        if channel is None:
            return await ctx.send(embed=discord.Embed(
                description="The channel this incident belonged to, "
                            "doesn't exist anymore.",
                color=ctx.bot.colorsg['failure']
            ))

        texts = await storage.as_list('text').copy()
        incidents = {}
        for textid, _ in enumerate(texts):
            if await storage.exists(f'incident:{textid}'):
                incidents[textid] = await storage.get_int(
                    f'incident:{textid}'
                )

        message = f'{EMOJIS[STATE_OPERATIONAL]} __All systems operational__'
        color = COLORS[STATE_OPERATIONAL]
        if len(incidents) == len(texts):
            message = f'{EMOJIS[STATE_OUTAGE]}' \
                      f' __All systems experience downtime__'
            color = COLORS[STATE_OUTAGE]
        elif len(incidents) == 1:
            message = f'{EMOJIS[STATE_PARTIAL_OUTAGE]} ' \
                      f'__One system experiences downtime__'
            color = COLORS[STATE_PARTIAL_OUTAGE]
        elif incidents:
            message = f'{EMOJIS[STATE_PARTIAL_OUTAGE]} ' \
                      f'__Several systems experience downtime__'
            color = COLORS[STATE_PARTIAL_OUTAGE]

        systems = []
        for textid, text in enumerate(texts):
            if textid in incidents:
                updates = gstorage / 'incident' / incidents[textid]
                updates = [json.loads(x)
                           async for x in updates.as_list('updates')]
                for state, _, _ in updates[::-1]:
                    if state in COLORS:
                        systems.append(f'{EMOJIS[state]} **{state}**: '
                                       f'{text.decode()}')
                        break
            else:
                systems.append(
                    f'{EMOJIS[STATE_OPERATIONAL]} **{STATE_OPERATIONAL}**: '
                    f'{text.decode()}'
                )

        embed = discord.Embed(
            description=message + '\n\n' + '\n'.join(systems),
            color=color
        )
        messageid = await storage.get_int('message')
        try:
            await ctx.bot.http.edit_message(channel.id, messageid,
                                            embed=embed.to_dict())
        except discord.NotFound:
            # the message was deleted
            return await ctx.send(embed=discord.Embed(
                description='My status embed message has been deleted.',
                color=ctx.bot.colorsg['failure']
            ))

        if not incident:
            await ctx.message.add_reaction('👍')

    @commands.group(help='Manage status embeds')
    @commands.has_permissions(manage_guild=True)
    @has_premium()
    async def statusembed(self, ctx: commands.Context):
        if ctx.subcommand_passed is None:
            prefix = (await ctx.bot.get_command_prefix(ctx.bot,
                                                       ctx.message))[0]
            await ctx.send(embed=discord.Embed(
                description=(
                    f'Subcommand is missing.\n\n'
                    f'- `{prefix}statusembed new #channel`\n'
                    f'- `{prefix}statusembed add <id> <text>`\n'
                    f'- `{prefix}statusembed remove <id> <textid>`\n'
                    f'- `{prefix}statusembed delete <id>`'
                ),
                color=ctx.bot.colorsg['failure']
            ))

    @statusembed.command()
    @commands.has_permissions(manage_guild=True)
    @has_premium()
    async def new(self, ctx: commands.Context, channel: discord.TextChannel):
        perms = channel.permissions_for(ctx.guild.me)
        if not perms.send_messages:
            return await ctx.send(embed=discord.Embed(
                description=(
                    f"I'm missing the **send messages** permission "
                    f"in {channel.mention}.\n"
                    f"Correct my permissions and try again!"
                ),
                color=ctx.bot.colorsg['failure']
            ))
        if not perms.embed_links:
            return await ctx.send(embed=discord.Embed(
                description=(
                    f"I'm missing the **embed links** permission "
                    f"in {channel.mention}.\n"
                    f"Correct my permissions and try again!"
                ),
                color=ctx.bot.colorsg['failure']
            ))

        gstorage = ctx.bot.get_storage(ctx.guild)  # type: Storage
        id = await gstorage.increment('statusembeds')
        storage = gstorage / 'statusembed' / str(id)

        await storage.set('channel', channel.id)
        message = await channel.send(embed=discord.Embed(
            description=f'{EMOJIS[STATE_OPERATIONAL]} All systems operational',
            color=ctx.bot.colorsg['success']
        ))
        await storage.set('message', message.id)

        prefix = (await ctx.bot.get_command_prefix(ctx.bot, ctx.message))[0]
        await ctx.send(embed=discord.Embed(
            title=f'Statusembed {id} created!',
            description=(
                f'The statusembed id is **{id}**.\n\n'
                f'You can now use commands to manage the statusembed.\n'
                f'- `{prefix}statusembed add {id} "Bot Status"`\n'
            ),
            color=ctx.bot.colorsg['success']
        ))

    @statusembed.command()
    @commands.has_permissions(manage_guild=True)
    @has_premium()
    async def add(self, ctx: commands.Context, id: int, text: str):
        gstorage = ctx.bot.get_storage(ctx.guild)  # type: Storage
        storage = gstorage / 'statusembed' / str(id)
        if not await storage.exists('message'):
            return await ctx.send(embed=discord.Embed(
                description='No statusembed with that id exists.',
                color=ctx.bot.colorsg['failure']
            ))

        texts = storage.as_list('text')
        await texts.append(text)

        await self.update_statusembed(ctx, id)

    @statusembed.command()
    @commands.has_permissions(manage_guild=True)
    @has_premium()
    async def remove(self, ctx: commands.Context, id: int, textid: int):
        gstorage = ctx.bot.get_storage(ctx.guild)  # type: Storage
        storage = gstorage / 'statusembed' / str(id)
        if not await storage.exists('message'):
            return await ctx.send(embed=discord.Embed(
                description='No statusembed with that id exists.',
                color=ctx.bot.colorsg['failure']
            ))

        texts = storage.as_list('text')
        if textid <= 0 or textid > await texts.len():
            return await ctx.send(embed=discord.Embed(
                description='Invalid text id.',
                color=ctx.bot.colorsg['failure']
            ))
        await texts.del_(textid - 1)

        await self.update_statusembed(ctx, id)

    @statusembed.command()
    @commands.has_permissions(manage_guild=True)
    @has_premium()
    async def delete(self, ctx: commands.Context, id: int):
        gstorage = ctx.bot.get_storage(ctx.guild)  # type: Storage
        storage = gstorage / 'statusembed' / str(id)
        if not await storage.exists('message'):
            return await ctx.send(embed=discord.Embed(
                description='No statusembed with that id exists.',
                color=ctx.bot.colorsg['failure']
            ))

        try:
            await ctx.bot.http.delete_message(
                await storage.get_int('channel'),
                await storage.get_int('message')
            )
        except discord.HTTPException:
            pass
        await storage.delete('channel', 'message', 'texts')

        return await ctx.send(embed=discord.Embed(
            description='Statusembed deleted!',
            color=ctx.bot.colorsg['failure']
        ))


def setup(bot: commands.Bot):
    bot.add_cog(StatusEmbed())
