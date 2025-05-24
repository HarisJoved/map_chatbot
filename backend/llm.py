import os
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-pro")  # or your default

llm = ChatGoogleGenerativeAI(
    google_api_key=GOOGLE_API_KEY,
    model=GOOGLE_MODEL,
)

embeddings = GoogleGenerativeAIEmbeddings(
    google_api_key=GOOGLE_API_KEY,
    model="models/embedding-001"
) 