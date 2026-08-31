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

        google_config = st.secrets["google_drive"]

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

        self.root_folder_id = google_config["folder_id"]