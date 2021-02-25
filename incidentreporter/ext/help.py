
import discord
from discord.ext import commands

from ..__version__ import __version__
from ..bot import INVITE_PERMISSIONS


class Help(commands.Cog):
    @commands.command(help='Sends an invite for the bot')
    async def invite(self, ctx: commands.Context):
        appinfo = await ctx.bot.application_info()
        if not appinfo.bot_public:
            disclaimer = (
                ':warning: I am currently not public, you must be the bot '
                'owner or in the application team to invite me.\n'
            )
        else:
            disclaimer = ''

        link = discord.utils.oauth_url(ctx.bot.user.id, INVITE_PERMISSIONS)
        await ctx.send(embed=discord.Embed(
            title='Here\'s my invite link!',
            url=link,
            description=(
                f'{link}'
                f'\n\n{disclaimer}:information_source: You need to have the '
                f'**Manage Server** permission to invite me.'
                f'\n\n__What permissions do I need to work properly__?'
            ),
            color=ctx.bot.colorsg['info']
        ).set_footer(
            text=f'Requested by {ctx.author}',
            icon_url=ctx.author.avatar_url
        ).add_field(
            name='Send & Read Messages',
            value='I **must have** this permission to respond to commands and '
                  'send notifications.'
        ).add_field(
            name='Embed Links',
            value='I **must have** this permission to properly respond to '
                  'commands and display incidents.'
        ))

    @commands.command(help='Information about the bot')
    async def about(self, ctx: commands.Context):
        github = 'https://github.com/Le0Developer/incident-reporter'
        await ctx.send(embed=discord.Embed(
            description=(
                f'[Incident Reporter is an opensource]({github}) discord bot '
                f'for managing incidents.\nIncident Reporter is '
                f'[licensed under MIT]({github}/blob/master/LICENSE).'
            ),
            color=ctx.bot.colorsg['info']
        ).add_field(
            name='Support server',
            value=ctx.bot.config.get('general', 'support server')
        ).add_field(
            name='Bot version',
            value=(
                f'[{__version__}]'
                f'({github}/releases/tag/v{__version__})'
            )
        ).add_field(
            name='discord.py version',
            value=f'[{discord.__version__}]'
                  f'(https://github.com/Rapptz/discord.py/'
                  f'releases/tag/v{discord.__version__})'
        ).set_footer(
            text=f'Requested by {ctx.author}',
            icon_url=ctx.author.avatar_url
        ))

    @commands.command(help='Getting started with incidents',
                      aliases=['getting-start', 'quickstart'])
    async def getting_started(self, ctx: commands.Context):
        prefix = (await ctx.bot.get_command_prefix(ctx.bot, ctx.message))[0]
        message = (
            f'Hey :wave:,\nthis is the quickstart guide for using me '
            f':slight_smile:\n\n'
            f'__Creating an incident__\n'
            f'You can create an incident with the `new` command. The syntax '
            f'is: `new <channel> (Outage|"Partial Outage") <message>`\n\n'
            f'`{prefix}new #status-update Outage Bot offline`\n'
            f'`{prefix}new #status-update "Partial Outage" '
            f'Several shards offline`\n\n'
            f'The bot will respond with an **incident id**, which you should '
            f'remember, because it\'s used for updating the incident.\n\n'
            f'__Updating an incident__\n'
            f'To update an incident you can use one of the follow commands. '
            f'They all have the same syntax: `STATE <incident id> <message>`'
            f'\n\n`outage`, `partial-outage`, `update` or `resolve`.\n\n'
            f'`{prefix}partial-outage 42 Some shards have recovered.`\n'
            f'`{prefix}update 42 Our engineers identified the core issue`\n'
            f'`{prefix}outage 42 Entire bot is restarting for fix`\n'
            f'`{prefix}resolve 42 The issue has been fixed and the bot is '
            f'operational. Thank you for your patience.`\n\n'
            f'__Permissions__\n'
            f'You need the **manage server** permission to create and manage '
            f'incidents.'
        )
        example_image = (
            'https://cdn.discordapp.com/attachments/808282485104443393'
            '/812733121539604500/example.png'
        )
        await ctx.send(embed=discord.Embed(
            description=message,
            color=ctx.bot.colorsg['success'],
        ).set_image(url=example_image))


def setup(bot):
    bot.add_cog(Help(bot))
