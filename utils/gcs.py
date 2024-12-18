#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
##
# Description:-
#
#       Google Cloud Storage (GCS) client integration utilities.
#       Provides robust binary payload upload, content-type inference,
#       and blob enumeration across enterprise Cloud Storage buckets.
#
##
# Development date    Developed by       Comments
# ----------------    ------------       ---------
# 14/11/2024          Saddam Khan        Initial implementation
# 18/12/2024          Saddam Khan        Added Cloud Storage object upload and prefix listing
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import os
import mimetypes
from typing import Tuple, List, Optional
from google.cloud import storage
from google.auth.exceptions import DefaultCredentialsError

def get_gcs_client(project_id: str = "") -> Optional[storage.Client]:
    """
    Explanation: Initializes Google Cloud Storage client authenticated via ADC
    :param  project_id str: GCP project identifier
    :return client Optional[storage.Client]: Authenticated GCS client or None
    """
    try:
        if project_id and project_id.strip():
            return storage.Client(project=project_id.strip())
        return storage.Client()
    except (DefaultCredentialsError, Exception):
        return None

def upload_to_gcs(
    file_bytes: bytes,
    filename: str,
    bucket_name: str,
    folder: str = "raw",
    project_id: str = "",
) -> Tuple[bool, str]:
    """
    Explanation: Uploads raw byte content to designated GCS bucket and path
    :param  file_bytes bytes: Document byte array
    :param  filename str: Destination file name
    :param  bucket_name str: Target GCS bucket name
    :param  folder str: Target directory folder within bucket
    :param  project_id str: GCP project identifier
    :return success bool: True if upload succeeded, False otherwise
    :return gcs_uri_or_error str: Resulting gs:// URI or error message string
    """
    if not bucket_name or not bucket_name.strip():
        return False, "No GCS bucket specified in configuration."

    client = get_gcs_client(project_id)
    if not client:
        return False, "Could not initialize GCS client (ADC credentials missing)."

    clean_bucket = bucket_name.strip().replace("gs://", "").strip("/")
    clean_folder = folder.strip().strip("/")
    blob_path = f"{clean_folder}/{filename}" if clean_folder else filename
    gcs_uri = f"gs://{clean_bucket}/{blob_path}"

    try:
        bucket = client.bucket(clean_bucket)
        blob = bucket.blob(blob_path)

        content_type, _ = mimetypes.guess_type(filename)
        blob.upload_from_string(
            file_bytes,
            content_type=content_type or "application/octet-stream",
        )
        return True, gcs_uri
    except Exception as e:
        return False, f"GCS Upload failed: {str(e)}"

def list_gcs_blobs(
    bucket_name: str,
    folder: str = "raw",
    project_id: str = "",
) -> List[str]:
    """
    Explanation: Lists document URIs present under specified prefix in GCS bucket
    :param  bucket_name str: Target GCS bucket name
    :param  folder str: Directory prefix filter
    :param  project_id str: GCP project ID
    :return uris List[str]: List of matching gs:// blob URI paths
    """
    if not bucket_name:
        return []

    client = get_gcs_client(project_id)
    if not client:
        return []

    clean_bucket = bucket_name.strip().replace("gs://", "").strip("/")
    prefix = f"{folder.strip().strip('/')}/" if folder else None

    try:
        bucket = client.bucket(clean_bucket)
        blobs = bucket.list_blobs(prefix=prefix)
        return [f"gs://{clean_bucket}/{b.name}" for b in blobs if not b.name.endswith("/")]
    except Exception:
        return []
