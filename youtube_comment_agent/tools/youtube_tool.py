import os
import logging
from typing import List, Dict, Optional
from dotenv  import load_dotenv
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

# Constants
MAX_RESULTS_PER_PAGE = 30
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

def get_youtube_service():
    """Builds and returns the YouTube service."""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY environment variable is not set.")
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=api_key)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=3),
    retry=retry_if_exception_type((HttpError, TimeoutError))
)
def fetch_comments(video_id: str, max_comments: int = 1000) -> List[Dict[str, str]]:
    """
    Fetches comments for a given YouTube video ID with retries and timeout handling.
    
    Args:
        video_id: The ID of the YouTube video.
        max_comments: Maximum number of comments to retrieve.
        
    Returns:
        A list of dictionaries containing comment details (author, text, published_at).
    """
    try:
        service = get_youtube_service()
        comments = []
        
        request = service.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=min(max_comments, 1000),
            textFormat="plainText"
        )
        
        while request and len(comments) < max_comments:
            # Execute request with default socket timeout (handled by google-api-python-client)
            response = request.execute()
            
            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "author": snippet["authorDisplayName"],
                    "text": snippet["textDisplay"],
                    "published_at": snippet["publishedAt"],
                    "like_count": snippet["likeCount"]
                })
                
                if len(comments) >= max_comments:
                    break
            
            # Pagination
            if "nextPageToken" in response and len(comments) < max_comments:
                request = service.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=min(max_comments - len(comments), 1000),
                    textFormat="plainText",
                    pageToken=response["nextPageToken"]
                )
            else:
                break
                
        logger.info(f"Successfully fetched {len(comments)} comments for video {video_id}")
        return comments

    except HttpError as e:
        logger.error(f"An HTTP error occurred: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise
