from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import os
import pickle
import io

# Permisos necesarios
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def autenticar_google_drive():
    """Autentica y devuelve el servicio de Google Drive"""
    creds = None
    
    # El archivo token.pickle guarda las credenciales del usuario
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # Si no hay credenciales válidas, solicita login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Guardar credenciales para la próxima vez
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('drive', 'v3', credentials=creds)

def subir_a_drive(nombre_archivo, archivo_bytes, mimetype):
    """Sube un archivo a Google Drive y devuelve el enlace público"""
    try:
        service = autenticar_google_drive()
        
        # Metadata del archivo
        file_metadata = {
            'name': nombre_archivo,
            'parents': ['root']  # Puedes especificar una carpeta específica con su ID
        }
        
        # Crear stream del archivo
        fh = io.BytesIO(archivo_bytes)
        media = MediaIoBaseUpload(fh, mimetype=mimetype, resumable=True)
        
        # Subir archivo
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink, webContentLink'
        ).execute()
        
        file_id = file.get('id')
        
        # Hacer el archivo público (lectura para cualquiera con el enlace)
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        # Obtener enlace directo de la imagen
        url_directo = f"https://drive.google.com/uc?export=view&id={file_id}"
        
        return url_directo
        
    except Exception as e:
        print(f"Error subiendo a Drive: {e}")
        return None
