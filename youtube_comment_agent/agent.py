import os
from google import genai
from google.adk.agents.llm_agent import Agent
from .tools.youtube_tool import fetch_comments

def analyze_youtube_video(video_id: str) -> str:
    """
    Analyzes the comments of a YouTube video using a direct analysis approach.
    
    Args:
        video_id: The ID of the YouTube video to analyze.
        
    Returns:
        A comprehensive summary of the user comments and sentiment.
    """
    print(f"Starting analysis for video: {video_id}")
    
    # Fetching Comments
    try:
        comments = fetch_comments(video_id)
        if not comments:
            return "No comments found for this video."
    except Exception as e:
        return f"Error fetching comments: {str(e)}"

    
    # Format comments (limit to first 1000 to be safe, though fetch_comments defaults to 1000)
    comment_text = "\n".join([f"- {c['text']}" for c in comments[:1000]])
    
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION")
    
    try:
        client = genai.Client(vertexai=True, project=project, location=location)
        
        prompt = f"""
        Analyze the following YouTube comments:
        
        {comment_text}
        
        Provide a comprehensive summary of the user comments, including:
        1. Key Expressions/Topics
        2. Overall Sentiment (Positive/Negative/Neutral) with explanation
        3. Notable specific user feedback
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Error analyzing comments: {str(e)}"


root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='A specialized analyst that extracts and summarizes audience feedback, sentiment, and questions from YouTube comment sections.',
    instruction="""
        You are the YouTube Comment Insight Agent. Your goal is to help users understand the discussion happening around any YouTube video.

        1. **Identify the Input:** Check if the user has provided a YouTube URL or a Video ID in their message.
        
        2. **If a Link/ID is Provided:** - Immediately use the `analyze_youtube_video` tool.
           - If the user asked a specific question, answer it using only the comment data.
           - If the user just gave a link or asked for an overview, provide a summary of the top themes, general sentiment (positive/negative), and any frequent questions from the viewers.

        3. **If NO Link/ID is Provided (Greetings/General Chat):** - Do not use the tool.
           - Introduce yourself: "Hello! I am your YouTube Comment Insight Agent."
           - Explain your purpose: "I can analyze any YouTube video's comment section to give you a summary of what people are saying, answer specific questions about the audience's reaction, or identify common feedback."
           - Provide a Call to Action: "To get started, please provide a YouTube video link or Video ID."

        Always be concise and base your insights strictly on the data retrieved from the video comments.
    """,
    tools=[analyze_youtube_video]
)
