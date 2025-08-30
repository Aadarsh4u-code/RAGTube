import os
from uuid import uuid4
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.chains.combine_documents import create_stuff_documents_chain
from deep_translator import GoogleTranslator

from utils import batch_translate
# from prompt import PROMPT, EXAMPLE_PROMPT

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "text-embedding-3-small"

llm = None
vector_store = None

def initialize_llm():
    # Initialize LLM.
    global llm, vector_store

    if OPENAI_API_KEY is None:
        raise ValueError("OPENAI_API_KEY environment variable not set.")    
    
    if llm is None:
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, openai_api_key=OPENAI_API_KEY)
    return llm

# Step 1a - Indexing (Document Ingestion)
def fetch_youtube_transcript(video_id: str, target_lang="en"):
    """
    Fetch the transcript of a YouTube video in English.
    - Checks if transcript is available
    - Lists available languages
    - Translates to English if needed
    Returns: translated text and language in which video is
    """

    ytt_api = YouTubeTranscriptApi()

    try:
        transcript_list = ytt_api.list(video_id)
    except NoTranscriptFound:
        print("No transcript available for this video")
        return None
    
    for transcript in transcript_list:
        print(
            f"- Language: {transcript.language} ({transcript.language_code}) | "
            f"Generated: {transcript.is_generated} | "
            f"Translatable: {transcript.is_translatable}"
        )

    # Try to find English transcript first
    try:
        transcript = transcript_list.find_transcript([target_lang])
        fetched = transcript.fetch()
        if fetched:
            transcript_text = " ".join(snippet.text for snippet in fetched)
            return transcript_text, fetched.language
        
    except:
        # If no English, use google translator to translate
        translated_text = []
        translator = GoogleTranslator(source=transcript.language_code, target=target_lang)

        transcript = next(iter(transcript_list))
        print(f"\n {transcript.language} transcript not translatable via YouTube. Using Google Translate...")
        fetched = transcript.fetch()
        for snippet in fetched[:10]:
            translated_text.append(translator.translate(snippet.text))
        return " ".join(translated_text), fetched.language

if __name__ == "__main__":
    # video_id = "yC36gN-rqjo"  # Example video ID hindi
    video_id = "etnLX7m2MiA"  # Example video ID hindi small
    # video_id = "ZCSsIkyCZk4"  # Example video ID english
    # video_id = "hhuNW1COrSM"  # Example video ID german
    translated_text, language = fetch_youtube_transcript(video_id)
    print('translated_text', translated_text)
    print('language', language)