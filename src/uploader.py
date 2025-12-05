# FILE: src/uploader.py
# This is the new, robust version that handles authentication correctly
# for both local use and GitHub Actions deployment.

import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pathlib import Path

# Define the paths for the credential files in the root directory
CLIENT_SECRETS_FILE = Path('client_secrets.json')
CREDENTIALS_FILE = Path('credentials.json')
YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]

def get_authenticated_service():
    """
    Handles the entire OAuth2 flow and returns an authenticated YouTube service object.
    This function is designed to work both locally and in automation.
    """
    credentials = None
    
    # Check if we already have credentials stored from a previous run
    if CREDENTIALS_FILE.exists():
        print("INFO: Found existing credentials file.")
        credentials = Credentials.from_authorized_user_file(str(CREDENTIALS_FILE), YOUTUBE_UPLOAD_SCOPE)

    # If we don't have valid credentials, start the authentication flow
    if not credentials or not credentials.valid:
        # If credentials exist but are expired, try to refresh them automatically.
        # This is what your GitHub Action will do on every run.
        if credentials and credentials.expired and credentials.refresh_token:
            print("INFO: Refreshing expired credentials...")
            credentials.refresh(Request())
        else:
            # This is the part that runs on your local computer the very first time.
            print("INFO: No valid credentials found. Starting new authentication flow...")
            if not CLIENT_SECRETS_FILE.exists():
                raise FileNotFoundError(f"CRITICAL ERROR: {CLIENT_SECRETS_FILE} not found. Please download it from Google Cloud Console.")
            
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), scopes=YOUTUBE_UPLOAD_SCOPE)
            
            # This command will start a local server, open your browser,
            # and wait for you to grant permission.
            credentials = flow.run_local_server(port=0)
        
        # Save the new, fresh credentials for all future runs
        with open(CREDENTIALS_FILE, 'w') as f:
            f.write(credentials.to_json())
        print(f"INFO: Credentials saved to {CREDENTIALS_FILE}")
            
    return build('youtube', 'v3', credentials=credentials)


# MODIFIED: Added thumbnail_path parameter
def upload_to_youtube(video_path, title, description, tags, thumbnail_path=None):
    """Uploads a video to YouTube with the given metadata and optionally a thumbnail."""
    print(f"⬆️ Uploading '{video_path}' to YouTube...")
    try:
        youtube = get_authenticated_service()
        
        request_body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags.split(','),
                'categoryId': '28' # 28 = Science & Technology
            },
            'status': {
                'privacyStatus': os.getenv('YOUTUBE_PRIVACY_STATUS', 'public'), # 'private', 'public', or 'unlisted'
                'selfDeclaredMadeForKids': False
            }
        }

        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        
        request = youtube.videos().insert(
            part=','.join(request_body.keys()),
            body=request_body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%.")
                
        video_id = response.get('id')
        print(f"✅ Video uploaded successfully! Video ID: {video_id}")

        # ADDED: Thumbnail upload logic
        if thumbnail_path and os.path.exists(thumbnail_path):
            print(f"⬆️ Uploading thumbnail '{thumbnail_path}' for video ID: {video_id}...")
            try:
                thumbnail_media = MediaFileUpload(str(thumbnail_path))
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=thumbnail_media
                ).execute()
                print("✅ Thumbnail uploaded successfully!")
            except Exception as e:
                print(f"❌ ERROR: Failed to upload thumbnail: {e}")
        else:
            print("⚠️ No thumbnail path provided or thumbnail file does not exist. Skipping thumbnail upload.")

        return video_id
        
    except Exception as e:
        print(f"❌ ERROR: Failed to upload to YouTube. {e}")
        raise


def generate_metadata_from_script(script_data: dict, topic: str = None):
    """Generate title, description, tags from script JSON.

    - Title: first hook line (max 50 chars)
    - Description: short summary, topic keywords, and one hashtag
    - Tags: pulled from `keywords` in script_data
    """
    script = script_data.get('script', '')
    # Extract first line or sentence (stop at [PAUSE] or newline or period)
    first = script.split('[PAUSE]')[0].strip()
    first = first.split('\n')[0].strip()
    if '.' in first:
        first = first.split('.')[0].strip()

    title = first[:50]

    keywords = script_data.get('keywords') or []
    tags = ','.join(keywords)

    summary = ''
    # Build a brief summary from the core message (try to find after first [PAUSE])
    parts = [p.strip() for p in script.split('[PAUSE]') if p.strip()]
    if len(parts) > 1:
        summary = parts[1][:200]
    else:
        summary = ' '.join(parts)[:200]

    hashtag = f"#{keywords[0].replace(' ', '')}" if keywords else (f"#{topic.replace(' ','')}" if topic else '')

    description = f"{summary}\n\nKeywords: {', '.join(keywords)}\n{hashtag}"

    return {
        'title': title,
        'description': description,
        'tags': tags,
        'hashtag': hashtag
    }

