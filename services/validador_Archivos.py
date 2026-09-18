import os
ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".docx", 
    ".xlsx", ".xls",           # Excel
    ".dwg", ".dxf",            # AutoCAD
    ".blend"                   # Blender
}

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",       # xlsx
    "application/vnd.ms-excel",                                                # xls
    "image/vnd.dwg", "application/acad", "application/x-autocad", "application/dxf", "application/x-dxf", # AutoCAD
    "application/x-blender",                                                   # Blender
    "application/octet-stream" 
}

MAX_FILE_SIZE_MB = 50  

def validate_secure_file(file_name, mime_type, file_size_bytes):
    """
    Evalúa el archivo bajo políticas de seguridad estrictas antes de enviarlo a la nube.
    Retorna (es_valido: bool, mensaje_error: str)
    """
    ext = os.path.splitext(file_name)[1].lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"🚫 Extensión bloqueada: '{ext}'. Solo se admiten archivos de ofimática, imágenes, AutoCAD o Blender."
        
    if mime_type not in ALLOWED_MIME_TYPES:
        return False, f"🚫 Tipo de archivo de sistema no válido: {mime_type}."
        
    if file_size_bytes > (MAX_FILE_SIZE_MB * 1024 * 1024):
        return False, f"🚫 El archivo supera el peso máximo permitido de {MAX_FILE_SIZE_MB} MB."
        
    return True, "Archivo seguro"