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

        @tree.command(name="stan", description="Wyświetla szczegółowe informacje o stanie bota")
        async def status_command(interaction: discord.Interaction):
            try:
                logger.info(f"Komenda /stan wywołana przez {interaction.user.name} (ID: {interaction.user.id})")

                from bot_config import get_bot_status
                status = get_bot_status()

                # Przygotowanie kolorów w zależności od stanu
                color = discord.Color.green()

                # Jeśli jedna z głównych funkcji jest wyłączona, użyj żółtego koloru
                if not status["reports_enabled"] or not status["leaderboard_enabled"]:
                    color = discord.Color.yellow()

                embed = discord.Embed(
                    title="📊 Stan bota Wielki Inkwizytor Filipa",
                    description="Szczegółowe informacje o konfiguracji i stanie bota",
                    color=color
                )

                # Kanały
                embed.add_field(
                    name="🔧 Kanały",
                    value=(
                        f"🐞 **Bugi**: <#{status['bugs_channel_id']}>\n"
                        f"📝 **Raporty**: <#{status['reports_channel_id']}>\n"
                        f"🏆 **Leaderboard**: <#{status['leaderboard_channel_id']}>"
                    ),
                    inline=False
                )

                # Funkcje
                embed.add_field(
                    name="⚙️ Funkcje",
                    value=(
                        f"🔄 **Interwał aktualizacji bugów**: {status['update_interval']} sekund\n"
                        f"📝 **Raporty**: {'✅ Włączone' if status['reports_enabled'] else '❌ Wyłączone'}\n"
                        f"🏆 **Leaderboard**: {'✅ Włączone' if status['leaderboard_enabled'] else '❌ Wyłączone'}"
                    ),
                    inline=False
                )

                # Harmonogram
                embed.add_field(
                    name="⏰ Harmonogram",
                    value=(
                        f"📝 **Czas raportów**: {status['report_time']}\n"
                        f"🏆 **Czas leaderboardu**: {status['leaderboard_time']}"
                    ),
                    inline=False
                )

                # Jira
                embed.add_field(
                    name="🔗 Jira",
                    value=(
                        f"🌐 **Serwer**: {status['jira_server']}\n"
                        f"📂 **Projekt**: {status['jira_project']}\n"
                        f"🕒 **Strefa czasowa**: {status['timezone']}"
                    ),
                    inline=False
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info("Informacje o stanie bota wyświetlone pomyślnie")

            except Exception as e:
                logger.error(f"Błąd podczas wyświetlania stanu bota: {e}")
                logger.error(traceback.format_exc())
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            f"❌ Wystąpił błąd podczas wyświetlania stanu bota: {str(e)}",
                            ephemeral=True
                        )
                except discord.errors.NotFound:
                    logger.warning("Nie można odpowiedzieć po błędzie - interakcja wygasła")
                except Exception:
                    pass

        @tree.command(name="wlacz_raporty", description="Włącza wysyłanie raportów według harmonogramu")
        @app_commands.default_permissions(administrator=True)
        async def enable_reports(interaction: discord.Interaction):
            try:
                logger.info(
                    f"Komenda /wlacz_raporty wywołana przez {interaction.user.name} (ID: {interaction.user.id})")

                # Sprawdź uprawnienia
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
                    return

                from bot_config import is_reports_enabled, set_reports_enabled

                # Sprawdź obecny stan
                if is_reports_enabled():
                    await interaction.response.send_message("ℹ️ Raporty są już włączone!", ephemeral=True)
                    return

                # Włącz raporty
                success = set_reports_enabled(True)

                if success:
                    await interaction.response.send_message(
                        "✅ Raporty zostały włączone! Będą wysyłane zgodnie z harmonogramem.", ephemeral=True)
                    logger.info("Raporty zostały włączone przez użytkownika")
                else:
                    await interaction.response.send_message("❌ Wystąpił błąd podczas włączania raportów.",
                                                            ephemeral=True)
                    logger.error("Błąd podczas włączania raportów")

            except Exception as e:
                logger.error(f"Błąd podczas włączania raportów: {e}")
                logger.error(traceback.format_exc())
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            f"❌ Wystąpił błąd: {str(e)}",
                            ephemeral=True
                        )
                except discord.errors.NotFound:
                    logger.warning("Nie można odpowiedzieć po błędzie - interakcja wygasła")
                except Exception:
                    pass

        @tree.command(name="wylacz_raporty", description="Wyłącza wysyłanie raportów")
        @app_commands.default_permissions(administrator=True)
        async def disable_reports(interaction: discord.Interaction):
            try:
                logger.info(
                    f"Komenda /wylacz_raporty wywołana przez {interaction.user.name} (ID: {interaction.user.id})")

                # Sprawdź uprawnienia
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
                    return

                from bot_config import is_reports_enabled, set_reports_enabled

                # Sprawdź obecny stan
                if not is_reports_enabled():
                    await interaction.response.send_message("ℹ️ Raporty są już wyłączone!", ephemeral=True)
                    return

                # Wyłącz raporty
                success = set_reports_enabled(False)

                if success:
                    await interaction.response.send_message(
                        "✅ Raporty zostały wyłączone. Nie będą automatycznie wysyłane.", ephemeral=True)
                    logger.info("Raporty zostały wyłączone przez użytkownika")
                else:
                    await interaction.response.send_message("❌ Wystąpił błąd podczas wyłączania raportów.",
                                                            ephemeral=True)
                    logger.error("Błąd podczas wyłączania raportów")

            except Exception as e:
                logger.error(f"Błąd podczas wyłączania raportów: {e}")
                logger.error(traceback.format_exc())
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            f"❌ Wystąpił błąd: {str(e)}",
                            ephemeral=True
                        )
                except discord.errors.NotFound:
                    logger.warning("Nie można odpowiedzieć po błędzie - interakcja wygasła")
                except Exception:
                    pass

        @tree.command(name="wlacz_leaderboard", description="Włącza wysyłanie tablic wyników według harmonogramu")
        @app_commands.default_permissions(administrator=True)
        async def enable_leaderboard(interaction: discord.Interaction):
            try:
                logger.info(
                    f"Komenda /wlacz_leaderboard wywołana przez {interaction.user.name} (ID: {interaction.user.id})")

                # Sprawdź uprawnienia
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
                    return

                from bot_config import is_leaderboard_enabled, set_leaderboard_enabled

                # Sprawdź obecny stan
                if is_leaderboard_enabled():
                    await interaction.response.send_message("ℹ️ Tablica wyników jest już włączona!", ephemeral=True)
                    return

                # Włącz tablicę
                success = set_leaderboard_enabled(True)

                if success:
                    await interaction.response.send_message(
                        "✅ Tablica wyników została włączona! Będzie wysyłana zgodnie z harmonogramem.", ephemeral=True)
                    logger.info("Tablica wyników została włączona przez użytkownika")
                else:
                    await interaction.response.send_message("❌ Wystąpił błąd podczas włączania tablicy wyników.",
                                                            ephemeral=True)
                    logger.error("Błąd podczas włączania tablicy wyników")

            except Exception as e:
                logger.error(f"Błąd podczas włączania tablicy wyników: {e}")
                logger.error(traceback.format_exc())
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            f"❌ Wystąpił błąd: {str(e)}",
                            ephemeral=True
                        )
                except discord.errors.NotFound:
                    logger.warning("Nie można odpowiedzieć po błędzie - interakcja wygasła")
                except Exception:
                    pass

        @tree.command(name="wylacz_leaderboard", description="Wyłącza wysyłanie tablic wyników")
        @app_commands.default_permissions(administrator=True)
        async def disable_leaderboard(interaction: discord.Interaction):
            try:
                logger.info(
                    f"Komenda /wylacz_leaderboard wywołana przez {interaction.user.name} (ID: {interaction.user.id})")

                # Sprawdź uprawnienia
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
                    return

                from bot_config import is_leaderboard_enabled, set_leaderboard_enabled

                # Sprawdź obecny stan
                if not is_leaderboard_enabled():
                    await interaction.response.send_message("ℹ️ Tablica wyników jest już wyłączona!", ephemeral=True)
                    return

                # Wyłącz tablicę
                success = set_leaderboard_enabled(False)

                if success:
                    await interaction.response.send_message(
                        "✅ Tablica wyników została wyłączona. Nie będzie automatycznie wysyłana.", ephemeral=True)
                    logger.info("Tablica wyników została wyłączona przez użytkownika")
                else:
                    await interaction.response.send_message("❌ Wystąpił błąd podczas wyłączania tablicy wyników.",
                                                            ephemeral=True)
                    logger.error("Błąd podczas wyłączania tablicy wyników")

            except Exception as e:
                logger.error(f"Błąd podczas wyłączania tablicy wyników: {e}")
                logger.error(traceback.format_exc())
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            f"❌ Wystąpił błąd: {str(e)}",
                            ephemeral=True
                        )
                except discord.errors.NotFound:
                    logger.warning("Nie można odpowiedzieć po błędzie - interakcja wygasła")
                except Exception:
                    pass

        @tree.command(name="konfiguracja_raportu", description="Konfiguruje kanał i czas wysyłania raportów")
        @app_commands.describe(
            kanal="Kanał, na którym mają być wysyłane raporty",
            godzina="Godzina wysyłania raportu (0-23)",
            minuta="Minuta wysyłania raportu (0-59)"
        )
        @app_commands.default_permissions(administrator=True)
        async def configure_report(
                interaction: discord.Interaction,
                kanal: discord.TextChannel = None,
                godzina: int = None,
                minuta: int = None
        ):
            try:
                logger.info(
                    f"Komenda /konfiguracja_raportu wywołana przez {interaction.user.name} (ID: {interaction.user.id})")

                # Sprawdź uprawnienia
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
                    return

                from bot_config import get_channel_id, set_channel_id, get_report_time, set_report_time

                changes_made = False
                update_text = []

                # Pobierz aktualne ustawienia
                current_channel_id = get_channel_id('reports')
                current_hour, current_minute = get_report_time()

                # Aktualizacja kanału jeśli podano
                if kanal is not None:
                    if set_channel_id('reports', kanal.id):
                        update_text.append(f"✅ Kanał raportów zmieniony na {kanal.mention}")
                        changes_made = True
                    else:
                        update_text.append("❌ Nie udało się zmienić kanału raportów")

                # Aktualizacja czasu jeśli podano
                if godzina is not None or minuta is not None:
                    # Użyj aktualnych wartości dla niepodanych parametrów
                    new_hour = godzina if godzina is not None else current_hour
                    new_minute = minuta if minuta is not None else current_minute

                    # Walidacja
                    if new_hour < 0 or new_hour > 23:
                        update_text.append(f"❌ Nieprawidłowa godzina: {new_hour} (musi być 0-23)")
                    elif new_minute < 0 or new_minute > 59:
                        update_text.append(f"❌ Nieprawidłowa minuta: {new_minute} (musi być 0-59)")
                    elif set_report_time(new_hour, new_minute):
                        update_text.append(f"✅ Czas raportów zmieniony na {new_hour}:{new_minute:02d}")
                        changes_made = True
                    else:
                        update_text.append("❌ Nie udało się zmienić czasu raportów")

                # Jeśli nie podano żadnych parametrów, wyświetl obecną konfigurację
                if not changes_made and not update_text:
                    channel_mention = f"<#{current_channel_id}>" if current_channel_id else "Nie ustawiono"
                    await interaction.response.send_message(
                        f"ℹ️ Aktualna konfiguracja raportów:\n"
                        f"Kanał: {channel_mention}\n"
                        f"Czas: {current_hour}:{current_minute:02d}",
                        ephemeral=True
                    )
                    return

                # Wyświetl podsumowanie zmian
                await interaction.response.send_message(
                    "📝 Konfiguracja raportów:\n" + "\n".join(update_text),
                    ephemeral=True
                )

                logger.info(f"Zaktualizowano konfigurację raportów: {', '.join(update_text)}")

            except Exception as e:
                logger.error(f"Błąd podczas konfiguracji raportów: {e}")
                logger.error(traceback.format_exc())
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            f"❌ Wystąpił błąd: {str(e)}",
                            ephemeral=True
                        )
                except discord.errors.NotFound:
                    logger.warning("Nie można odpowiedzieć po błędzie - interakcja wygasła")
                except Exception:
                    pass

        @tree.command(name="konfiguracja_leaderboard", description="Konfiguruje kanał i czas wysyłania tablicy wyników")
        @app_commands.describe(
            kanal="Kanał, na którym ma być wysyłana tablica wyników",
            dzien="Dzień tygodnia (0=poniedziałek, 6=niedziela)",
            godzina="Godzina wysyłania (0-23)",
            minuta="Minuta wysyłania (0-59)"
        )
        @app_commands.choices(dzien=[
            app_commands.Choice(name="Poniedziałek", value=0),
            app_commands.Choice(name="Wtorek", value=1),
            app_commands.Choice(name="Środa", value=2),
            app_commands.Choice(name="Czwartek", value=3),
            app_commands.Choice(name="Piątek", value=4),
            app_commands.Choice(name="Sobota", value=5),
            app_commands.Choice(name="Niedziela", value=6),
        ])
        @app_commands.default_permissions(administrator=True)
        async def configure_leaderboard(
                interaction: discord.Interaction,
                kanal: discord.TextChannel = None,
                dzien: int = None,
                godzina: int = None,
                minuta: int = None
        ):
            try:
                logger.info(
                    f"Komenda /konfiguracja_leaderboard wywołana przez {interaction.user.name} (ID: {interaction.user.id})")

                # Sprawdź uprawnienia
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
                    return

                from bot_config import get_channel_id, set_channel_id, get_leaderboard_time, set_leaderboard_time

                changes_made = False
                update_text = []

                # Pobierz aktualne ustawienia
                current_channel_id = get_channel_id('leaderboard')
                current_day, current_hour, current_minute = get_leaderboard_time()

                # Aktualizacja kanału jeśli podano
                if kanal is not None:
                    if set_channel_id('leaderboard', kanal.id):
                        update_text.append(f"✅ Kanał tablicy wyników zmieniony na {kanal.mention}")
                        changes_made = True
                    else:
                        update_text.append("❌ Nie udało się zmienić kanału tablicy wyników")

                # Aktualizacja czasu jeśli podano
                if dzien is not None or godzina is not None or minuta is not None:
                    # Użyj aktualnych wartości dla niepodanych parametrów
                    new_day = dzien if dzien is not None else current_day
                    new_hour = godzina if godzina is not None else current_hour
                    new_minute = minuta if minuta is not None else current_minute

                    # Walidacja
                    if new_day < 0 or new_day > 6:
                        update_text.append(f"❌ Nieprawidłowy dzień: {new_day} (musi być 0-6)")
                    elif new_hour < 0 or new_hour > 23:
                        update_text.append(f"❌ Nieprawidłowa godzina: {new_hour} (musi być 0-23)")
                    elif new_minute < 0 or new_minute > 59:
                        update_text.append(f"❌ Nieprawidłowa minuta: {new_minute} (musi być 0-59)")
                    elif set_leaderboard_time(new_day, new_hour, new_minute):
                        day_names = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]
                        update_text.append(
                            f"✅ Czas tablicy wyników zmieniony na {day_names[new_day]}, {new_hour}:{new_minute:02d}")
                        changes_made = True
                    else:
                        update_text.append("❌ Nie udało się zmienić czasu tablicy wyników")

                # Jeśli nie podano żadnych parametrów, wyświetl obecną konfigurację
                if not changes_made and not update_text:
                    day_names = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]
                    channel_mention = f"<#{current_channel_id}>" if current_channel_id else "Nie ustawiono"
                    await interaction.response.send_message(
                        f"ℹ️ Aktualna konfiguracja tablicy wyników:\n"
                        f"Kanał: {channel_mention}\n"
                        f"Dzień: {day_names[current_day]}\n"
                        f"Czas: {current_hour}:{current_minute:02d}",
                        ephemeral=True
                    )
                    return

                # Wyświetl podsumowanie zmian
                await interaction.response.send_message(
                    "🏆 Konfiguracja tablicy wyników:\n" + "\n".join(update_text),
                    ephemeral=True
                )

                logger.info(f"Zaktualizowano konfigurację tablicy wyników: {', '.join(update_text)}")

            except Exception as e:
                logger.error(f"Błąd podczas konfiguracji tablicy wyników: {e}")
                logger.error(traceback.format_exc())
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            f"❌ Wystąpił błąd: {str(e)}",
                            ephemeral=True
                        )
                except discord.errors.NotFound:
                    logger.warning("Nie można odpowiedzieć po błędzie - interakcja wygasła")
                except Exception:
                    pass

        # Zachowaj pozostałe komendy które chcesz

        logger.info("Komendy slash zarejestrowane pomyślnie")

    except Exception as e:
        logger.error(f"Błąd podczas rejestrowania komend slash: {e}")
        logger.error(traceback.format_exc())