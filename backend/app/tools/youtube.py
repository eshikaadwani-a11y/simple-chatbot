"""YouTube learning tool — finds educational videos and tutorials."""

from __future__ import annotations

import json

from langchain_core.tools import tool

from app.config import get_settings


@tool
def youtube_learning(topic: str, max_results: int = 5) -> str:
    """Find high-quality educational YouTube videos/tutorials for a topic.

    Returns a JSON list of {title, channel, url, description}. Prefer this when
    the learner asks for videos, visual explanations, or course recommendations.
    """
    settings = get_settings()
    if not settings.youtube_api_key:
        return json.dumps(
            {
                "note": "YOUTUBE_API_KEY not configured; returning a search link instead.",
                "topic": topic,
                "search_url": f"https://www.youtube.com/results?search_query={topic.replace(' ', '+')}+tutorial",
                "results": [],
            }
        )

    try:
        from googleapiclient.discovery import build

        youtube = build("youtube", "v3", developerKey=settings.youtube_api_key)
        request = youtube.search().list(
            q=f"{topic} tutorial",
            part="snippet",
            type="video",
            maxResults=max_results,
            order="relevance",
            videoEmbeddable="true",
        )
        response = request.execute()
        results = []
        for item in response.get("items", []):
            vid = item["id"]["videoId"]
            sn = item["snippet"]
            results.append(
                {
                    "title": sn["title"],
                    "channel": sn["channelTitle"],
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "description": sn.get("description", "")[:300],
                }
            )
        return json.dumps({"topic": topic, "results": results})
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"topic": topic, "error": str(exc), "results": []})
