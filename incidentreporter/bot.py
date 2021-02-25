from __future__ import annotations

import base64
import configparser
import logging
import os
from pathlib import Path
import traceback

import aredis
import discord
from discord.ext import commands
import httpx

from .storage import Storage
from .util import NotStaff, NotPremium


EXTENSIONS = [
    'incidentreporter.ext.cleaner',
    'incidentreporter.ext.config',
    'incidentreporter.ext.data',
    'incidentreporter.ext.dev',
    'incidentreporter.ext.help',
    'incidentreporter.ext.incidents',
    'incidentreporter.ext.premium',
    'incidentreporter.ext.roles',
    'incidentreporter.ext.statusembed',
]
INTENTS = discord.Intents(
    guilds=True,  # for working guild cache
    guild_messages=True,  # dont even bother about dm_messages
)
# Names are according to discord ui (EN-UK)
PERMISSIONS = {
    'add_reactions': 'Add Reactions',
    'administrator': 'Administrator',
    'attach_files': 'Attach Files',
    'ban_members': 'Ban Members',
    'change_nickname': 'Change Nickname',
    'connect': 'Connect',
    'create_instant_invite': 'Create Invite',
    'deafen_members': 'Deafen Members',
    'embed_links': 'Embed Links',
    'external_emojis': 'Use External Emojis',
    'kick_members': 'Kick Members',
    'manage_channels': 'Manage Channels',
    'manage_emojis': 'Manage Emojis',
    'manage_guild': 'Manage Server',
    'manage_messages': 'Manage Messages',
    'manage_nicknames': 'Manage Nicknames',
    'manage_permissions': 'Manage Roles',
    'manage_roles': 'Manage Roles',
    'manage_webhooks': 'Manage Webhooks',
    'mention_everyone': 'Mention @everyone, @here, and All Roles',
    'move_members': 'Move Members',
    'mute_members': 'Mute Members',
    'priority_speaker': 'Priority Speaker',
    'read_message_history': 'Read Message History',
    'read_messages': 'View Channels',
    'send_messages': 'Send Messages',
    'send_tts_messages': 'Send TTS Message',
    'speak': 'Speak',
    'stream': 'Video',
    'use_external_emojis': 'Use External Emojis',
    'use_voice_activation': 'Use Voice Activity',
    'view_audit_log': 'View Audit Log',
    'view_channel': 'View Channels',
    'view_guild_insights': 'View Server Insights'
}
INVITE_PERMISSIONS = discord.Permissions(
    send_messages=True,
    read_messages=True,
    embed_links=True,  # so our messages are beautiful
)

logger = logging.getLogger(__name__)


class IncidentReporterBot(commands.Bot):
    def __init__(self, config: configparser.ConfigParser,
                 redis: aredis.StrictRedis, **kwargs):
        super().__init__(
            activity=discord.Activity(
                name='out for new incidents',
                type=discord.ActivityType.watching
            ),
            command_prefix=self.get_command_prefix,
            intents=INTENTS,
            **kwargs
        )
        self.config = config
        self.default_prefix = self.config.get('general', 'default_prefix')
        # eval() for supporting hex colors, should be safe because it's
        # directly from the config
        self.colorsg = {key: eval(value)
                        for key, value in self.config.items('colors:generic')}

        self.errorlog = None
        if self.config.getboolean('errorlog', 'enabled'):
            self.errorlog = Path(self.config.get('errorlog', 'path'))

        self.storage = Storage(redis)
        self.shoppy = httpx.AsyncClient(headers={
            'Authorization': self.config.get('shoppy', 'api key'),
            'User-Agent': 'python-httpx (Incident Reporter Bot)'
        }, base_url='https://shoppy.gg/')

        self._loaded_extensions = False

        self.add_check(
            commands.bot_has_permissions(embed_links=True).predicate,
            call_once=True
        )

    async def on_ready(self):
        if not self._loaded_extensions:
            if self.config.getboolean('prometheus', 'enabled'):
                EXTENSIONS.append('incidentreporter.ext.prometheus')

            logger.info('loading extensions')
            for extension in EXTENSIONS:
                logger.info(f'loading extension: {extension}')
                self.load_extension(extension)
            logger.info('loaded extensions')
            self._loaded_extensions = True

            print('-' * os.get_terminal_size().columns)
            print(f'Name: {self.user}  ({self.user.id})')
            print(f'Guilds: {len(self.guilds)}')

            if not self.guilds:  # in no servers, let's print an invite :)
                print()
                print('Hey! It seems like I am in no servers, you can invite '
                      'me with the link below.')
                print(
                    '==> '
                    + discord.utils.oauth_url(self.user.id, INVITE_PERMISSIONS)
                )
                print()
            print('-' * os.get_terminal_size().columns)

    @staticmethod
    async def get_command_prefix(bot: IncidentReporterBot,
                                 message: discord.Message):
        return (
            await bot.get_storage(message.guild).get_str(
                'prefix',
                default=bot.default_prefix
            ),
            bot.user.mention + ' ',
            f'<@!{bot.user.id}> '
        )

    def get_storage(self, guild: discord.Guild) -> Storage:
        return self.storage / 'guild' / guild.id

    async def on_command_error(self, ctx: commands.Context, exception):
        if isinstance(exception, commands.CommandError):
            if isinstance(exception, commands.MissingRequiredArgument):
                prefix = (await self.get_command_prefix(self, ctx.message))[0]
                return await ctx.send(embed=discord.Embed(
                    description=(
                        f'You are missing a required argument: '
                        f'`{exception.param.name}`.\n'
                        f'For more help use `{prefix}help {ctx.command.name}`'
                    ),
                    color=self.colorsg['failure']
                ))
            elif isinstance(exception, commands.CommandNotFound):
                return
            elif isinstance(exception, commands.MissingPermissions):
                return await ctx.send(embed=discord.Embed(
                    description=(
                        'You are missing permissions to execute this command: '
                        + ', '.join(f'**{PERMISSIONS.get(x, x)}**'
                                    for x in exception.missing_perms)
                    ),
                    color=self.colorsg['failure']
                ))
            elif isinstance(exception, commands.BotMissingPermissions):
                if 'embed_links' in exception.missing_perms:
                    return await ctx.send(
                        "I'm missing permissions to execute this command: "
                        + ', '.join(f'**{PERMISSIONS.get(x, x)}**'
                                    for x in exception.missing_perms)
                    )
                else:
                    return await ctx.send(embed=discord.Embed(
                        description=(
                            "I'm missing permissions to execute this command: "
                            + ', '.join(f'**{PERMISSIONS.get(x, x)}**'
                                        for x in exception.missing_perms)
                        ),
                        color=self.colorsg['failure']
                    ))
            elif isinstance(exception, commands.NotOwner):
                return await ctx.send(embed=discord.Embed(
                    description='This command is reserved for my owners.',
                    color=self.colorsg['failure']
                ))
            elif isinstance(exception, commands.ChannelNotFound):
                return await ctx.send(embed=discord.Embed(
                    description='You supplied an invalid channel, please '
                                'check your spelling and make sure the '
                                'channel actually exists.',
                    color=self.colorsg['failure']
                ))
            elif isinstance(exception, (commands.BadArgument,
                                        commands.ExpectedClosingQuoteError)):
                return await ctx.send(embed=discord.Embed(
                    description='You supplied a bad argument, please check '
                                'your spelling.',
                    color=self.colorsg['failure']
                ))
            elif isinstance(exception, NotStaff):
                return await ctx.send(embed=discord.Embed(
                    description=(
                        "You're not staff.\n"
                        "Make sure you've the **Manage Server** permission or "
                        "have one of the staff roles."
                    ),
                    color=self.colorsg['failure']
                ))
            elif isinstance(exception, NotPremium):
                return await ctx.send(embed=discord.Embed(
                    description='You need premium to use this command',
                    color=self.colorsg['failure']
                ))

        logger.exception(
            f'An exception occured while executing {ctx.command.name}.',
            exc_info=exception
        )

        support = self.config.get('general', 'support server')
        if not self.errorlog:
            return await ctx.send(embed=discord.Embed(
                description=(
                    f'An error occured during the execution of this command.\n'
                    f'If this keeps happening contact our support team.\n\n'
                    f':link: [Support Server]({support})'
                ),
                color=self.colorsg['failure']
            ))

        error = base64.urlsafe_b64encode(
            ctx.message.id.to_bytes(12, 'big')
        ).decode()
        error_text = ''.join(traceback.format_exception(
            type(exception), exception, exception.__traceback__
        ))
        error_text = (
            f'Message: {ctx.message.content!r}\n'
            f'More: {ctx.message.id} ({ctx.message.created_at.isoformat()})\n'
            f'Author: {ctx.author!r} ({ctx.author.id})\n'
            f'Guild: {ctx.guild!r} ({ctx.guild.id})\n'
            f'----------------\n'
            f'{error_text}'
        )

        if not self.errorlog.exists():
            self.errorlog.mkdir(parents=True)
        with (self.errorlog / f'{error}.log').open('w') as f:
            f.write(error_text)

        await ctx.send(embed=discord.Embed(
            description=(
                f'An error occured during the execution of this command.\n'
                f'Error code: `{error}`\n'
                f'If this keeps happening contact our support team.\n\n'
                f':link: [Support Server]({support})'
            ),
            color=self.colorsg['failure']
        ))
