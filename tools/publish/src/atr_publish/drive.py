"""Push built docs to Google Drive, converting docx -> native Google Docs.

OAuth desktop flow, least-privilege (`drive.file` scope -- the tool only ever sees
files it created itself, never the rest of your Drive). Needs a Google Cloud OAuth
client file (Desktop type) saved as tools/publish/.gdrive/credentials.json. The first
push opens a browser to approve; the token is cached at tools/publish/.gdrive/token.json
so later pushes are non-interactive.

Each docx is uploaded with target mimeType application/vnd.google-apps.document, so
Drive converts it to a real Google Doc on the way in -- nobody opens a .docx. PNGs
upload as images. Idempotent: a same-named file in the target folder is updated in
place (its link/id is preserved), not duplicated.
"""

from __future__ import annotations

from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

GOOGLE_DOC = "application/vnd.google-apps.document"
GOOGLE_FOLDER = "application/vnd.google-apps.folder"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

SETUP_HINT = (
    "Google Drive client libraries are not installed in this env.\n"
    "  conda run -n atr-ingest pip install -e tools/publish\n"
    "(installs google-api-python-client + google-auth-oauthlib)."
)


def _service(credentials: Path, token: Path):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:  # pragma: no cover - environment guard
        raise SystemExit(f"{SETUP_HINT}\n({exc})")

    creds = None
    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials.exists():
                raise SystemExit(
                    f"Missing OAuth client file: {credentials}\n"
                    "Create a Desktop OAuth client in Google Cloud, download its JSON, "
                    "and save it there. Steps in tools/publish/README.md."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials), SCOPES)
            print("Opening a browser to authorize Google Drive access ...")
            creds = flow.run_local_server(port=0)
        token.parent.mkdir(parents=True, exist_ok=True)
        token.write_text(creds.to_json(), encoding="utf-8")
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _find_or_create_folder(svc, name: str) -> str:
    safe = name.replace("'", "\\'")
    q = (f"mimeType='{GOOGLE_FOLDER}' and trashed=false and name='{safe}'")
    found = svc.files().list(q=q, spaces="drive", fields="files(id,name)").execute().get("files", [])
    if found:
        return found[0]["id"]
    meta = {"name": name, "mimeType": GOOGLE_FOLDER}
    return svc.files().create(body=meta, fields="id").execute()["id"]


def _folder_link(svc, folder_id: str) -> str:
    return svc.files().get(fileId=folder_id, fields="webViewLink").execute().get("webViewLink", "")


def _upload(svc, folder_id: str, local: Path) -> tuple[str, str, str]:
    from googleapiclient.http import MediaFileUpload

    is_docx = local.suffix == ".docx"
    is_png = local.suffix == ".png"
    # A Google Doc carries no file extension; images keep their name.
    name = local.stem if is_docx else local.name
    media_mime = DOCX_MIME if is_docx else "image/png" if is_png else "application/octet-stream"
    target_mime = GOOGLE_DOC if is_docx else None

    safe = name.replace("'", "\\'")
    q = f"name='{safe}' and '{folder_id}' in parents and trashed=false"
    existing = svc.files().list(q=q, spaces="drive", fields="files(id,name)").execute().get("files", [])

    media = MediaFileUpload(str(local), mimetype=media_mime, resumable=False)
    if existing:
        f = svc.files().update(fileId=existing[0]["id"], media_body=media,
                               fields="id,webViewLink").execute()
        action = "updated"
    else:
        body = {"name": name, "parents": [folder_id]}
        if target_mime:
            body["mimeType"] = target_mime
        f = svc.files().create(body=body, media_body=media, fields="id,webViewLink").execute()
        action = "created"
    return action, name, f.get("webViewLink", "")


def push(out_dir: Path, files: list[Path], credentials: Path, token: Path,
         folder_name: str = "ATR documents") -> str:
    """Upload the built docx/png outputs as native Google Docs / images. Returns folder link."""
    svc = _service(credentials, token)
    folder_id = _find_or_create_folder(svc, folder_name)
    for local in files:
        action, name, _ = _upload(svc, folder_id, local)
        kind = "Google Doc" if local.suffix == ".docx" else "image"
        print(f"  {action:>7}  {name}  ({kind})")
    return _folder_link(svc, folder_id)
