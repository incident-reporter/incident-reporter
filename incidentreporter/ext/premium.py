
import logging
import re

import discord
from discord.ext import commands
import humanfriendly

from ..storage import Storage


logger = logging.getLogger(__name__)
# UUID regex to verify the code before the api request
UUID4 = re.compile(
    r'[\dabcdef]{8}-[\dabcdef]{4}-[\dabcdef]{4}-[\dabcdef]{4}-[\dabcdef]{12}'
)


# noinspection PyUnresolvedReferences
def _patch_humanfriendly():
    # Add months support to humanfriendly.format_timespan()
    #   humanfriendly does some weird wrapping for backward compatibility
    #   so we have to use .module which confuses PyCharm
    if getattr(humanfriendly.module, '__month_patched__', None):
        return  # already patched

    humanfriendly.module.time_units = list(humanfriendly.module.time_units)
    humanfriendly.module.time_units.insert(
        len(humanfriendly.time_units) - 1,
        dict(divider=60 * 60 * 24 * 30, singular='month', plural='months',
             abbreviations=['M'])
    )
    humanfriendly.module.time_units = tuple(
        humanfriendly.module.time_units
    )
    humanfriendly.module.__month_patched__ = True  # so we dont patch again


class Premium(commands.Cog):
    @staticmethod
    def shoppy_products(ctx: commands.Context):
        for key, section in ctx.bot.config.items():
            if key.startswith('shoppy:'):
                yield (key[7:], section.get('duration text'),
                       section.getint('duration'), section.getfloat('price'))

    @commands.command(help='Shows your current subscription status')
    @commands.has_permissions(administrator=True)
    async def subscription(self, ctx: commands.Context):
        storage = ctx.bot.get_storage(ctx.guild)  # type: Storage
        shop = []
        for product_id, duration_text, _, price in self.shoppy_products(ctx):
            shop.append(
                f':arrow_right: You can buy premium for __{duration_text}'
                f'__ [here](https://shoppy.gg/product/{product_id}). '
                f'*({price}€)*'
            )

        if await storage.exists('premium'):
            expires = await storage.ttl('premium')
            if expires >= 0:
                color = 'green' if expires > 60 * 60 * 24 * 7 else 'yellow'
                await ctx.send(embed=discord.Embed(
                    description=(
                        f'Subscription: :{color}_square:\n Expires: '
                        + humanfriendly.format_timespan(expires)
                    ) + ((
                        '\n\n:warning: Your subscription expires within the '
                        'next week!\n\n' + '\n'.join(shop)
                    ) if color == 'yellow' else ''),
                    color=ctx.bot.colorsg[
                        'success' if color == 'green' else 'warning']
                ).set_footer(
                    text=f'Requested by {ctx.author}',
                    icon_url=ctx.author.avatar_url
                ))
            else:
                await ctx.send(embed=discord.Embed(
                    description=(
                        'Subscription: :green_square:\n Expires: '
                        '**Never**'
                    ),
                    color=ctx.bot.colorsg['success']
                ).set_footer(
                    text=f'Requested by {ctx.author}',
                    icon_url=ctx.author.avatar_url
                ))
        else:
            await ctx.send(embed=discord.Embed(
                description=(
                    'Subscription: :red_square:\n'
                    'Expires: **Expired**\n\n'
                    + '\n'.join(shop)
                ),
                color=ctx.bot.colorsg['failure']
            ).set_footer(
                text=f'Requested by {ctx.author}',
                icon_url=ctx.author.avatar_url
            ))

    @commands.command(help='Redeem your premium subscription '
                           'from a shoppy order id')
    @commands.has_permissions(administrator=True)
    @commands.cooldown(rate=3, per=300, type=commands.BucketType.guild)
    async def redeem(self, ctx: commands.Context, orderid: str):
        if not UUID4.fullmatch(orderid):
            return await ctx.send(embed=discord.Embed(
                description='The supplied order id is malformed.',
                color=ctx.bot.colorsg['failure']
            ).set_footer(
                text=f'Requested by {ctx.author}',
                icon_url=ctx.author.avatar_url
            ))

        storage = ctx.bot.get_storage(ctx.guild)  # type: Storage

        if await storage.ttl('premium') == -1:
            return await ctx.send(embed=discord.Embed(
                description='This server already has a permanent premium '
                            'subscription.',
                color=ctx.bot.colorsg['failure']
            ).set_footer(
                text=f'Requested by {ctx.author}',
                icon_url=ctx.author.avatar_url
            ))
        # order has already been redeemed
        if await storage[0].exists(f'premium:{orderid}'):
            return await ctx.send(embed=discord.Embed(
                description='That order has already been redeemeed.',
                color=ctx.bot.colorsg['failure']
            ).set_footer(
                text=f'Requested by {ctx.author}',
                icon_url=ctx.author.avatar_url
            ))

        if await storage[0].exists(f'premium-gift:{orderid}'):
            j = {
                'paid_at': True,
                'disputed_at': None,
                'product_id': await storage[0].get_str(
                    f'premium-gift:{orderid}'
                ),
                'is_partial': False
            }
        else:
            r = await ctx.bot.shoppy.get(f'/api/v1/orders/{orderid}')
            if r.status_code == 404:
                return await ctx.send(embed=discord.Embed(
                    description='Unknown order id.',
                    color=ctx.bot.colorsg['failure']
                ).set_footer(
                    text=f'Requested by {ctx.author}',
                    icon_url=ctx.author.avatar_url
                ))
            elif r.status_code != 200:
                logger.warning(f'Unexpected status code by shoppy api. '
                               f'OrderID={orderid}, code={r.status_code}')
                return await ctx.send(embed=discord.Embed(
                    description='Something else went wrong.',
                    color=ctx.bot.colorsg['failure']
                ).set_footer(
                    text=f'Requested by {ctx.author}',
                    icon_url=ctx.author.avatar_url
                ))

            j = r.json()

        if j['paid_at'] is None or j['is_partial']:
            return await ctx.send(embed=discord.Embed(
                description='That order has not (fully) been paid yet.\n'
                            'Please complete the payment.',
                color=ctx.bot.colorsg['failure']
            ).set_footer(
                text=f'Requested by {ctx.author}',
                icon_url=ctx.author.avatar_url
            ))
        elif j['disputed_at'] is not None:
            return await ctx.send(embed=discord.Embed(
                description='That order has been disputed.',
                color=ctx.bot.colorsg['failure']
            ).set_footer(
                text=f'Requested by {ctx.author}',
                icon_url=ctx.author.avatar_url
            ))

        for productid, duration_text, duration, price in \
                self.shoppy_products(ctx):
            if productid == j['product_id']:
                break
        else:
            return await ctx.send(embed=discord.Embed(
                description='I don\'t recognize that product.',
                color=ctx.bot.colorsg['failure']
            ).set_footer(
                text=f'Requested by {ctx.author}',
                icon_url=ctx.author.avatar_url
            ))

        await storage[0].set('premium:' + orderid, '1')
        if duration >= 0:
            if await storage.exists('premium'):
                await ctx.send(embed=discord.Embed(
                    description=f'Thanks for your continued support! :heart:\n'
                                f'This server is now premium for additional '
                                f'**{duration_text}**.',
                    color=ctx.bot.colorsg['success']
                ).set_footer(
                    text=f'Upgraded by {ctx.author}',
                    icon_url=ctx.author.avatar_url
                ))
                await storage.expire('premium',
                                     await storage.ttl('premium') + duration)
            else:
                await ctx.send(embed=discord.Embed(
                    description=f'Thanks for supporting us!\n'
                                f'This server is now premium for '
                                f'**{duration_text}**.',
                    color=ctx.bot.colorsg['success']
                ).set_footer(
                    text=f'Upgraded by {ctx.author}',
                    icon_url=ctx.author.avatar_url
                ))
                await storage.set('premium', '1', expires=duration)

        else:
            if await storage.exists('premium'):
                await ctx.send(embed=discord.Embed(
                    description='Thanks for your continued support!\n :heart:'
                                'This server will now remain premium forever! '
                                ':tada:',
                    color=ctx.bot.colorsg['success']
                ).set_footer(
                    text=f'Upgraded by {ctx.author}',
                    icon_url=ctx.author.avatar_url
                ))
                await storage.set('premium', '1')
            else:
                await ctx.send(embed=discord.Embed(
                    description='Thanks for supporting us!\n :heart:'
                                'This server is now premium forever! :tada:',
                    color=ctx.bot.colorsg['success']
                ).set_footer(
                    text=f'Upgraded by {ctx.author}',
                    icon_url=ctx.author.avatar_url
                ))
                await storage.set('premium', '1')


def setup(bot: commands.Bot):
    _patch_humanfriendly()
    bot.add_cog(Premium())
