from flask import Flask, request, redirect, url_for, render_template, session, flash
from flask_sqlalchemy import SQLAlchemy
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import redis

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# Configurar SQLAlchemy con PostgreSQL
database_url = os.getenv('DATABASE_URL')
if database_url:
    # Para compatibilidad con Vercel
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Fallback para desarrollo local
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Usar variables de entorno
app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key-change-in-production')
USUARIO = os.getenv('USUARIO_APP', 'admin')
PASSWORD = os.getenv('PASSWORD_APP', 'password')

# Configurar Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Configurar Redis (Vercel KV)
# En desarrollo usa SQLite, en producción usa Redis
if os.getenv('KV_URL'):
    # Producción: conectar a Vercel KV (Redis)
    try:
        redis_client = redis.from_url(os.getenv('KV_URL'), decode_responses=True)
        redis_client.ping()
        print("Conectado a Vercel KV (Redis)")
        USE_REDIS = True
    except Exception as e:
        print(f"No se pudo conectar a Redis: {e}")
        print("Usando SQLite en su lugar...")
        USE_REDIS = False
        import sqlite3
else:
    # Desarrollo: usar SQLite
    print("Usando SQLite para desarrollo local")
    USE_REDIS = False
    import sqlite3

# Funciones para manejar tanto SQLite como Redis
def init_db():
    """Inicializar base de datos (solo para SQLite local)"""
    if not USE_REDIS:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transferencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            fecha TEXT NOT NULL,
            monto TEXT,
            descripcion TEXT,
            imagen TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()
        conn.close()

def guardar_transferencia(nombre, fecha, monto, descripcion, imagen):
    """Guardar transferencia en Redis o SQLite"""
    if USE_REDIS:
        # Usar Redis
        try:
            transferencia = {
                'nombre': nombre,
                'fecha': fecha,
                'monto': monto,
                'descripcion': descripcion,
                'imagen': imagen,
                'created_at': datetime.now().isoformat()
            }
            
            # Incrementar contador para ID único
            transfer_id = redis_client.incr('transfer_count')
            redis_client.hset(f'transfer:{transfer_id}', mapping=transferencia)
            
            # Agregar ID a lista de todas las transferencias para búsqueda rápida
            redis_client.lpush('transfers_list', transfer_id)
            
            return True
        except Exception as e:
            print(f"Error guardando en Redis: {e}")
            return False
    else:
        # Usar SQLite
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO transferencias (nombre, fecha, monto, descripcion, imagen) VALUES (?, ?, ?, ?, ?)', 
                          (nombre, fecha, monto, descripcion, imagen))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error guardando en SQLite: {e}")
            return False

def obtener_transferencias():
    """Obtener todas las transferencias (ordenadas por fecha descendente)"""
    if USE_REDIS:
        # Usar Redis
        try:
            transfer_ids = redis_client.lrange('transfers_list', 0, -1)
            transferencias = []
            
            for transfer_id in transfer_ids:
                data = redis_client.hgetall(f'transfer:{transfer_id}')
                if data:
                    # Formato: (id, nombre, fecha, monto, descripcion, imagen)
                    transferencias.append((
                        transfer_id,
                        data.get('nombre', ''),
                        data.get('fecha', ''),
                        data.get('monto', ''),
                        data.get('descripcion', ''),
                        data.get('imagen', '')
                    ))
            
            # Ordenar por fecha descendente
            transferencias.sort(key=lambda x: x[2], reverse=True)
            return transferencias
        except Exception as e:
            print(f"Error obteniendo de Redis: {e}")
            return []
    else:
        # Usar SQLite
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM transferencias ORDER BY fecha DESC')
            datos = cursor.fetchall()
            conn.close()
            return datos
        except Exception as e:
            print(f"Error obteniendo de SQLite: {e}")
            return []

# Inicializar BD
init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        if usuario == USUARIO and password == PASSWORD:
            session['logueado'] = True
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logueado', None)
    return redirect(url_for('login'))

# Página principal: formulario para subir imagen + datos
@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logueado'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        fecha = request.form['fecha']
        monto = request.form.get('monto', '')
        descripcion = request.form.get('descripcion', '')
        imagen = request.files['imagen']
        
        if imagen:
            try:
                # Subir a Cloudinary
                resultado = cloudinary.uploader.upload(
                    imagen,
                    folder='comprobantes',
                    resource_type='auto'
                )
                
                url_imagen = resultado['secure_url']
                
                # Guardar en BD (Redis o SQLite)
                if guardar_transferencia(nombre, fecha, monto, descripcion, url_imagen):
                    flash('Comprobante subido exitosamente')
                    return redirect(url_for('index'))
                else:
                    flash('Error al guardar en la base de datos')
                    return redirect(url_for('index'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al subir la imagen: {str(e)}')
                return redirect(url_for('index'))
    
    return render_template('index.html')

# Página de listado/consulta
@app.route('/transferencias')
def ver_transferencias():
    if not session.get('logueado'):
        return redirect(url_for('login'))
    
    datos = obtener_transferencias()
    return render_template('lista.html', datos=datos)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
