
import asyncio
import configparser
import logging

import aredis

from incidentreporter.bot import IncidentReporterBot

# change default event loop to uvloop (faster than asyncio)
# but it's not available on windows, so we make it optional
try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


async def main():
    config = configparser.ConfigParser()
    config.read('config.ini')
    logging.basicConfig(level=logging.INFO)

    if not config.get('general', 'bot token'):
        print('No bot token found in config.ini')
        exit(1)

    redis = aredis.StrictRedis.from_url(config.get('general', 'redis'))
    try:
        await redis.exists('test')
    except aredis.exceptions.ConnectionError:
        print('Redis server is not running. Please make sure the URI in the '
              'config is correct.')
        exit(2)

    bot = IncidentReporterBot(config, redis)
    await bot.start(config.get('general', 'bot token'))
    if getattr(bot, 'restart'):
        import subprocess, sys
        subprocess.call([sys.executable, 'run.py'])


if __name__ == '__main__':
    asyncio.run(main())
