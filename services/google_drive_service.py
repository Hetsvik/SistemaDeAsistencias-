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

        google_config = dict(
            st.secrets["google_drive"]
        )

        # Corregir los saltos de línea de la private key
        google_config["private_key"] = (
            google_config["private_key"]
            .replace("\\n", "\n")
        )
        #yaa

        self.credentials = (
            service_account.Credentials.from_service_account_info(
                google_config,
                scopes=self.SCOPES
            )
        )

        self.service = build(
            "drive",
            "v3",
            credentials=self.credentials
        )

        self.root_folder_id = st.secrets["storage"][
            "google_drive_folder_id"
        ]

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
                fields="id,name"
            ).execute()

            return folder

        except HttpError as e:

            print(f"Error creando carpeta: {e}")

            return None

    # =========================================================
    # SUBIR ARCHIVO
    # =========================================================

    def upload_file(
        self,
        file_data,
        file_name,
        mime_type=None,
        parent_folder_id=None
    ):

        try:

            if parent_folder_id is None:
                parent_folder_id = self.root_folder_id

            if mime_type is None:

                mime_type = (
                    mimetypes.guess_type(file_name)[0]
                    or "application/octet-stream"
                )

            metadata = {
                "name": file_name,
                "parents": [parent_folder_id]
            }

            media = MediaIoBaseUpload(
                io.BytesIO(file_data),
                mimetype=mime_type,
                resumable=True
            )

            uploaded_file = self.service.files().create(
                body=metadata,
                media_body=media,
                fields="id,name,mimeType,size,webViewLink"
            ).execute()

            return uploaded_file

        except HttpError as e:

            print(f"Error subiendo archivo: {e}")

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
                )
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
                fileId=file_id
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
                fileId=file_id
            ).execute()

            return True

        except HttpError as e:

            print(f"Error eliminando archivo: {e}")

            return False
