import os
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from deep_translator import GoogleTranslator
from langchain_groq import ChatGroq
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from prompt import apply_prompt
from utils import batch_translate, extract_youtube_id, format_docs

load_dotenv()
os.environ["TOKENIZERS_PARALLELISM"] = "false"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HUGGINGFACEHUB_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "llama-3.3-70b-versatile"

llm = None
vector_store = None

def initialize_llm():
    global llm
    try:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable not set.")    
        if llm is None:
            llm = ChatGroq(model=LLM_MODEL, temperature=0.9, max_tokens=500, api_key=GROQ_API_KEY)
        return llm
    except ValueError as ve:
        # Handle missing API key or custom ValueError
        print(ve)
        return None

    except Exception as e:
        # Handle invalid API key or other errors during initialization
        print(f"❌ Failed to initialize LLM: {e}")
        return None

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

# Step 1b - Indexing (Text Splitting)
def text_splitter(translated_text, CHUNK_SIZE, CHUNK_OVERLAP):
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.create_documents([translated_text])
    return chunks

# Step 1c & 1d - Indexing (Embedding Generation and Storing in Vector Store)
def embedding_vector_store(translated_text):
    global vector_store

    if vector_store is None:
        chunks = text_splitter(translated_text, CHUNK_SIZE, CHUNK_OVERLAP)
        embedding_fun = HuggingFaceEmbeddings(model=EMBEDDING_MODEL)
        vector_store = FAISS.from_documents(chunks, embedding_fun)

def process_video(url: str):
    """Full pipeline for ingesting YouTube video into vector store."""
    video_id = extract_youtube_id(url)
    if video_id:
        initialize_llm()
        transcript, language = fetch_youtube_transcript(video_id)
        vector_store = embedding_vector_store(transcript)
        print("Transcript processed and stored ✅")
        return vector_store
    

def call_llm(text):
    # llm is your global ChatOpenAI instance
    return llm.invoke(text).content


# --- Step 4: LLM with prompt Generate Answer using Chain ---
def generate_answer_chain(query: str):
    if not vector_store:
        raise RuntimeError("Vector store is not initialized. Please process a video first.")

    # Step 2: Retrieval
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})

    # Step 3 : Augmentation | Parallel retrieval + passthrough
    parallel_chain = RunnableParallel({
        "context": retriever | RunnableLambda(format_docs),
        "question": RunnablePassthrough()
    })

    # Wrap prompt and LLM into RunnableLambda
    prompt_runnable = RunnableLambda(apply_prompt)
    llm_runnable = RunnableLambda(call_llm)
    parser = StrOutputParser()

    # Build the main chain
    main_chain = parallel_chain | prompt_runnable | llm_runnable | parser

    # Step 5: Invoke the chain with query
    answer = main_chain.invoke(query)
    # main_chain.get_graph().print_ascii()
    return answer


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=ZCSsIkyCZk4"
    process_video(url)

    generate_answer_chain("What is FAISS Vector")
