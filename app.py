from flask import Flask, request, redirect, url_for, render_template, send_from_directory, session, flash

import os
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'  # Carpeta donde se guardan las imágenes
app.secret_key = 'Jesusvalen07!'

# Verificar que exista la carpeta de uploads
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

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

USUARIO = 'admin'
PASSWORD = 'Jesusvalen07!'

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
            # Guardar imagen en carpeta uploads
            ruta = os.path.join(app.config['UPLOAD_FOLDER'], imagen.filename)
            imagen.save(ruta)

            # Guardar datos en la base de datos
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO transferencias (nombre, fecha, monto, descripcion, imagen) VALUES (?, ?, ?, ?, ?)', 
                          (nombre, fecha, monto, descripcion, imagen.filename))
            conn.commit()
            conn.close()

            return redirect(url_for('index'))

    # Mostrar formulario
    return render_template('index.html')

# Página de listado/consulta (puedes filtrar después)
@app.route('/transferencias')
def ver_transferencias():
    if not session.get('logueado'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transferencias')
    datos = cursor.fetchall()
    conn.close()
    return render_template('lista.html', datos=datos)

# Servir imágenes guardadas
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if not session.get('logueado'):
        return redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == "__main__":
    app.run(debug=True)
