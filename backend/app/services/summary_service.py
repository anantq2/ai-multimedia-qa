from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0.3,
)

SUMMARY_PROMPT = ChatPromptTemplate.from_template(
    """Summarize the following content clearly and concisely.
Format the summary as 5-10 bullet points.
Highlight the key topics, main ideas, and important details.

Content:
{text}

Summary:"""
)


def summarize(text: str) -> str:
    """Summarize text using OpenAI via LangChain. Truncates to ~12000 chars to stay within token limits."""
    truncated = text[:12000]
    chain = SUMMARY_PROMPT | llm
    result = chain.invoke({"text": truncated})
    return result.content
