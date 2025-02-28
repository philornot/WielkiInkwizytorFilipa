# commands.py
import logging
import os
import traceback

import discord
from discord import app_commands

from bot_config import get_channel_id, set_channel_id, set_update_interval, get_update_interval
from discord_embeds import create_help_embed, create_error_embed
from message_updater import update_bugs_message
from reports import generate_on_demand_report

logger = logging.getLogger('jira-discord-bot')


def register_commands(tree):
    """
    Rejestruje wszystkie komendy slash dla bota.

    Args:
        tree (app_commands.CommandTree): Drzewo komend bota
    """
    try:
        logger.info("Rejestrowanie komend slash...")

        @tree.command(name="refresh", description="Odśwież listę bugów z Jiry")
        async def refresh_bugs(interaction: discord.Interaction):
            try:
                logger.info(f"Komenda /refresh wywołana przez {interaction.user.name} (ID: {interaction.user.id})")
                await interaction.response.defer(ephemeral=True)

                await update_bugs_message(interaction.client)
                await interaction.followup.send("✅ Lista bugów została zaktualizowana!", ephemeral=True)
                logger.info("Komendy /refresh wykonana pomyślnie")
            except Exception as e:
                logger.error(f"Błąd podczas odświeżania bugów: {e}")
                logger.error(traceback.format_exc())
                await interaction.followup.send(f"❌ Wystąpił błąd podczas aktualizacji bugów: {str(e)}", ephemeral=True)

        @tree.command(name="setbugschannel", description="Ustaw kanał do wyświetlania bugów")
        @app_commands.describe(channel="Kanał, na którym mają być wyświetlane bugi")
        async def set_bugs_channel(interaction: discord.Interaction, channel: discord.TextChannel = None):
            try:
                logger.info(
                    f"Komenda /setbugschannel wywołana przez {interaction.user.name} (ID: {interaction.user.id})")

                if not interaction.user.guild_permissions.administrator:
                    logger.warning(
                        f"Użytkownik {interaction.user.name} próbował ustawić kanał bugów bez uprawnień administratora")
                    await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
                    return

                await interaction.response.defer(ephemeral=True)

                if channel is None:
                    channel = interaction.channel

                old_channel_id = get_channel_id('bugs')
                logger.info(f"Zmiana kanału bugów z ID {old_channel_id} na ID {channel.id} ({channel.name})")

                if set_channel_id('bugs', channel.id):
                    await interaction.followup.send(
                        f"✅ Kanał do raportowania bugów został zmieniony na {channel.mention}!",
                        ephemeral=True
                    )
                    await update_bugs_message(interaction.client)
                    logger.info(f"Kanał bugów pomyślnie zmieniony na {channel.name} (ID: {channel.id})")
                else:
                    await interaction.followup.send(
                        "❌ Wystąpił błąd podczas zmiany kanału bugów!",
                        ephemeral=True
                    )
            except Exception as e:
                logger.error(f"Błąd podczas ustawiania kanału bugów: {e}")
                logger.error(traceback.format_exc())
                await interaction.followup.send(f"❌ Wystąpił nieoczekiwany błąd: {str(e)}", ephemeral=True)

        @tree.command(name="setreportschannel", description="Ustaw kanał do wysyłania dziennych raportów")
        @app_commands.describe(channel="Kanał, na którym mają być wysyłane raporty")
        async def set_reports_channel(interaction: discord.Interaction, channel: discord.TextChannel = None):
            try:
                logger.info(
                    f"Komenda /setreportschannel wywołana przez {interaction.user.name} (ID: {interaction.user.id})")

                if not interaction.user.guild_permissions.administrator:
                    logger.warning(
                        f"Użytkownik {interaction.user.name} próbował ustawić kanał raportów bez uprawnień administratora")
                    await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
                    return

                await interaction.response.defer(ephemeral=True)

                if channel is None:
                    channel = interaction.channel

                old_channel_id = get_channel_id('reports')
                logger.info(f"Zmiana kanału raportów z ID {old_channel_id} na ID {channel.id} ({channel.name})")

                if set_channel_id('reports', channel.id):
                    await interaction.followup.send(
                        f"✅ Kanał do wysyłania raportów został zmieniony na {channel.mention}!",
                        ephemeral=True
                    )
                    logger.info(f"Kanał raportów pomyślnie zmieniony na {channel.name} (ID: {channel.id})")
                else:
                    await interaction.followup.send(
                        "❌ Wystąpił błąd podczas zmiany kanału raportów!",
                        ephemeral=True
                    )
            except Exception as e:
                logger.error(f"Błąd podczas ustawiania kanału raportów: {e}")
                logger.error(traceback.format_exc())
                await interaction.followup.send(f"❌ Wystąpił nieoczekiwany błąd: {str(e)}", ephemeral=True)

        @tree.command(name="setreportschannelid", description="Ustaw kanał do wysyłania raportów poprzez ID")
        @app_commands.describe(channel_id="ID kanału, na którym mają być wysyłane raporty")
        async def set_reports_channel_id(interaction: discord.Interaction, channel_id: str):
            try:
                logger.info(
                    f"Komenda /setreportschannelid wywołana przez {interaction.user.name} (ID: {interaction.user.id})")

                if not interaction.user.guild_permissions.administrator:
                    logger.warning(
                        f"Użytkownik {interaction.user.name} próbował ustawić kanał raportów bez uprawnień administratora")
                    await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
                    return

                try:
                    channel_id_int = int(channel_id.strip())
                    channel = interaction.client.get_channel(channel_id_int)

                    if channel is None:
                        logger.warning(f"Nie znaleziono kanału o ID {channel_id}")
                        await interaction.response.send_message(
                            f"❌ Nie znaleziono kanału o ID {channel_id}. Upewnij się, że ID jest poprawne i bot ma dostęp do tego kanału.",
                            ephemeral=True)
                        return

                    old_channel_id = get_channel_id('reports')
                    logger.info(f"Zmiana kanału raportów z ID {old_channel_id} na ID {channel_id_int} ({channel.name})")

                    if set_channel_id('reports', channel_id_int):
                        await interaction.response.send_message(
                            f"✅ Kanał do wysyłania raportów został zmieniony na {channel.mention} (ID: {channel_id})!",
                            ephemeral=True
                        )
                        logger.info(f"Kanał raportów pomyślnie zmieniony na {channel.name} (ID: {channel_id_int})")
                    else:
                        await interaction.response.send_message(
                            "❌ Wystąpił błąd podczas zmiany kanału raportów!",
                            ephemeral=True
                        )
                except ValueError:
                    logger.warning(f"Podano nieprawidłowe ID kanału: {channel_id}")
                    await interaction.response.send_message("❌ Podane ID kanału nie jest poprawną liczbą!",
                                                            ephemeral=True)

            except Exception as e:
                logger.error(f"Błąd podczas ustawiania ID kanału raportów: {e}")
                logger.error(traceback.format_exc())
                await interaction.response.send_message(f"❌ Wystąpił błąd: {str(e)}", ephemeral=True)

        @tree.command(name="setinterval", description="Ustaw interwał aktualizacji bugów (w minutach)")
        @app_commands.describe(minutes="Czas w minutach pomiędzy aktualizacjami")
        async def set_interval(interaction: discord.Interaction, minutes: int):
            try:
                logger.info(
                    f"Komenda /setinterval wywołana przez {interaction.user.name} (ID: {interaction.user.id}) z wartością {minutes} minut")

                if not interaction.user.guild_permissions.administrator:
                    logger.warning(
                        f"Użytkownik {interaction.user.name} próbował zmienić interwał bez uprawnień administratora")
                    await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
                    return

                if minutes < 1:
                    logger.warning(f"Próba ustawienia zbyt małego interwału: {minutes} minut")
                    await interaction.response.send_message("❌ Interwał musi być większy niż 1 minuta!", ephemeral=True)
                    return

                old_interval = get_update_interval()
                new_interval = minutes * 60
                logger.info(f"Zmiana interwału aktualizacji z {old_interval} sekund na {new_interval} sekund")

                if set_update_interval(new_interval):
                    await interaction.response.send_message(
                        f"✅ Interwał aktualizacji bugów został ustawiony na {minutes} minut.",
                        ephemeral=True
                    )
                    logger.info(f"Interwał aktualizacji pomyślnie zmieniony na {minutes} minut")
                else:
                    await interaction.response.send_message(
                        "❌ Wystąpił błąd podczas zmiany interwału aktualizacji!",
                        ephemeral=True
                    )
            except Exception as e:
                logger.error(f"Błąd podczas ustawiania interwału aktualizacji: {e}")
                logger.error(traceback.format_exc())
                await interaction.response.send_message(f"❌ Wystąpił nieoczekiwany błąd: {str(e)}", ephemeral=True)

        @tree.command(name="generate_report", description="Wygeneruj raport ukończonych zadań na żądanie")
        async def generate_report(interaction: discord.Interaction):
            try:
                logger.info(
                    f"Komenda /generate_report wywołana przez {interaction.user.name} (ID: {interaction.user.id})")
                await interaction.response.defer()

                report_embed = await generate_on_demand_report()
                await interaction.followup.send(embed=report_embed)
                logger.info("Raport wygenerowany i wysłany pomyślnie")
            except Exception as e:
                logger.error(f"Błąd podczas generowania raportu na żądanie: {e}")
                logger.error(traceback.format_exc())
                error_embed = create_error_embed(
                    "Błąd raportu",
                    f"Wystąpił błąd podczas generowania raportu: {str(e)}"
                )
                await interaction.followup.send(embed=error_embed)

        @tree.command(name="help", description="Wyświetla informacje o komendach bota")
        async def help_command(interaction: discord.Interaction):
            try:
                logger.info(f"Komenda /help wywołana przez {interaction.user.name} (ID: {interaction.user.id})")
                embed = create_help_embed()
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info("Pomoc wyświetlona pomyślnie")
            except Exception as e:
                logger.error(f"Błąd podczas wyświetlania pomocy: {e}")
                logger.error(traceback.format_exc())
                await interaction.response.send_message(
                    f"❌ Wystąpił błąd podczas wyświetlania pomocy: {str(e)}",
                    ephemeral=True
                )

        logger.info("Komendy slash zarejestrowane pomyślnie")

    except Exception as e:
        logger.error(f"Błąd podczas rejestrowania komend slash: {e}")
        logger.error(traceback.format_exc())