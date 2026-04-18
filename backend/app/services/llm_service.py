from typing import Generator
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0.2,
)

QA_PROMPT = ChatPromptTemplate.from_template(
    """You are a helpful AI assistant. Answer the user's question using ONLY the context provided below.
If the answer is not in the context, say exactly: "I couldn't find information about that in the uploaded file."
Be concise and accurate.

Context:
{context}

Question: {question}

Answer:"""
)


def answer(question: str, chunks: list[dict]) -> str:
    """Run the LangChain QA chain with retrieved chunks as context."""
    context = "\n\n---\n\n".join([c["text"] for c in chunks])
    chain = QA_PROMPT | llm
    result = chain.invoke({"context": context, "question": question})
    return result.content


def answer_stream(question: str, chunks: list[dict]) -> Generator[str, None, None]:
    """
    Stream the LLM response token-by-token.
    Yields content strings as they arrive from the model.
    """
    context = "\n\n---\n\n".join([c["text"] for c in chunks])
    chain = QA_PROMPT | llm
    for chunk in chain.stream({"context": context, "question": question}):
        if hasattr(chunk, "content") and chunk.content:
            yield chunk.content
