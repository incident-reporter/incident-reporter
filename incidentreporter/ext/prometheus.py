
import threading
import typing as t
from wsgiref.simple_server import make_server

import discord
from discord.ext import commands

from prometheus_client import CollectorRegistry, make_wsgi_app, Counter, Gauge
from prometheus_client.exposition import (
    ThreadingWSGIServer, _SilentHandler as SilentHandler
)


# noinspection PyUnusedLocal
class Prometheus(commands.Cog):
    def __init__(self, bot: commands.Bot, registry):
        self.pr_messages = Counter(
            'incidentreporter_messages', 'Total messages', registry=registry
        )
        self.pr_commands = Counter(
            'incidentreporter_commands', 'Total commands', registry=registry
        )
        self.pr_exceptions = Counter(
            'incidentreporter_exceptions', 'Unhandled exceptions',
            registry=registry
        )
        self.pr_guilds = Gauge(
            'incidentreporter_guilds', 'Guilds', registry=registry
        )
        self.pr_guilds.set_function(lambda: len(bot.guilds))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        self.pr_messages.inc()

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        self.pr_commands.inc()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, exception):
        self.pr_exceptions.inc()


httpd = None  # type: t.Optional[ThreadingWSGIServer]
httpdt = None  # type: t.Optional[threading.Thread]


def setup(bot: commands.Bot):
    global httpd, httpdt

    registry = CollectorRegistry()
    pr = Prometheus(bot, registry)
    bot.add_cog(pr)

    app = make_wsgi_app(registry=registry)
    port = bot.config.getint('prometheus', 'port')
    httpd = make_server('localhost', port, app,
                        ThreadingWSGIServer, handler_class=SilentHandler)
    httpdt = threading.Thread(target=httpd.serve_forever)
    httpdt.daemon = True
    httpdt.start()


# noinspection PyUnusedLocal
def teardown(bot: commands.Bot):
    httpd.shutdown()
    httpdt.join()
    httpd.server_close()  # shut the socket down to free the address
