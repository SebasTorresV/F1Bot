import discord
from discord.ext import tasks
from datetime import datetime, timedelta, timezone
from views import RegistrationView
import asyncio

# Diccionario para almacenar eventos
events = {}
events_lock = asyncio.Lock()  # Lock para evitar condiciones de carrera

class RaceEvent:
    """Clase que representa un evento de carrera en Discord."""
    def __init__(self, guild_id, channel, creator, track, start_time, duration_minutes):
        self.guild_id = guild_id
        self.channel = channel
        self.creator = creator
        self.track = track
        self.start_time = start_time
        self.duration_minutes = duration_minutes
        self.registered_users = []
        self.registration_open = True
        self.close_time = self.start_time + timedelta(minutes=self.duration_minutes)
        self.event_message = None

    async def create_event(self):
        await self.update_event_message()
        await self.channel.send("¡Evento creado y listo para inscripciones!")

    async def update_event_message(self):
        participants = "No hay inscritos" if not self.registered_users else "\n".join(
            user.mention for user in self.registered_users)

        embed = discord.Embed(
            title=f"Evento de Carrera - {self.track}",
            description="¡No te pierdas el evento!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="⏰ Hora",
            value=f"{self.start_time.strftime('%I:%M %p')} - {(self.start_time + timedelta(minutes=self.duration_minutes)).strftime('%I:%M %p')}",
            inline=False
        )
        embed.add_field(name="🏎 Pista", value=self.track, inline=False)
        embed.add_field(name="Participantes", value=participants, inline=False)
        embed.set_footer(text="¡No faltes!")

        if self.event_message:
            if not self.registration_open:
                # Deshabilitar los botones
                view = discord.ui.View()
                if self.event_message.components:
                    for item in self.event_message.components:
                        for component in item.children:
                            if isinstance(component, discord.ui.Button):
                                component.disabled = True
                                view.add_item(component)
                try:
                    await self.event_message.edit(embed=embed, view=view)
                except discord.NotFound:
                    # El mensaje fue eliminado
                    self.event_message = None
                except Exception as e:
                    print(f"Error al actualizar el mensaje del evento: {e}")
            else:
                # Actualizar la vista con los botones de inscripción
                view = RegistrationView(self)
                try:
                    await self.event_message.edit(embed=embed, view=view)
                except discord.NotFound:
                    # El mensaje fue eliminado
                    self.event_message = None
                except Exception as e:
                    print(f"Error al actualizar el mensaje del evento: {e}")
        else:
            # El mensaje del evento fue eliminado o no existe
            # Enviamos el mensaje inicial del evento
            view = RegistrationView(self)
            try:
                self.event_message = await self.channel.send(embed=embed, view=view)
            except Exception as e:
                print(f"Error al enviar el mensaje del evento: {e}")

    async def close_registrations(self):
        self.registration_open = False
        try:
            await self.update_event_message()
        except discord.NotFound:
            # El mensaje del evento ha sido eliminado
            self.event_message = None
        except Exception as e:
            print(f"Error al actualizar el mensaje del evento durante close_registrations: {e}")
        await self.channel.send("⏰ Las inscripciones para el evento han finalizado.")

# Bucle para verificar los tiempos de los eventos
@tasks.loop(minutes=1)
async def check_time():
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    async with events_lock:
        for guild_id, event in list(events.items()):
            if event.registration_open and now >= event.close_time:
                await event.close_registrations()
                del events[guild_id]
