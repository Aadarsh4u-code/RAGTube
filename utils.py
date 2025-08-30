
import re
from urllib.parse import urlparse, parse_qs
import time
from deep_translator import GoogleTranslator, MyMemoryTranslator
from youtube_transcript_api import NoTranscriptFound, YouTubeTranscriptApi
import time

def batch_translate(text, source_lang, target_lang="en", max_chunk_size=1000, retries=3):
    """
    Translate text in chunks with retries, exponential backoff, and fallback translator.
    """
    chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
    translated_chunks = []

    for idx, chunk in enumerate(chunks, 1):
        success = False
        delay = 1  # initial backoff

        for attempt in range(retries):
            try:
                translated = GoogleTranslator(source=source_lang, target=target_lang).translate(chunk)
                translated_chunks.append(translated)
                success = True
                break
            except Exception as e:
                print(f"⚠️ Google failed for chunk {idx} (attempt {attempt+1}): {e}")
                time.sleep(delay)
                delay *= 2  # exponential backoff

        if not success:
            # Final fallback: MyMemory
            print(f"⚠️ Falling back to MyMemoryTranslator for chunk {idx}")
            try:
                translated = MyMemoryTranslator(source=source_lang, target=target_lang).translate(chunk)
                translated_chunks.append(translated)
            except Exception as e:
                raise RuntimeError(f"Translation failed for chunk {idx} after {retries} retries and fallback: {e}")

    return " ".join(translated_chunks)


def extract_youtube_id(url: str) -> str:
    parsed_url = urlparse(url)
    
    # Case 1: Standard watch link (youtube.com/watch?v=...)
    if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
        if parsed_url.path == "/watch":
            query_params = parse_qs(parsed_url.query)
            return query_params.get("v", [None])[0]
        elif parsed_url.path.startswith("/embed/"):
            return parsed_url.path.split("/")[2]
        elif parsed_url.path.startswith("/shorts/"):
            return parsed_url.path.split("/")[2]
    
    # Case 2: Shortened youtu.be link
    if parsed_url.hostname == "youtu.be":
        print('parsed_url.path', parsed_url.path)
        return parsed_url.path[1:]  # skip leading '/'
    
    return None



from deep_translator import GoogleTranslator
import time

def batch_translate(text, source_lang, target_lang, max_chunk_size=4000):
    """
    Splits text into chunks and translates them safely.
    Retries if translation fails.
    """
    translator = GoogleTranslator(source=source_lang, target=target_lang)

    # Split into smaller chunks
    chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
    translated_chunks = []

    for idx, chunk in enumerate(chunks, 1):
        for attempt in range(3):  # retry up to 3 times per chunk
            try:
                translated = translator.translate(chunk)
                translated_chunks.append(translated)
                break
            except Exception as e:
                print(f"⚠️ Chunk {idx} translation failed (attempt {attempt+1}): {e}")
                time.sleep(2)  # wait before retry
        else:
            raise RuntimeError(f"Translation failed for chunk {idx} after 3 retries")

    return " ".join(translated_chunks)



def fetch_youtube_transcript(video_id: str, target_lang="en") -> str:
    """
    Fetch the transcript of a YouTube video in English.
    - Checks if transcript is available
    - Lists available languages
    - Translates to English if needed
    Returns: List of transcript snippets [{'text': ..., 'start': ..., 'duration': ...}, ...]
    """

    ytt_api = YouTubeTranscriptApi()

    try:
        transcript_list = ytt_api.list(video_id)
    except NoTranscriptFound:
        print("❌ No transcript available for this video")
        return None
    
    # Print available languages
    print("Available transcripts for this video:")
    for transcript in transcript_list:
        print(
            f"- Language: {transcript.language} ({transcript.language_code}) | "
            f"Generated: {transcript.is_generated} | "
            f"Translatable: {transcript.is_translatable}"
        )

    # Try to find English transcript first
    try:
        transcript = transcript_list.find_transcript(['en'])
        print("\n✅ English transcript found.")
        fetched = transcript.fetch()
        return fetched.to_raw_data()
    except:
        # If no English, pick the first available and translate
        transcript = transcript_list[0]
        if transcript.is_translatable:
            print(f"\n✅ Translating {transcript.language} -> English via YouTube")
            translated = transcript.translate('en').fetch()
            return translated.to_raw_data()
        else:
             # 3️⃣ Use Google Translate as fallback
            print(f"\n {transcript.language} transcript not translatable via YouTube. Using Google Translate...")
            fetched = transcript.fetch()
            translated = []
            translator = GoogleTranslator(source=transcript.language_code, target='en')
            for snippet in fetched:
                translated.append({
                    'text': translator.translate(snippet.text),
                    'start': snippet.start,
                    'duration': snippet.duration
                })
            return translated