import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone
from views import TrackButton
from events import events, events_lock  # Importa el diccionario y el lock

F1_TRACKS = [
    "Silverstone", "Monza", "Spa-Francorchamps", "Mónaco", "Interlagos",
    "Suzuka", "Circuito de las Américas", "Yas Marina", "Baréin", "Imola",
    "Zandvoort", "Red Bull Ring", "Paul Ricard", "Jeddah (Arabia Saudita)",
    "Miami", "Las Vegas", "Barcelona-Cataluña", "Hungaroring (Hungría)",
    "Singapur", "Melbourne (Australia)", "Shanghái (China)",
    "Ciudad de México (México)"
]

# Función para crear un evento de carrera
async def create_race_event(interaction, race_time_str, race_duration_minutes):
    guild_id = interaction.guild.id

    async with events_lock:
        if guild_id in events:
            await interaction.response.send_message("Ya hay un evento en curso en este servidor.", ephemeral=True)
            return

    # Manejo de zonas horarias (UTC)
    try:
        race_time = datetime.strptime(race_time_str, '%I:%M %p').replace(tzinfo=timezone.utc)
        current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        race_time = race_time.replace(year=current_time.year, month=current_time.month, day=current_time.day)
        if race_time < current_time:
            race_time += timedelta(days=1)
    except ValueError:
        await interaction.response.send_message("Formato de hora incorrecto. Use el formato HH:MM AM/PM.", ephemeral=True)
        return

    # Diferir la respuesta ya que vamos a realizar operaciones que toman tiempo
    await interaction.response.defer()

    event_creator = {
        'start_time': race_time,
        'duration_minutes': race_duration_minutes,
        'interaction': interaction
    }

    view = discord.ui.View()
    for track in F1_TRACKS:
        button = TrackButton(track, event_creator)
        view.add_item(button)

    # Enviar el mensaje y guardar la referencia
    message = await interaction.followup.send(
        "Selecciona una pista para la carrera (clasificación y carrera combinadas):",
        view=view
    )
    # Guardar el mensaje en event_creator para que pueda ser editado en el callback
    event_creator['message'] = message

# Comando /race
@app_commands.command(name="race", description="Crear un evento de carrera (clasificación y carrera combinadas)")
@commands.has_permissions(administrator=True)
async def race(interaction: discord.Interaction):
    try:
        # Crear el evento de carrera (clasificación y carrera combinadas)
        await create_race_event(interaction, "7:00 PM", 120)
    except discord.errors.NotFound:
        # Manejar el caso de una interacción no válida o caducada
        await interaction.response.send_message("Error: Interacción no encontrada o ha caducado.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Error de HTTP: {e}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Error inesperado: {e}", ephemeral=True)

# Comando /p (Penalización)
@app_commands.command(name="p", description="Crear una penalización")
async def crear_penalizacion(interaction: discord.Interaction, usuario: discord.Member, razon: str):
    if razon.strip() == '':
        await interaction.response.send_message("Proporcione una razón para la penalización.", ephemeral=True)
        return

    # Definir el ID del rol de comisario
    COMISARIO_ROLE_ID = 1299584449926795284  # Reemplaza con el ID real

    # Buscar el rol de comisario en el servidor
    comisario_role = interaction.guild.get_role(COMISARIO_ROLE_ID)
    if comisario_role is None:
        await interaction.response.send_message("No se encontró el rol @Comisario en este servidor.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🚨 Propuesta de Penalización 🚨",
        description="Un jugador ha sido reportado.",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="⚠ Jugador", value=usuario.mention, inline=False)
    embed.add_field(name="👤 Reportado por", value=interaction.user.mention, inline=False)
    embed.add_field(name="📄 Razón", value=razon, inline=False)
    embed.set_footer(text="Sistema de Penalizaciones")

    try:
        thread_name = f"{interaction.user.display_name}/{usuario.display_name}"
        thread = await interaction.channel.create_thread(
            name=thread_name,
            auto_archive_duration=60,
            type=discord.ChannelType.private_thread
        )
    except discord.Forbidden:
        await interaction.response.send_message("No tengo permisos para crear un hilo privado.", ephemeral=True)
        return

    await thread.add_user(interaction.user)
    await thread.add_user(usuario)

    # Mención al rol de comisario en el hilo
    await thread.send(
        f"{comisario_role.mention}, se ha creado una nueva propuesta de penalización para {usuario.mention}. Por favor, revisen el caso."
    )

    # Agregar enlace al hilo en el embed
    embed.add_field(
        name="🗣 Ir a discusión",
        value=f"[Haz clic aquí para ir a la discusión]({thread.jump_url})",
        inline=False
    )
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("Penalización creada.", ephemeral=True)

# Comando /cerrar (Cerrar Hilo)
@app_commands.command(name="cerrar", description="Cerrar un hilo (solo administradores)")
@commands.has_permissions(administrator=True)
async def cerrar_hilo(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    if isinstance(interaction.channel, discord.Thread):
        try:
            await interaction.channel.send("Este hilo ha sido finalizado.")
            await interaction.channel.edit(archived=True, locked=True)
            await interaction.followup.send("El hilo ha sido cerrado.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Error al cerrar el hilo: {e}", ephemeral=True)
    else:
        await interaction.followup.send("Este comando solo puede usarse en un hilo.", ephemeral=True)

# Comando /sc (Sanción personalizada)
@app_commands.command(name="sc", description="Reportar una sanción personalizada")
@commands.has_permissions(administrator=True)
async def sancion(interaction: discord.Interaction, usuario: discord.Member, mensaje: str):
    if mensaje.strip() == '':
        await interaction.response.send_message("Proporcione un mensaje para la sanción.", ephemeral=True)
        return

    embed = discord.Embed(
        title="📋 Sanción Personalizada",
        description=f"{interaction.user.mention} ha reportado una sanción para {usuario.mention}.",
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="📝 Mensaje", value=mensaje, inline=False)
    embed.set_footer(text="Sistema de Sanciones")

    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("Sanción reportada.", ephemeral=True)

# Comando /end_race (Finalizar evento de carrera)
@app_commands.command(name="end_race", description="Finalizar el evento de carrera (solo administradores)")
@commands.has_permissions(administrator=True)
async def end_race(interaction: discord.Interaction):
    # Diferir la respuesta
    await interaction.response.defer(ephemeral=True)

    guild_id = interaction.guild.id
    async with events_lock:
        if guild_id not in events:
            await interaction.followup.send("No hay ningún evento en curso en este servidor.", ephemeral=True)
            return

        event = events[guild_id]

        # Finalizar las inscripciones y cerrar el evento
        await event.close_registrations()

        # Enviar mensaje de finalización
        if event.registered_users:
            users_list = "\n".join(user.mention for user in event.registered_users)
            await interaction.channel.send(f"🏁 ¡El evento ha finalizado! Lista de inscritos:\n{users_list}")
        else:
            await interaction.channel.send("❌ El evento ha finalizado, pero no hubo usuarios inscritos.")

        # Deshabilitar los botones en la vista si el mensaje existe
        if event.event_message:
            new_view = discord.ui.View()
            if event.event_message.components:
                for item in event.event_message.components:
                    for component in item.children:
                        if isinstance(component, discord.ui.Button):
                            component.disabled = True
                            new_view.add_item(component)

            try:
                await event.event_message.edit(view=new_view)
            except discord.NotFound:
                # El mensaje fue eliminado; continuamos sin interrumpir
                event.event_message = None
            except discord.HTTPException as e:
                if e.code == 50083:  # Thread is archived
                    await interaction.channel.send("El hilo está archivado. Será eliminado.")
                    await event.event_message.channel.delete()  # Eliminar el hilo archivado
                else:
                    raise e

        # Eliminar el evento del diccionario
        del events[guild_id]

    # Enviar mensaje de confirmación
    await interaction.followup.send("Evento finalizado.", ephemeral=True)

# Comando /ayuda
@app_commands.command(name="ayuda", description="Mostrar ayuda")
async def custom_help(interaction: discord.Interaction):
    help_message = (
        "Comandos disponibles:\n"
        "/p - Crear penalización.\n"
        "/cerrar - Cerrar un hilo (solo administradores).\n"
        "/sc - Sanción personalizada (solo administradores).\n"
        "/race - Crear evento de carrera (clasificación y carrera combinadas).\n"
        "/end_race - Finalizar el evento de carrera (solo administradores).\n"
    )
    await interaction.response.send_message(help_message, ephemeral=True)

# Registrar todos los comandos
def register_commands(bot):
    bot.tree.add_command(race)
    bot.tree.add_command(crear_penalizacion)
    bot.tree.add_command(cerrar_hilo)
    bot.tree.add_command(sancion)
    bot.tree.add_command(end_race)
    bot.tree.add_command(custom_help)
