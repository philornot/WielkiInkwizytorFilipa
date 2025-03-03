# commands.py
import logging
import traceback

import discord
from discord import app_commands

from bot_config import get_channel_id, set_channel_id, set_update_interval, get_update_interval
from discord_embeds import create_help_embed, create_error_embed
from message_updater import update_bugs_message
from reports import generate_on_demand_report

logger = logging.getLogger('WielkiInkwizytorFilipa')


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

                try:
                    # Natychmiastowa odpowiedź zamiast defer
                    await interaction.response.send_message("⏳ Odświeżanie listy bugów...", ephemeral=True)
                except discord.errors.NotFound:
                    logger.warning("Interakcja wygasła, nie można odpowiedzieć na /refresh")
                    return

                try:
                    success = await update_bugs_message(interaction.client)
                    if success:
                        await interaction.edit_original_response(content="✅ Lista bugów została zaktualizowana!")
                        logger.info("Komenda /refresh wykonana pomyślnie")
                    else:
                        await interaction.edit_original_response(
                            content="❌ Wystąpił błąd podczas aktualizacji listy bugów")
                except discord.errors.NotFound:
                    logger.warning("Nie można zaktualizować odpowiedzi - webhook nie istnieje")
                except Exception as edit_error:
                    logger.error(f"Błąd podczas edycji odpowiedzi: {edit_error}")
            except Exception as e:
                logger.error(f"Błąd podczas odświeżania bugów: {e}")
                logger.error(traceback.format_exc())
                try:
                    # Próba odpowiedzi w przypadku błędu
                    if interaction.response.is_done():
                        await interaction.edit_original_response(content=f"❌ Wystąpił błąd: {str(e)}")
                    else:
                        await interaction.response.send_message(f"❌ Wystąpił błąd: {str(e)}", ephemeral=True)
                except discord.errors.NotFound:
                    logger.warning("Nie można zaktualizować odpowiedzi po błędzie - interakcja wygasła")
                except Exception as resp_error:
                    logger.error(f"Błąd podczas wysyłania informacji o błędzie: {resp_error}")

        @tree.command(name="setbugschannel", description="Ustaw kanał do wyświetlania bugów")
        @app_commands.describe(channel="Kanał, na którym mają być wyświetlane bugi")
        async def set_bugs_channel(interaction: discord.Interaction, channel: discord.TextChannel = None):
            try:
                logger.info(
                    f"Komenda /setbugschannel wywołana przez {interaction.user.name} (ID: {interaction.user.id})")

                # Sprawdź uprawnienia
                if not interaction.user.guild_permissions.administrator:
                    try:
                        await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
                    except discord.errors.NotFound:
                        logger.warning("Interakcja wygasła, nie można odpowiedzieć na /setbugschannel")
                    return

                try:
                    # Użyj send_message zamiast defer, aby natychmiast potwierdzić interakcję
                    await interaction.response.send_message("⏳ Trwa zmiana kanału bugów...", ephemeral=True)
                except discord.errors.NotFound:
                    logger.warning("Interakcja wygasła, nie można odpowiedzieć na /setbugschannel")
                    return

                # Jeśli nie podano kanału, użyj bieżącego
                if channel is None:
                    channel = interaction.channel

                old_channel_id = get_channel_id('bugs')
                logger.info(f"Zmiana kanału bugów z ID {old_channel_id} na ID {channel.id} ({channel.name})")

                # Zaktualizuj kanał
                if set_channel_id('bugs', channel.id):
                    try:
                        await interaction.edit_original_response(
                            content=f"✅ Kanał do raportowania bugów został zmieniony na {channel.mention}!"
                        )
                        await update_bugs_message(interaction.client)
                        logger.info(f"Kanał bugów pomyślnie zmieniony na {channel.name} (ID: {channel.id})")
                    except discord.errors.NotFound:
                        logger.warning("Nie można zaktualizować odpowiedzi - webhook nie istnieje")
                    except Exception as edit_error:
                        logger.error(f"Błąd podczas edycji odpowiedzi: {edit_error}")
                else:
                    try:
                        await interaction.edit_original_response(
                            content="❌ Wystąpił błąd podczas zmiany kanału bugów!"
                        )
                    except discord.errors.NotFound:
                        logger.warning("Nie można zaktualizować odpowiedzi po błędzie - webhook nie istnieje")
                    except Exception as edit_error:
                        logger.error(f"Błąd podczas edycji odpowiedzi po błędzie: {edit_error}")
            except Exception as e:
                logger.error(f"Błąd podczas ustawiania kanału bugów: {e}")
                logger.error(traceback.format_exc())
                try:
                    if interaction.response.is_done():
                        await interaction.edit_original_response(content=f"❌ Wystąpił nieoczekiwany błąd: {str(e)}")
                    else:
                        await interaction.response.send_message(f"❌ Wystąpił nieoczekiwany błąd: {str(e)}",
                                                                ephemeral=True)
                except discord.errors.NotFound:
                    logger.warning("Nie można odpowiedzieć po błędzie - interakcja wygasła")
                except Exception:
                    pass

        @tree.command(name="setreportschannel", description="Ustaw kanał do wysyłania dziennych raportów")
        @app_commands.describe(channel="Kanał, na którym mają być wysyłane raporty")
        async def set_reports_channel(interaction: discord.Interaction, channel: discord.TextChannel = None):
            try:
                logger.info(
                    f"Komenda /setreportschannel wywołana przez {interaction.user.name} (ID: {interaction.user.id})")

                # Sprawdź uprawnienia
                if not interaction.user.guild_permissions.administrator:
                    try:
                        await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
                    except discord.errors.NotFound:
                        logger.warning("Interakcja wygasła, nie można odpowiedzieć na /setreportschannel")
                    return

                try:
                    await interaction.response.send_message("⏳ Trwa zmiana kanału raportów...", ephemeral=True)
                except discord.errors.NotFound:
                    logger.warning("Interakcja wygasła, nie można odpowiedzieć na /setreportschannel")
                    return

                # Jeśli nie podano kanału, użyj bieżącego
                if channel is None:
                    channel = interaction.channel

                old_channel_id = get_channel_id('reports')
                logger.info(f"Zmiana kanału raportów z ID {old_channel_id} na ID {channel.id} ({channel.name})")

                # Zaktualizuj kanał
                if set_channel_id('reports', channel.id):
                    try:
                        await interaction.edit_original_response(
                            content=f"✅ Kanał do wysyłania raportów został zmieniony na {channel.mention}!"
                        )
                        logger.info(f"Kanał raportów pomyślnie zmieniony na {channel.name} (ID: {channel.id})")
                    except discord.errors.NotFound:
                        logger.warning("Nie można zaktualizować odpowiedzi - webhook nie istnieje")
                    except Exception as edit_error:
                        logger.error(f"Błąd podczas edycji odpowiedzi: {edit_error}")
                else:
                    try:
                        await interaction.edit_original_response(
                            content="❌ Wystąpił błąd podczas zmiany kanału raportów!"
                        )
                    except discord.errors.NotFound:
                        logger.warning("Nie można zaktualizować odpowiedzi po błędzie - webhook nie istnieje")
                    except Exception as edit_error:
                        logger.error(f"Błąd podczas edycji odpowiedzi po błędzie: {edit_error}")
            except Exception as e:
                logger.error(f"Błąd podczas ustawiania kanału raportów: {e}")
                logger.error(traceback.format_exc())
                try:
                    if interaction.response.is_done():
                        await interaction.edit_original_response(content=f"❌ Wystąpił nieoczekiwany błąd: {str(e)}")
                    else:
                        await interaction.response.send_message(f"❌ Wystąpił nieoczekiwany błąd: {str(e)}",
                                                                ephemeral=True)
                except discord.errors.NotFound:
                    logger.warning("Nie można odpowiedzieć po błędzie - interakcja wygasła")
                except Exception:
                    pass

        @tree.command(name="setinterval", description="Ustaw interwał aktualizacji bugów (w minutach)")
        @app_commands.describe(minutes="Czas w minutach pomiędzy aktualizacjami")
        async def set_interval(interaction: discord.Interaction, minutes: int):
            try:
                logger.info(
                    f"Komenda /setinterval wywołana przez {interaction.user.name} (ID: {interaction.user.id}) z wartością {minutes} minut")

                # Sprawdź uprawnienia
                if not interaction.user.guild_permissions.administrator:
                    try:
                        await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
                    except discord.errors.NotFound:
                        logger.warning("Interakcja wygasła, nie można odpowiedzieć na /setinterval")
                    return

                # Sprawdź czy wartość jest prawidłowa
                if minutes < 1:
                    try:
                        await interaction.response.send_message("❌ Interwał musi być większy niż 1 minuta!",
                                                                ephemeral=True)
                    except discord.errors.NotFound:
                        logger.warning("Interakcja wygasła, nie można odpowiedzieć na /setinterval")
                    return

                try:
                    await interaction.response.send_message(f"⏳ Ustawianie interwału na {minutes} minut...",
                                                            ephemeral=True)
                except discord.errors.NotFound:
                    logger.warning("Interakcja wygasła, nie można odpowiedzieć na /setinterval")
                    return

                old_interval = get_update_interval()
                new_interval = minutes * 60
                logger.info(f"Zmiana interwału aktualizacji z {old_interval} sekund na {new_interval} sekund")

                # Zaktualizuj interwał
                if set_update_interval(new_interval):
                    try:
                        await interaction.edit_original_response(
                            content=f"✅ Interwał aktualizacji bugów został ustawiony na {minutes} minut."
                        )
                        logger.info(f"Interwał aktualizacji pomyślnie zmieniony na {minutes} minut")
                    except discord.errors.NotFound:
                        logger.warning("Nie można zaktualizować odpowiedzi - webhook nie istnieje")
                else:
                    try:
                        await interaction.edit_original_response(
                            content="❌ Wystąpił błąd podczas zmiany interwału aktualizacji!"
                        )
                    except discord.errors.NotFound:
                        logger.warning("Nie można zaktualizować odpowiedzi po błędzie - webhook nie istnieje")
            except Exception as e:
                logger.error(f"Błąd podczas ustawiania interwału aktualizacji: {e}")
                logger.error(traceback.format_exc())
                try:
                    if interaction.response.is_done():
                        await interaction.edit_original_response(content=f"❌ Wystąpił nieoczekiwany błąd: {str(e)}")
                    else:
                        await interaction.response.send_message(f"❌ Wystąpił nieoczekiwany błąd: {str(e)}",
                                                                ephemeral=True)
                except discord.errors.NotFound:
                    logger.warning("Nie można odpowiedzieć po błędzie - interakcja wygasła")
                except Exception:
                    pass

        @tree.command(name="generate_report", description="Wygeneruj raport ukończonych zadań na żądanie")
        async def generate_report(interaction: discord.Interaction):
            try:
                logger.info(
                    f"Komenda /generate_report wywołana przez {interaction.user.name} (ID: {interaction.user.id})")

                try:
                    await interaction.response.send_message("⏳ Generowanie raportu...", ephemeral=False)
                except discord.errors.NotFound:
                    logger.warning("Interakcja wygasła, nie można odpowiedzieć na /generate_report")
                    return

                # Generowanie raportu
                try:
                    report_embed = await generate_on_demand_report()
                    await interaction.edit_original_response(content=None, embed=report_embed)
                    logger.info("Raport wygenerowany i wysłany pomyślnie")
                except discord.errors.NotFound:
                    logger.warning("Nie można zaktualizować odpowiedzi - webhook nie istnieje")
                except Exception as report_error:
                    logger.error(f"Błąd podczas generowania raportu: {report_error}")
                    logger.error(traceback.format_exc())
                    error_embed = create_error_embed(
                        "Błąd raportu",
                        f"Wystąpił błąd podczas generowania raportu: {str(report_error)}"
                    )
                    try:
                        await interaction.edit_original_response(content=None, embed=error_embed)
                    except discord.errors.NotFound:
                        logger.warning("Nie można zaktualizować odpowiedzi po błędzie - webhook nie istnieje")
            except Exception as e:
                logger.error(f"Błąd podczas generowania raportu na żądanie: {e}")
                logger.error(traceback.format_exc())
                try:
                    if interaction.response.is_done():
                        error_embed = create_error_embed(
                            "Błąd raportu",
                            f"Wystąpił błąd podczas generowania raportu: {str(e)}"
                        )
                        await interaction.edit_original_response(content=None, embed=error_embed)
                    else:
                        await interaction.response.send_message(f"❌ Wystąpił błąd: {str(e)}", ephemeral=True)
                except discord.errors.NotFound:
                    logger.warning("Nie można odpowiedzieć po błędzie - interakcja wygasła")
                except Exception:
                    pass

        @tree.command(name="help", description="Wyświetla informacje o komendach bota")
        async def help_command(interaction: discord.Interaction):
            try:
                logger.info(f"Komenda /help wywołana przez {interaction.user.name} (ID: {interaction.user.id})")

                try:
                    embed = create_help_embed()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    logger.info("Pomoc wyświetlona pomyślnie")
                except discord.errors.NotFound:
                    logger.warning("Interakcja wygasła, nie można odpowiedzieć na /help")
                except Exception as resp_error:
                    logger.error(f"Błąd podczas wysyłania pomocy: {resp_error}")
                    logger.error(traceback.format_exc())
                    # Próba ponownej odpowiedzi
                    try:
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                f"❌ Wystąpił błąd podczas wyświetlania pomocy: {str(resp_error)}",
                                ephemeral=True
                            )
                    except discord.errors.NotFound:
                        logger.warning("Nie można odpowiedzieć po ponownej próbie - interakcja wygasła")
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Błąd podczas wyświetlania pomocy: {e}")
                logger.error(traceback.format_exc())
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            f"❌ Wystąpił błąd podczas wyświetlania pomocy: {str(e)}",
                            ephemeral=True
                        )
                except discord.errors.NotFound:
                    logger.warning("Nie można odpowiedzieć po błędzie - interakcja wygasła")
                except Exception:
                    pass

        logger.info("Komendy slash zarejestrowane pomyślnie")

    except Exception as e:
        logger.error(f"Błąd podczas rejestrowania komend slash: {e}")
        logger.error(traceback.format_exc())

    @tree.command(name="leaderboard", description="Wyświetla tablicę wyników zespołu")
    @app_commands.describe(days="Liczba dni wstecz do analizy (domyślnie 30)")
    async def show_leaderboard(interaction: discord.Interaction, days: int = 30):
        try:
            logger.info(
                f"Komenda /leaderboard wywołana przez {interaction.user.name} (ID: {interaction.user.id}) z parametrem {days} dni")

            try:
                await interaction.response.send_message("⏳ Generowanie tablicy wyników...", ephemeral=False)
            except discord.errors.NotFound:
                logger.warning("Interakcja wygasła, nie można odpowiedzieć na /leaderboard")
                return

            # Import funkcji generującej tablicę wyników
            from leaderboard import generate_leaderboard

            # Generowanie tablicy wyników
            try:
                leaderboard_embed = await generate_leaderboard(days=days)
                await interaction.edit_original_response(content=None, embed=leaderboard_embed)
                logger.info("Tablica wyników wygenerowana i wysłana pomyślnie")
            except discord.errors.NotFound:
                logger.warning("Nie można zaktualizować odpowiedzi - webhook nie istnieje")
            except Exception as leaderboard_error:
                logger.error(f"Błąd podczas generowania tablicy wyników: {leaderboard_error}")
                logger.error(traceback.format_exc())
                error_embed = create_error_embed(
                    "Błąd tablicy wyników",
                    f"Wystąpił błąd podczas generowania tablicy wyników: {str(leaderboard_error)}"
                )
                try:
                    await interaction.edit_original_response(content=None, embed=error_embed)
                except discord.errors.NotFound:
                    logger.warning("Nie można zaktualizować odpowiedzi po błędzie - webhook nie istnieje")

        except Exception as e:
            logger.error(f"Błąd podczas obsługi komendy leaderboard: {e}")
            logger.error(traceback.format_exc())
            try:
                if interaction.response.is_done():
                    error_embed = create_error_embed(
                        "Błąd tablicy wyników",
                        f"Wystąpił błąd podczas generowania tablicy wyników: {str(e)}"
                    )
                    await interaction.edit_original_response(content=None, embed=error_embed)
                else:
                    await interaction.response.send_message(f"❌ Wystąpił błąd: {str(e)}", ephemeral=True)
            except discord.errors.NotFound:
                logger.warning("Nie można odpowiedzieć po błędzie - interakcja wygasła")
            except Exception:
                pass
