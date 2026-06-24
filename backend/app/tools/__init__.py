"""Tool registry.

All tools are plain LangChain tools, so any agent can be granted any subset.
``TOOLS_BY_AGENT`` defines which tools each specialist is allowed to call, and
``ALL_TOOLS`` is the union used to build the shared ``ToolNode``.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool

from app.tools.dsa_mentor import dsa_mentor
from app.tools.interview import interview_prep
from app.tools.notes import notes_generator
from app.tools.progress_analytics import progress_analytics
from app.tools.quiz import quiz_generator
from app.tools.resources import resource_recommender
from app.tools.resume_review import resume_review
from app.tools.roadmap import roadmap_generator
from app.tools.web_search import web_search
from app.tools.youtube import youtube_learning

# Tools available to each specialist agent.
TOOLS_BY_AGENT: dict[str, list[BaseTool]] = {
    "tutor": [
        web_search,
        youtube_learning,
        notes_generator,
        resource_recommender,
        dsa_mentor,
    ],
    "quiz": [quiz_generator, progress_analytics],
    "roadmap": [roadmap_generator, resource_recommender, progress_analytics],
    "resume": [resume_review, web_search],
    "interview": [interview_prep, dsa_mentor, web_search],
    # Fallback general agent gets the broad toolset.
    "general": [
        web_search,
        youtube_learning,
        notes_generator,
        resource_recommender,
        progress_analytics,
    ],
}

# Union of every tool, de-duplicated, for the shared ToolNode.
ALL_TOOLS: list[BaseTool] = list(
    {t.name: t for tools in TOOLS_BY_AGENT.values() for t in tools}.values()
)

__all__ = [
    "TOOLS_BY_AGENT",
    "ALL_TOOLS",
    "web_search",
    "youtube_learning",
    "roadmap_generator",
    "quiz_generator",
    "resume_review",
    "interview_prep",
    "dsa_mentor",
    "progress_analytics",
    "notes_generator",
    "resource_recommender",
]
