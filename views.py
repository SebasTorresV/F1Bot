import discord

class TrackButton(discord.ui.Button):
    def __init__(self, track_name, event_creator):
        super().__init__(label=track_name, style=discord.ButtonStyle.primary)
        self.track_name = track_name
        self.event_creator = event_creator

    async def callback(self, interaction: discord.Interaction):
        from events import events, events_lock, RaceEvent

        guild_id = interaction.guild.id
        start_time = self.event_creator['start_time']
        duration_minutes = self.event_creator['duration_minutes']
        creator = interaction.user
        channel = interaction.channel

        async with events_lock:
            # Crear el evento y almacenarlo
            event = RaceEvent(guild_id, channel, creator, self.track_name, start_time, duration_minutes)
            events[guild_id] = event

        await event.create_event()

        # Intentar eliminar el mensaje de selección de pista
        try:
            await self.event_creator['message'].delete()
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass
        except Exception as e:
            print(f"Error al eliminar el mensaje de selección de pista: {e}")

        # Enviar un mensaje confirmando la creación del evento
        await interaction.response.send_message(
            f"Evento de carrera creado en {self.track_name} por {creator.mention}.",
            ephemeral=True
        )

class RegistrationButton(discord.ui.Button):
    def __init__(self, event):
        super().__init__(label="Inscribirse", style=discord.ButtonStyle.success)
        self.event = event

    async def callback(self, interaction: discord.Interaction):
        if not self.event.registration_open:
            await interaction.response.send_message("Las inscripciones ya han cerrado.", ephemeral=True)
            return

        user = interaction.user
        if user in self.event.registered_users:
            await interaction.response.send_message("Ya estás inscrito en este evento.", ephemeral=True)
            return

        self.event.registered_users.append(user)
        await self.event.update_event_message()
        await interaction.response.send_message("Te has inscrito correctamente.", ephemeral=True)

class UnregisterButton(discord.ui.Button):
    def __init__(self, event):
        super().__init__(label="Desinscribirse", style=discord.ButtonStyle.danger)
        self.event = event

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        if user not in self.event.registered_users:
            await interaction.response.send_message("No estás inscrito en este evento.", ephemeral=True)
            return

        self.event.registered_users.remove(user)
        await self.event.update_event_message()
        await interaction.response.send_message("Te has desinscrito del evento.", ephemeral=True)

class RegistrationView(discord.ui.View):
    def __init__(self, event):
        super().__init__(timeout=None)
        self.add_item(RegistrationButton(event))
        self.add_item(UnregisterButton(event))
