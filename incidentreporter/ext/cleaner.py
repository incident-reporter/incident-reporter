
import base64
import datetime
from pathlib import Path

from discord.ext import commands, tasks
from discord.utils import snowflake_time


class ErrorlogCleaner(commands.Cog):
    def __init__(self, bot):
        self.maxage = bot.config.getint('errorlog', 'max-age')  # type: int
        self.errorlog = bot.errorlog  # type: Path
        self.cleaner.start()

    def cog_unload(self):
        self.cleaner.cancel()

    @tasks.loop(hours=1)
    async def cleaner(self):
        now = datetime.datetime.utcnow()
        for errorlog in self.errorlog.iterdir():
            if not errorlog.name.startswith('.') and errorlog.suffix == '.log':
                messageid = base64.urlsafe_b64decode(errorlog.stem.encode())
                time = snowflake_time(int.from_bytes(messageid, 'big'))
                if (now - time).total_seconds() > self.maxage:
                    errorlog.unlink()


def setup(bot):
    if bot.errorlog:
        bot.add_cog(ErrorlogCleaner(bot))
