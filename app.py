from flask import Flask, request, redirect, url_for, render_template, session, flash
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

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

# Verificar que exista la carpeta de uploads (para desarrollo local)
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Modelo de Base de Datos
class Transferencia(db.Model):
    __tablename__ = 'transferencias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    fecha = db.Column(db.String(255), nullable=False)
    monto = db.Column(db.String(255))
    descripcion = db.Column(db.Text)
    imagen = db.Column(db.String(512), nullable=False)

    def __repr__(self):
        return f'<Transferencia {self.nombre}>'

# Crear las tablas
with app.app_context():
    db.create_all()

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
                
                # Obtener URL de la imagen
                url_imagen = resultado['secure_url']
                
                # Guardar en la base de datos
                nueva_transferencia = Transferencia(
                    nombre=nombre,
                    fecha=fecha,
                    monto=monto,
                    descripcion=descripcion,
                    imagen=url_imagen
                )
                db.session.add(nueva_transferencia)
                db.session.commit()
                
                flash('Comprobante subido exitosamente')
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
    
    transferencias = Transferencia.query.order_by(Transferencia.fecha.desc()).all()
    
    # Convertir a tuplas para compatibilidad con la plantilla
    datos = [(t.id, t.nombre, t.fecha, t.monto, t.descripcion, t.imagen) for t in transferencias]
    
    return render_template('lista.html', datos=datos)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
