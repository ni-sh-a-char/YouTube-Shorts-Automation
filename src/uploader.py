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

    # If we don't have valid credentials, try several strategies.
    if not credentials or not credentials.valid:
        # 1) If credentials exist but are expired, try to refresh them automatically.
        if credentials and credentials.expired and credentials.refresh_token:
            print("INFO: Refreshing expired credentials...")
            credentials.refresh(Request())

        else:
            # 2) If credentials.json is not present but a refresh token + client id/secret
            #    are provided via environment variables, construct credentials from the
            #    refresh token and refresh to obtain an access token. This avoids the
            #    need to run an interactive browser flow on headless hosts like Render.
            refresh_token = os.getenv('YOUTUBE_REFRESH_TOKEN')
            env_client_id = os.getenv('YOUTUBE_CLIENT_ID')
            env_client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
            token_uri = 'https://oauth2.googleapis.com/token'

            if refresh_token and env_client_id and env_client_secret:
                try:
                    print("INFO: Creating credentials from environment refresh token...")
                    credentials = Credentials(
                        token=None,
                        refresh_token=refresh_token,
                        token_uri=token_uri,
                        client_id=env_client_id,
                        client_secret=env_client_secret,
                        scopes=YOUTUBE_UPLOAD_SCOPE
                    )
                    # Refresh to obtain a valid access token
                    credentials.refresh(Request())
                    print("INFO: Successfully refreshed credentials from env refresh token")
                except Exception as e:
                    print(f"WARN: Failed to refresh credentials from environment: {e}")
                    credentials = None

            # 3) Fallback to interactive installed app flow (local dev only)
            if (not credentials or not credentials.valid) and not CREDENTIALS_FILE.exists():
                print("INFO: No valid credentials found. Starting new authentication flow...")
                if not CLIENT_SECRETS_FILE.exists():
                    raise FileNotFoundError(f"CRITICAL ERROR: {CLIENT_SECRETS_FILE} not found. Please download it from Google Cloud Console.")

                flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), scopes=YOUTUBE_UPLOAD_SCOPE)
                # This command will start a local server, open your browser,
                # and wait for you to grant permission.
                credentials = flow.run_local_server(port=0)

        # If we obtained credentials, optionally save them for future runs
        if credentials and credentials.valid:
            try:
                with open(CREDENTIALS_FILE, 'w') as f:
                    f.write(credentials.to_json())
                print(f"INFO: Credentials saved to {CREDENTIALS_FILE}")
            except Exception:
                # If filesystem is read-only on platform, skip saving silently
                print("WARN: Could not save credentials to disk; proceeding with in-memory credentials")
            
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
    # Normalize keywords to a list
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(',') if k.strip()]

    # Build tags: priority defaults + extracted keywords (max 30)
    default_tags = ['Shorts', 'Viral', 'HowTo', 'Tutorial']
    if topic:
        default_tags.insert(0, topic.replace(' ', ''))

    tags_list = default_tags + [k.replace(' ', '') for k in keywords]
    # Keep unique and limit to 30
    seen = set()
    dedup_tags = []
    for t in tags_list:
        if t and t.lower() not in seen:
            dedup_tags.append(t)
            seen.add(t.lower())
        if len(dedup_tags) >= 30:
            break

    tags = ','.join(dedup_tags)

    # Build a set of hashtags (keywords + trending)
    hashtags = []
    for k in keywords[:10]:
        h = '#' + ''.join(e for e in k if e.isalnum())
        if h and h.lower() not in [x.lower() for x in hashtags]:
            hashtags.append(h)

    trending = ['#Shorts', '#Viral', '#FYP', '#ForYou']
    if topic:
        topic_tag = '#' + ''.join(e for e in topic if e.isalnum())
        if topic_tag.lower() not in [x.lower() for x in hashtags]:
            hashtags.insert(0, topic_tag)

    # Merge unique trending hashtags after keywords
    for t in trending:
        if t.lower() not in [x.lower() for x in hashtags]:
            hashtags.append(t)

    hashtags_str = ' '.join(hashtags[:20])

    # Build a concise description (include script summary and hashtags)
    parts = [p.strip() for p in script.split('[PAUSE]') if p.strip()]
    if len(parts) > 1:
        summary = parts[1].strip()
    else:
        summary = ' '.join(parts).strip()

    # Truncate summary gracefully
    max_summary = 800
    if len(summary) > max_summary:
        summary = summary[:max_summary].rsplit(' ', 1)[0] + '...'

    channel_url = os.getenv('CHANNEL_URL', '')

    # If the script provides a ready-to-paste description, prefer it (but still
    # append web-trending hashtags if available). Respect code inclusion policy.
    description = None
    if isinstance(script_data, dict) and script_data.get('description_for_upload'):
        description = script_data.get('description_for_upload')

    # If allowed, append short code snippet into description (escaped)
    allow_code = os.getenv('ALLOW_CODE_IN_DESCRIPTION', 'false').lower() == 'true'
    code_snippet = script_data.get('code_snippet') if isinstance(script_data, dict) else None
    if description is None:
        description_lines = [summary]
        if channel_url:
            description_lines.append(f"🔗 More tutorials: {channel_url}")
        description_lines.append(hashtags_str)
        description = "\n\n".join([l for l in description_lines if l])

    if code_snippet and allow_code:
        # Sanitize snippet to avoid very long blocks
        cs = str(code_snippet).strip()
        lines = cs.splitlines()
        if len(lines) > 12:
            cs = '\n'.join(lines[:12]) + '\n#...'
        description = description + "\n\nCode snippet:\n" + cs

    return {
        'title': title,
        'description': description,
        'tags': tags,
        'hashtags': hashtags_str
    }

