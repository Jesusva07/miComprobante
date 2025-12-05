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
    
    # Obtener parámetros de búsqueda
    busqueda = request.args.get('busqueda', '').strip()
    filtro_fecha = request.args.get('fecha', '').strip()
    filtro_tipo = request.args.get('tipo', 'nombre').strip()  # nombre, fecha, monto
    
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Query base
        query = 'SELECT * FROM transferencias WHERE 1=1'
        params = []
        
        # Filtro de búsqueda
        if busqueda:
            if filtro_tipo == 'nombre':
                query += ' AND nombre LIKE ?'
                params.append(f'%{busqueda}%')
            elif filtro_tipo == 'monto':
                query += ' AND monto LIKE ?'
                params.append(f'%{busqueda}%')
            elif filtro_tipo == 'descripcion':
                query += ' AND descripcion LIKE ?'
                params.append(f'%{busqueda}%')
        
        # Filtro de fecha exacta
        if filtro_fecha:
            query += ' AND fecha = ?'
            params.append(filtro_fecha)
        
        # Ordenar por fecha descendente
        query += ' ORDER BY fecha DESC'
        
        cursor.execute(query, params)
        datos = cursor.fetchall()
        conn.close()
        
        return render_template('lista.html', 
                             datos=datos,
                             busqueda=busqueda,
                             filtro_fecha=filtro_fecha,
                             filtro_tipo=filtro_tipo)
    except Exception as e:
        print(f"Error en búsqueda: {e}")
        flash(f'Error al filtrar: {str(e)}')
        return render_template('lista.html', datos=[])



@app.route('/transferencias/eliminar/<int:transfer_id>', methods=['POST'])
def eliminar_transferencia(transfer_id):
    """Eliminar una transferencia por ID"""
    if not session.get('logueado'):
        return redirect(url_for('login'))
    
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Obtener la URL de la imagen para eliminarla de Cloudinary (opcional)
        cursor.execute('SELECT imagen FROM transferencias WHERE id = ?', (transfer_id,))
        resultado = cursor.fetchone()
        
        if resultado:
            imagen_url = resultado[0]
            # Aquí podrías eliminar de Cloudinary si quieres (es opcional)
            
            # Eliminar registro de la base de datos
            cursor.execute('DELETE FROM transferencias WHERE id = ?', (transfer_id,))
            conn.commit()
            conn.close()
            
            flash('Transferencia eliminada correctamente')
            return redirect(url_for('ver_transferencias'))
        else:
            flash('Transferencia no encontrada')
            return redirect(url_for('ver_transferencias'))
            
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}')
        return redirect(url_for('ver_transferencias'))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
