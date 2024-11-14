from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/', methods=['GET'])
def index():
    return "El bot está activo MUACK!"

@app.errorhandler(404)
def not_found(e):
    return "Página no encontrada", 404

def run():
    try:
        app.run(host='0.0.0.0', port=8080)  # Render necesita que la app escuche en un puerto
    except Exception as e:
        print(f"Error en el servidor Flask: {e}")

def keep_alive():
    t = Thread(target=run)
    t.start()
