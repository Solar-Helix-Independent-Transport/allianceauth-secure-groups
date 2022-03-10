# Cog Stuff
from discord.ext import commands
from discord.embeds import Embed
from discord.colour import Color
# AA Contexts
from django.conf import settings
from django.contrib.auth.models import User, Group

from django.core.exceptions import ObjectDoesNotExist
from allianceauth.eveonline.models import EveCharacter
# AA-Discordbot
from aadiscordbot.cogs.utils.decorators import sender_has_perm

import logging

logger = logging.getLogger(__name__)


class GroupCheck(commands.Cog):
    """
    All about grouos!
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    @sender_has_perm('corputils.view_alliance_corpstats')
    async def sg_audit(self, ctx):
        """
        Smart Group Audit of a user
        Input: [group name]|[main_character]
        """
        if ctx.message.channel.id not in settings.ADMIN_DISCORD_BOT_CHANNELS:
            return await ctx.message.add_reaction(chr(0x1F44E))

        input_name = ctx.message.content[10:].split("|")

        embed = Embed(
            title="{group} Audit: {character_name}".format(
                character_name=input_name[1], group=input_name[0])
        )

        try:
            char = EveCharacter.objects.get(character_name=input_name[1])
            group = Group.objects.get(name=input_name[0])

            try:
                main = char.character_ownership.user
                checks = group.smartgroup.run_check_on_user(main)

                embed.colour = Color.blue()

                for c in checks:
                    msg = c.get("message")
                    if not msg:
                        msg = "Pass: {}".format(c.get("check"))

                    embed.add_field(
                        name="{} (Pass: {})".format(c.get("filter").filter_object.description, c.get("check")), value=msg, inline=False
                    )

                return await ctx.send(embed=embed)
            except ObjectDoesNotExist as e:
                return await ctx.send("Member or Group issues")

        except EveCharacter.DoesNotExist:
            embed.colour = Color.red()

            embed.description = (
                "Character **{character_name}** does not exist in our Auth system"
            ).format(character_name=input_name[1])

            return await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(GroupCheck(bot))
