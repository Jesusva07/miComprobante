from flask import Flask, request, redirect, url_for, render_template, send_from_directory, session, flash
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Usar variables de entorno (con valores por defecto para desarrollo)
app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key-change-in-production')

# Credenciales de login
USUARIO = os.getenv('USUARIO_APP', 'admin')
PASSWORD = os.getenv('PASSWORD_APP', 'password')

# Verificar que exista la carpeta de uploads
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Configurar Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Inicializar base de datos SQLite y crear tabla si no existe
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transferencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        fecha TEXT NOT NULL,
        monto TEXT,
        descripcion TEXT,
        imagen TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

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
            # Subir a Cloudinary
            contenido = imagen.read()
            url_imagen = cloudinary.uploader.upload(
                contenido,
                folder='comprobantes',
                resource_type='auto'
            )['secure_url']

            if url_imagen:
                # Guardar URL en la base de datos
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute('INSERT INTO transferencias (nombre, fecha, monto, descripcion, imagen) VALUES (?, ?, ?, ?, ?)', 
                              (nombre, fecha, monto, descripcion, url_imagen))
                conn.commit()
                conn.close()
                
                flash('Comprobante subido exitosamente')
                return redirect(url_for('index'))
            else:
                flash('Error al subir imagen a Cloudinary')
                return redirect(url_for('index'))

    return render_template('index.html')

# Página de listado/consulta
@app.route('/transferencias')
def ver_transferencias():
    if not session.get('logueado'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transferencias ORDER BY fecha DESC')
    datos = cursor.fetchall()
    conn.close()
    return render_template('lista.html', datos=datos)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
