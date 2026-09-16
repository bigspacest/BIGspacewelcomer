import json
import os
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "welcomer.json"

class Welcomer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config: dict[str, dict] = {}
        self._ensure_data_dir()
        self._load_config()

    def _ensure_data_dir(self) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        if not DATA_FILE.exists():
            DATA_FILE.write_text("{}", encoding="utf-8")

    def _load_config(self) -> None:
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self.config = {}
            self._save_config()

    def _save_config(self) -> None:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def _get_guild_config(self, guild_id: int) -> Optional[dict]:
        return self.config.get(str(guild_id))

    def _format_message(self, template: str, member: discord.Member) -> str:
        """Replace placeholders with real values."""
        return (
            template
            .replace("{user}", member.mention)
            .replace("{server}", member.guild.name)
            .replace("{member-count}", str(member.guild.member_count))
        )

    @app_commands.command(
        name="welcomer-setup",
        description="Configure the welcome message for this server"
    )
    @app_commands.describe(
        channel="The channel where welcome messages will be sent",
        message="Welcome message. Available variables: {user} {server} {member-count}"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def welcomer_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True
            )
            return

        # Validaciones básicas
        if len(message) > 2000:
            await interaction.response.send_message(
                "Message cannot exceed 2000 characters.",
                ephemeral=True
            )
            return

        # Guardar configuración
        guild_id = str(interaction.guild.id)
        self.config[guild_id] = {
            "channel_id": channel.id,
            "message": message
        }
        self._save_config()

        # Preview del mensaje
        preview = self._format_message(message, interaction.user)  # type: ignore

        embed = discord.Embed(
            title="Welcome system configured",
            color=discord.Color.green(),
            description=f"Welcome messages will be sent to {channel.mention}"
        )
        embed.add_field(name="Message template", value=f"```{message}```", inline=False)
        embed.add_field(name="Preview", value=preview[:1024], inline=False)
        embed.set_footer(text="Variables: {user} {server} {member-count}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @welcomer_setup.error
    async def welcomer_setup_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You need **Administrator** permission to use this command.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"An error occurred: {str(error)}",
                ephemeral=True
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return  # opcional: ignorar bots

        guild_config = self._get_guild_config(member.guild.id)
        if not guild_config:
            return

        channel_id = guild_config.get("channel_id")
        template = guild_config.get("message")
        if not channel_id or not template:
            return

        channel = member.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            formatted = self._format_message(template, member)
            await channel.send(formatted)
        except discord.Forbidden:
            # El bot no tiene permisos para hablar en ese canal
            print(f"[Welcomer] Missing permissions in channel {channel_id} (guild {member.guild.id})")
        except Exception as e:
            print(f"[Welcomer] Error sending welcome message: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Welcomer(bot))
