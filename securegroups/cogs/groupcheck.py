# Cog Stuff
import logging

# AA-Discordbot
from aadiscordbot.app_settings import get_all_servers
from aadiscordbot.cogs.utils.decorators import (
    has_any_perm, in_channels, sender_has_perm,
)
from discord import AutocompleteContext, SlashCommandGroup, option
from discord.colour import Color
from discord.embeds import Embed
from discord.ext import commands

# AA Contexts
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist

from allianceauth.eveonline.models import EveCharacter

from ..models import SmartGroup

logger = logging.getLogger(__name__)


class GroupCheck(commands.Cog):
    """
    All about groups!
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
            except ObjectDoesNotExist:
                return await ctx.send("Member or Group issues")

        except EveCharacter.DoesNotExist:
            embed.colour = Color.red()

            embed.description = (
                "Character **{character_name}** does not exist in our Auth system"
            ).format(character_name=input_name[1])

            return await ctx.send(embed=embed)

    async def search_characters(ctx: AutocompleteContext):
        """Returns a list of chars that begin with the characters entered so far."""
        return list(EveCharacter.objects.filter(character_name__icontains=ctx.value).values_list('character_name', flat=True)[:10])

    async def search_groups(ctx: AutocompleteContext):
        """Returns a list of groups that begin with the characters entered so far."""
        return list(SmartGroup.objects.filter(group_name__icontains=ctx.value).values_list('group__name', flat=True)[:10])

    sg_commands = SlashCommandGroup("sec_groups", "Secure Group Admin Commands", guild_ids=get_all_servers())

    @sg_commands.command(name='audit_member', guild_ids=get_all_servers())
    @option("character", description="Search for a Character!", autocomplete=search_characters)
    @option("group", description="Group to test!", autocomplete=search_groups)
    async def slash_lookup(
        self,
        ctx,
        character: str,
        group: str
    ):
        embed = Embed(
            title=f"{group} Audit: {character}"
        )

        try:
            in_channels(ctx.channel.id, settings.ADMIN_DISCORD_BOT_CHANNELS)
            has_any_perm(ctx.author.id, [
                         'corputils.view_alliance_corpstats', 'corpstats.view_alliance_corpstats'])
            await ctx.defer()
            char = EveCharacter.objects.get(character_name=character)
            group = Group.objects.get(name=group)

            try:
                main = char.character_ownership.user
                checks = group.smartgroup.run_check_on_user(main)

                embed.colour = Color.blue()

                for c in checks:
                    msg = c.get("message")
                    if not msg:
                        msg = "Pass: {}".format(c.get("check"))

                    embed.add_field(
                        name="{} {} (Pass: {})".format(
                            ':green_circle:' if c.get(
                                'check') else ':red_circle:',
                            c.get("filter").filter_object.description,
                            c.get("check")
                        ),
                        value=msg,
                        inline=False
                    )
                    if not c.get("check"):
                        embed.color = Color.red()

                return await ctx.respond(embed=embed)
            except ObjectDoesNotExist:
                return await ctx.respond("Error Processing Filters")

        except EveCharacter.DoesNotExist:
            embed.colour = Color.red()

            embed.description = (
                "Character **{character_name}** does not exist in our Auth system"
            ).format(character_name=character)

            return await ctx.respond(embed=embed)
        except Group.DoesNotExist:
            embed.colour = Color.red()

            embed.description = (
                "Group **{group_name}** does not exist in our Auth system"
            ).format(group_name=group)

            return await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(GroupCheck(bot))
