import io
import mimetypes

import streamlit as st

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import (
    MediaIoBaseUpload,
    MediaIoBaseDownload
)
from googleapiclient.errors import HttpError


class GoogleDriveService:

    SCOPES = [
        "https://www.googleapis.com/auth/drive"
    ]

    def __init__(self):

        # =====================================================
        # CREDENCIALES DE GOOGLE
        # =====================================================

        google_config = dict(
            st.secrets["google_drive"]
        )

        # Eliminar configuraciones que NO son credenciales
        google_config.pop("folder_id", None)

        # En __init__ de tu clase GoogleDriveService:
        self.credentials = (
            service_account.Credentials.from_service_account_info(
                google_config,
                scopes=self.SCOPES
            ).with_subject("terrapapus333@gmail.com") 
        )

        # =====================================================
        # CONEXIÓN CON GOOGLE DRIVE
        # =====================================================

        self.service = build(
            "drive",
            "v3",
            credentials=self.credentials
        )

        # =====================================================
        # CARPETA PRINCIPAL Y EMAIL PROPIETARIO
        # =====================================================

        self.root_folder_id = st.secrets["storage"][
            "google_drive_folder_id"
        ]

        # Email de tu cuenta personal de Gmail para transferirle la propiedad de los archivos
        self.owner_email = st.secrets["storage"].get("owner_email")

        # Guarda el último error de la API para poder mostrarlo en la UI
        self._last_error = None

    def get_last_error(self):
        return self._last_error

    # =========================================================
    # CREAR CARPETA
    # =========================================================

    def create_folder(
        self,
        folder_name,
        parent_folder_id=None
    ):

        try:

            if parent_folder_id is None:
                parent_folder_id = self.root_folder_id

            metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_folder_id]
            }

            folder = self.service.files().create(
                body=metadata,
                fields="id,name",
                supportsAllDrives=True
            ).execute()

            return folder

        except HttpError as e:

            print(f"Error creando carpeta: {e}")

            return None

    # =========================================================
    # BUSCAR O CREAR CARPETA (NUEVO)
    # =========================================================

    def get_or_create_folder(
        self,
        folder_name,
        parent_id=None
    ):
        """
        Busca una carpeta por nombre dentro de parent_id.
        Si existe, retorna su ID.
        Si no existe, la crea y retorna el nuevo ID.
        """
        try:
            if parent_id is None:
                parent_id = self.root_folder_id

            # Escapar comillas simples en el nombre de la carpeta para evitar errores en la query
            safe_folder_name = folder_name.replace("'", "\\'")

            # Consulta para verificar si existe la carpeta activa (no en la papelera)
            query_str = (
                f"mimeType = 'application/vnd.google-apps.folder' and "
                f"name = '{safe_folder_name}' and "
                f"'{parent_id}' in parents and "
                f"trashed = false"
            )

            results = self.service.files().list(
                q=query_str,
                spaces="drive",
                fields="files(id, name)",
                pageSize=1,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="allDrives"
            ).execute()

            files = results.get("files", [])

            # Si ya existe la carpeta, retornar su ID
            if files:
                return files[0]["id"]

            # Si no existe, la creamos
            new_folder = self.create_folder(folder_name, parent_folder_id=parent_id)
            if new_folder and "id" in new_folder:
                return new_folder["id"]

            return None

        except HttpError as e:
            print(f"Error al buscar o crear la carpeta '{folder_name}': {e}")
            return None

    # =========================================================
    # OBTENER (O CREAR) CARPETA PERSONAL DEL USUARIO
    # =========================================================

    def get_user_folder(self, role, code, full_name):
        """
        Devuelve el ID de la carpeta personal del usuario dentro de la
        carpeta raíz configurada en secrets, creando toda la jerarquía
        si todavía no existe:

            Documentos (root_folder_id)
              └── Trabajadores | Administradores
                    └── "{code} - {full_name}"

        role: "Administrador" o "Empleado" (cualquier otro valor se
              trata como "Empleado" / Trabajador).
        code: Código único del trabajador o administrador.
        full_name: Nombre completo del usuario (Nombre_Completo).

        Retorna None si no se pudo crear/encontrar la carpeta, en cuyo
        caso el llamador debe manejar el error (no forzar el root).
        """
        try:
            category_name = (
                "Administradores" if role == "Administrador" else "Trabajadores"
            )

            category_folder_id = self.get_or_create_folder(
                category_name,
                parent_id=self.root_folder_id
            )

            if not category_folder_id:
                return None

            safe_code = (code or "SIN-CODIGO").strip()
            safe_name = (full_name or "SIN-NOMBRE").strip()
            user_folder_name = f"{safe_code} - {safe_name}"

            user_folder_id = self.get_or_create_folder(
                user_folder_name,
                parent_id=category_folder_id
            )

            return user_folder_id

        except HttpError as e:
            print(f"Error obteniendo la carpeta del usuario '{code} - {full_name}': {e}")
            return None

    # =========================================================
    # SUBIR ARCHIVO
    # =========================================================

    def upload_file(
        self,
        file_data,
        file_name,
        mime_type=None,
        parent_folder_id=None,
        folder_id=None  # Acepta folder_id como alias para mantener compatibilidad
    ):
        try:

            target_folder = folder_id or parent_folder_id or self.root_folder_id

            if mime_type is None:

                mime_type = (
                    mimetypes.guess_type(file_name)[0]
                    or "application/octet-stream"
                )

            metadata = {
                "name": file_name,
                "parents": [target_folder]
            }

            media = MediaIoBaseUpload(
                io.BytesIO(file_data),
                mimetype=mime_type,
                resumable=True
            )

            uploaded_file = self.service.files().create(
                body=metadata,
                media_body=media,
                fields="id,name,mimeType,size,webViewLink",
                supportsAllDrives=True
            ).execute()

            # Transferir la propiedad a tu cuenta de Gmail personal para evitar el fallo de cuota
            if self.owner_email and uploaded_file and "id" in uploaded_file:
                try:
                    user_permission = {
                        "type": "user",
                        "role": "owner",
                        "emailAddress": self.owner_email
                    }
                    self.service.permissions().create(
                        fileId=uploaded_file["id"],
                        body=user_permission,
                        transferOwnership=True,
                        supportsAllDrives=True
                    ).execute()
                except Exception as perm_err:
                    print(f"Advertencia al transferir propiedad: {perm_err}")

            return uploaded_file

        except HttpError as e:

            print(f"Error subiendo archivo a la carpeta '{target_folder}': {e}")

            self._last_error = str(e)

            return None

    # =========================================================
    # OBTENER ARCHIVO
    # =========================================================

    def get_file(self, file_id):

        try:

            file = self.service.files().get(
                fileId=file_id,
                fields=(
                    "id,name,mimeType,size,"
                    "createdTime,modifiedTime,webViewLink"
                ),
                supportsAllDrives=True
            ).execute()

            return file

        except HttpError as e:

            print(f"Error obteniendo archivo: {e}")

            return None

    # =========================================================
    # DESCARGAR ARCHIVO
    # =========================================================

    def download_file(self, file_id):

        try:

            request = self.service.files().get_media(
                fileId=file_id,
                supportsAllDrives=True
            )

            file_buffer = io.BytesIO()

            downloader = MediaIoBaseDownload(
                file_buffer,
                request
            )

            done = False

            while not done:

                status, done = downloader.next_chunk()

            file_buffer.seek(0)

            return file_buffer.read()

        except HttpError as e:

            print(f"Error descargando archivo: {e}")

            return None

    # =========================================================
    # ELIMINAR ARCHIVO
    # =========================================================

    def delete_file(self, file_id):

        try:

            self.service.files().delete(
                fileId=file_id,
                supportsAllDrives=True
            ).execute()

            return True

        except HttpError as e:

            print(f"Error eliminando archivo: {e}")

            return False
