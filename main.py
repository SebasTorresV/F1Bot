import os
import discord
from discord.ext import commands
from keep_alive import keep_alive
from commands import register_commands
from dotenv import load_dotenv  # Importar dotenv para cargar el archivo .env

load_dotenv()  # Cargar variables de entorno desde .env

# Acceder a la variable de entorno para el token de Discord
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Verifica que el TOKEN esté disponible
if not TOKEN:
    raise ValueError("El TOKEN de Discord no está configurado correctamente.")

# Configuración de intents
intents = discord.Intents.default()
intents.guilds = True
intents.members = True

# Crear el bot
bot = commands.Bot(command_prefix='!', intents=intents, case_insensitive=True)

keep_alive()  # Mantener el bot activo

# Evento cuando el bot esté listo
@bot.event
async def on_ready():
    print(f'¡Bot conectado como {bot.user}!')
    try:
        synced = await bot.tree.sync()
        print(f"Se han sincronizado {len(synced)} comandos.")
    except discord.HTTPException as e:
        print(f"Error HTTP al sincronizar comandos: {e}")
    except discord.Forbidden as e:
        print(f"No tengo permisos para sincronizar comandos: {e}")
    except Exception as e:
        print(f"Error inesperado al sincronizar comandos: {e}")

# Registrar todos los comandos
register_commands(bot)

# Iniciar el bot
try:
    bot.run(TOKEN)
except discord.LoginFailure as e:
    print(f"Error al iniciar sesión: {e}")
except Exception as e:
    print(f"Error inesperado al ejecutar el bot: {e}")
