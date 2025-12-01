from flask import Flask, request, redirect, url_for, render_template, session, flash
import os
from datetime import datetime
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

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

# Configurar PostgreSQL (Railway)
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    # Desarrollo local: usar SQLite
    DATABASE_URL = 'sqlite:///./database.db'
    print("⚠️ Usando SQLite local (desarrollo)")
else:
    # En Vercel: usar PostgreSQL de Railway
    # Vercel necesita postgresql en lugar de postgres
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    print("✅ Usando PostgreSQL en Railway (producción)")

# Crear engine de SQLAlchemy
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# Modelo de la tabla Transferencias
class Transferencia(Base):
    __tablename__ = 'transferencias'
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    fecha = Column(String(50), nullable=False)
    monto = Column(String(100))
    descripcion = Column(String(500))
    imagen = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

# Crear tablas
Base.metadata.create_all(engine)

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
            try:
                # Subir a Cloudinary
                resultado = cloudinary.uploader.upload(
                    imagen,
                    folder='comprobantes',
                    resource_type='auto'
                )
                
                url_imagen = resultado['secure_url']
                
                # Guardar en PostgreSQL
                db_session = Session()
                try:
                    nueva_transferencia = Transferencia(
                        nombre=nombre,
                        fecha=fecha,
                        monto=monto,
                        descripcion=descripcion,
                        imagen=url_imagen
                    )
                    db_session.add(nueva_transferencia)
                    db_session.commit()
                    flash('Comprobante subido exitosamente')
                    return redirect(url_for('index'))
                except Exception as e:
                    db_session.rollback()
                    flash(f'Error al guardar: {str(e)}')
                    return redirect(url_for('index'))
                finally:
                    db_session.close()
                
            except Exception as e:
                flash(f'Error al subir la imagen: {str(e)}')
                return redirect(url_for('index'))

    return render_template('index.html')

# Página de listado/consulta
@app.route('/transferencias')
def ver_transferencias():
    if not session.get('logueado'):
        return redirect(url_for('login'))
    
    try:
        db_session = Session()
        transferencias = db_session.query(Transferencia).order_by(Transferencia.fecha.desc()).all()
        
        # Convertir a tuplas para mantener compatibilidad con template
        datos = []
        for t in transferencias:
            datos.append((t.id, t.nombre, t.fecha, t.monto, t.descripcion, t.imagen))
        
        db_session.close()
        return render_template('lista.html', datos=datos)
    except Exception as e:
        print(f"Error obteniendo transferencias: {e}")
        return render_template('lista.html', datos=[])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
