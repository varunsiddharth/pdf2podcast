import os
import io
import tempfile
import json
import base64
from flask import Flask, request, jsonify, send_from_directory, Response, session
from pypdf import PdfReader
import google.generativeai as genai
import pyttsx3
from dotenv import load_dotenv
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

# --- Configuration ---
# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
api_key = os.environ.get('GEMINI_API_KEY')
model = None

if not api_key:
    print("[WARN] GEMINI_API_KEY not found in environment variables.")
    print("[INFO] Proceeding with basic (non-AI) summary fallback. To enable AI, set GEMINI_API_KEY in a .env file.")
else:
    # Configure the Gemini API
    genai.configure(api_key=api_key)
    try:
        # Initialize the model - try different model names
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            print("[SUCCESS] Gemini client initialized with gemini-1.5-flash")
        except:
            try:
                model = genai.GenerativeModel('gemini-1.5-pro')
                print("[SUCCESS] Gemini client initialized with gemini-1.5-pro")
            except:
                model = genai.GenerativeModel('gemini-pro')
                print("[SUCCESS] Gemini client initialized with gemini-pro")
    except Exception as e:
        print(f"[ERROR] Error initializing Gemini Client: {e}")
        print(f"[ERROR] Please check your GEMINI_API_KEY in the .env file")
        model = None

# --- App Setup ---
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
TEMP_AUDIO_PATH = os.path.join(UPLOAD_FOLDER, 'podcast.wav') 

# Optional: allow configuring the Tesseract binary path via env
tesseract_cmd = os.environ.get('TESSERACT_CMD')
if tesseract_cmd:
    try:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        print(f"[INFO] Using custom Tesseract at: {tesseract_cmd}")
    except Exception as _tess_err:
        print(f"[WARN] Failed to set custom Tesseract path: {_tess_err}")

# --- Simple in-memory progress tracking ---
progress_store = {}

def _get_user_folder() -> str:
    user_id = session.get('user_id', 'anonymous')
    folder = os.path.join(UPLOAD_FOLDER, user_id)
    os.makedirs(folder, exist_ok=True)
    return folder

def _update_progress(job_id: str, status: str, detail: str = "") -> None:
    progress_store[job_id] = {"status": status, "detail": detail}

def _get_summary_targets(length_key: str):
    # Map UI choices to word targets
    length_map = {
        'short': (480, 650),   # ~500 words
        'medium': (900, 1100), # ~1000 words
        'long': (1500, 2000),  # ~1500–2000 words
    }
    return length_map.get((length_key or '').lower(), (1500, 2000))

# --- Helper Functions ---

def extract_text_from_pdf_pypdf(file_path):
    """Try extracting text with pypdf."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            except Exception as page_error:
                print(f"[WARN] pypdf: Could not extract text from page {page_num + 1}: {page_error}")
                continue
        return text.strip()
    except Exception as e:
        print(f"[ERROR] pypdf extraction error: {e}")
        return ""

def extract_text_from_pdf_pymupdf(file_path):
    """Try extracting selectable text using PyMuPDF (faster and often more reliable than pypdf)."""
    try:
        doc = fitz.open(file_path)
        text_chunks = []
        for page_index in range(len(doc)):
            try:
                page = doc.load_page(page_index)
                page_text = page.get_text("text") or ""
                if page_text.strip():
                    text_chunks.append(page_text)
            except Exception as page_error:
                print(f"[WARN] PyMuPDF text: Could not extract text from page {page_index + 1}: {page_error}")
                continue
        doc.close()
        return ("\n".join(text_chunks)).strip()
    except Exception as e:
        print(f"[ERROR] PyMuPDF text extraction error: {e}")
        return ""

def extract_text_from_pdf_ocr(file_path, dpi=200):
    """Extract text by rendering pages to images and running OCR with pytesseract."""
    try:
        doc = fitz.open(file_path)
        ocr_chunks = []
        for page_index in range(len(doc)):
            try:
                page = doc.load_page(page_index)
                pix = page.get_pixmap(dpi=dpi, alpha=False)
                img_bytes = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_bytes))
                try:
                    text = pytesseract.image_to_string(image)
                except Exception as ocr_err:
                    print(f"[ERROR] OCR failed on page {page_index + 1}: {ocr_err}")
                    text = ""
                if text and text.strip():
                    ocr_chunks.append(text)
            except Exception as page_error:
                print(f"[WARN] OCR: Could not process page {page_index + 1}: {page_error}")
                continue
        doc.close()
        return ("\n".join(ocr_chunks)).strip()
    except Exception as e:
        print(f"[ERROR] OCR extraction error: {e}")
        return ""

def extract_text_from_pdf(file_path):
    """Hybrid extractor: pypdf → PyMuPDF text → OCR fallback (per doc)."""
    # 1) Try pypdf
    text = extract_text_from_pdf_pypdf(file_path)
    if len(text) >= 200:
        return text

    # 2) Try PyMuPDF selectable text
    mu_text = extract_text_from_pdf_pymupdf(file_path)
    if len(mu_text) >= 200:
        # Merge both if both exist (to keep any extras)
        combined = (text + "\n" + mu_text).strip() if text else mu_text
        return combined

    # 3) OCR fallback
    print("[INFO] Falling back to OCR for PDF text extraction...")
    ocr_text = extract_text_from_pdf_ocr(file_path)
    if len(ocr_text) >= 50:
        combined = "\n".join([t for t in [text, mu_text, ocr_text] if t and t.strip()])
        return combined.strip()

    # Nothing usable
    return (text or mu_text or ocr_text or "").strip()

def _normalize_text_for_dedupe(text: str) -> str:
    # Lowercase, collapse whitespace, strip
    return " ".join((text or "").lower().split())

def _clean_trailing_duplicates(text: str) -> str:
    """Remove duplicated trailing sentences/phrases and ensure a clean single ending."""
    if not text:
        return text
    import re
    raw = text.strip()
    # Split into sentences conservatively; keep punctuation
    sentences = re.findall(r"[^.!?\n]+[.!?]+|[^.!?\n]+$", raw)
    if not sentences:
        cleaned = raw
    else:
        # Remove repeated trailing duplicates (case/space-insensitive)
        while len(sentences) >= 2:
            last = sentences[-1].strip()
            prev = sentences[-2].strip()
            if _normalize_text_for_dedupe(last) == _normalize_text_for_dedupe(prev):
                sentences.pop()
            else:
                break
        cleaned = " ".join(s.strip() for s in sentences).strip()
    # Normalize ending punctuation to a single period
    cleaned = re.sub(r"[.!?]+\s*$", ".", cleaned).strip()
    return cleaned

def extract_text_chunks_from_pdf(file_path, pages_per_chunk=10):
    """Extract text in chunks of N pages.
    Per page: try selectable text first; only run OCR if empty.
    Removes duplicate page texts and duplicate chunk texts to reduce repetition.
    """
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        print(f"[ERROR] Unable to open PDF for chunking: {e}")
        return []

    total_pages = len(doc)
    chunks = []
    current_chunk = []
    seen_page_hashes = set()

    for page_index in range(total_pages):
        page_text = ""
        try:
            page = doc.load_page(page_index)
            # 1) selectable text
            page_text = (page.get_text("text") or "").strip()
            # 2) OCR only if empty
            if not page_text:
                try:
                    pix = page.get_pixmap(dpi=200, alpha=False)
                    img_bytes = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_bytes))
                    page_text = (pytesseract.image_to_string(image) or "").strip()
                except Exception as ocr_err:
                    print(f"[WARN] OCR failed on page {page_index + 1}: {ocr_err}")
                    page_text = ""
        except Exception as page_err:
            print(f"[WARN] Could not process page {page_index + 1}: {page_err}")
            page_text = ""

        # De-duplicate identical page texts
        if page_text:
            ph = _normalize_text_for_dedupe(page_text)
            if ph and ph not in seen_page_hashes:
                seen_page_hashes.add(ph)
                current_chunk.append(page_text)

        # push chunk boundary at every N pages
        if (page_index + 1) % pages_per_chunk == 0:
            chunk_text = "\n".join(current_chunk).strip()
            if chunk_text:
                chunks.append(chunk_text)
            current_chunk = []

    # remaining pages
    if current_chunk:
        chunk_text = "\n".join(current_chunk).strip()
        if chunk_text:
            chunks.append(chunk_text)

    doc.close()

    # Remove duplicate chunk texts
    unique_chunks = []
    seen_chunk_hashes = set()
    for ch in chunks:
        h = _normalize_text_for_dedupe(ch)
        if h and h not in seen_chunk_hashes:
            seen_chunk_hashes.add(h)
            unique_chunks.append(ch)

    return unique_chunks

def generate_summary_for_chunk(text, chunk_index=None, total_chunks=None):
    """Summarize a chunk; fallback to truncated text if model unavailable."""
    if not text or not text.strip():
        return ""
    if not model:
        # basic fallback: first 400 words as a pseudo-summary
        words = text.split()[:400]
        return " ".join(words)

    tag = f" (Part {chunk_index + 1} of {total_chunks})" if chunk_index is not None and total_chunks is not None else ""
    prompt = (
        "You are summarizing a long document in parts" + tag + ".\n"
        "Write a clear, structured summary that captures key arguments, evidence, definitions, data, and action items.\n"
        "Prefer bullet points for lists, and short paragraphs for narratives.\n"
        "Avoid repetition; keep names and terms consistent.\n\n"
        "Chunk content follows:\n" + text
    )

    try:
        response = model.generate_content(prompt)
        if response and hasattr(response, 'text') and response.text:
            return response.text.strip()
    except Exception as e:
        print(f"[ERROR] Chunk summary failed: {e}")

    # fallback
    words = text.split()[:400]
    return " ".join(words)

def generate_final_summary_from_chunks(chunk_summaries, target_min_words=1500, target_max_words=2000, source_chunks=None):
    """Combine chunk summaries into one clean 1500–2000 word synthesis without repetition."""
    # 1) Drop empty and duplicate summaries
    cleaned = []
    seen = set()
    for cs in chunk_summaries:
        if not cs or not cs.strip():
            continue
        key = _normalize_text_for_dedupe(cs)
        if key and key not in seen:
            seen.add(key)
            cleaned.append(cs.strip())

    joined = "\n\n".join(cleaned)
    if not joined:
        return ""

    if not model:
        # Fallback: take unique sentences from summaries; if too short, augment from source chunks
        import re
        sentences = re.split(r"(?<=[.!?])\s+", joined)
        uniq_sent = []
        sent_seen = set()
        for s in sentences:
            k = _normalize_text_for_dedupe(s)
            if k and k not in sent_seen:
                sent_seen.add(k)
                uniq_sent.append(s.strip())
        text_accum = " ".join(uniq_sent).strip()

        # If not enough words, try to augment from original chunk text (deduped sentences)
        if source_chunks and len(text_accum.split()) < target_min_words:
            src_joined = "\n\n".join(source_chunks)
            src_sentences = re.split(r"(?<=[.!?])\s+", src_joined)
            for s in src_sentences:
                k = _normalize_text_for_dedupe(s)
                if k and k not in sent_seen:
                    sent_seen.add(k)
                    uniq_sent.append(s.strip())
                if len(" ".join(uniq_sent).split()) >= target_min_words:
                    break

        words = (" ".join(uniq_sent)).split()
        # Enforce lower and upper bounds
        if len(words) < target_min_words:
            target = len(words)
        else:
            target = min(target_max_words, len(words))
        fallback_text = " ".join(words[:target])
        return _clean_trailing_duplicates(fallback_text)

    synthesis_prompt = (
        "You are given multiple section summaries from a long PDF.\n"
        f"Write ONE cohesive, non-repetitive summary of {target_min_words}–{target_max_words} words.\n"
        "Strictly avoid repeating the same facts, sentences, or lists.\n"
        "Merge overlapping content, keep terminology consistent, and maintain a logical structure.\n"
        "Use short headings when natural, bullet lists only for enumerations, and concise paragraphs.\n"
        "Finish with a short set of actionable takeaways.\n\n"
        "Section summaries (may overlap):\n" + joined
    )

    try:
        response = model.generate_content(synthesis_prompt)
        if response and hasattr(response, 'text') and response.text:
            txt = response.text.strip()
            w = txt.split()
            # If too short, augment from chunk summaries and optionally source chunks
            if len(w) < target_min_words:
                import re
                # add deduped sentences from chunk summaries
                add_pool = "\n\n".join(chunk_summaries)
                sentences = re.split(r"(?<=[.!?])\s+", add_pool)
                seen = set(_normalize_text_for_dedupe(t) for t in w)
                for s in sentences:
                    k = _normalize_text_for_dedupe(s)
                    if k and k not in seen:
                        w.extend(s.strip().split())
                        seen.add(k)
                    if len(w) >= target_min_words:
                        break
                # still short? try raw source chunks
                if source_chunks and len(w) < target_min_words:
                    src_pool = "\n\n".join(source_chunks)
                    sentences = re.split(r"(?<=[.!?])\s+", src_pool)
                    for s in sentences:
                        k = _normalize_text_for_dedupe(s)
                        if k and k not in seen:
                            w.extend(s.strip().split())
                            seen.add(k)
                        if len(w) >= target_min_words:
                            break
            # Enforce upper bound to reflect chosen length
            if len(w) > target_max_words:
                w = w[:target_max_words]
            return _clean_trailing_duplicates(" ".join(w))
    except Exception as e:
        print(f"[ERROR] Final synthesis failed: {e}")

    # final fallback: take unique sentences up to target_max_words
    import re
    sentences = re.split(r"(?<=[.!?])\s+", joined)
    uniq_sent = []
    sent_seen = set()
    for s in sentences:
        k = _normalize_text_for_dedupe(s)
        if k and k not in sent_seen:
            sent_seen.add(k)
            uniq_sent.append(s.strip())
    words = (" ".join(uniq_sent)).split()
    return _clean_trailing_duplicates(" ".join(words[:target_max_words]))

def generate_summary(text):
    """Generate summary using Gemini API."""
    if not model:
        raise Exception("Gemini client not initialized. Check API key.")
    
    prompt = f"Create a comprehensive summary of the following document that would be suitable for an engaging audio podcast. Please provide a detailed summary that captures all the key points and main ideas. Make it informative and complete:\n\n{text}"
    
    try:
        print(f"[INFO] Sending request to Gemini API...")
        response = model.generate_content(prompt)
        print(f"[INFO] Gemini API response received")
        
        if response and hasattr(response, 'text'):
            print(f"[SUCCESS] Generated summary length: {len(response.text)} characters")
            return response.text
        else:
            print(f"[ERROR] No response text in Gemini API response")
            raise Exception("No response text received from Gemini API")
    except Exception as e:
        print(f"[ERROR] Gemini API error details: {e}")
        print(f"[ERROR] Error type: {type(e).__name__}")
        # Fallback: return a longer summary without truncation
        words = text.split()[:500]  # First 500 words for better fallback
        return " ".join(words) + "\n\n[This is a basic summary of your document. For a more detailed AI-generated summary, please check your API configuration.]"

def write_wav_header(stream, pcm_data_length, sample_rate):
    """Writes the WAV header to a stream."""
    stream.write(b'RIFF')
    stream.write((pcm_data_length + 36).to_bytes(4, 'little'))
    stream.write(b'WAVE')
    stream.write(b'fmt ')
    stream.write((16).to_bytes(4, 'little'))
    stream.write((1).to_bytes(2, 'little'))
    stream.write((1).to_bytes(2, 'little'))
    stream.write(int(sample_rate).to_bytes(4, 'little'))
    byte_rate = int(sample_rate) * 1 * (16 // 8)
    stream.write(int(byte_rate).to_bytes(4, 'little'))
    block_align = 1 * (16 // 8)
    stream.write(int(block_align).to_bytes(2, 'little'))
    stream.write((16).to_bytes(2, 'little'))
    stream.write(b'data')
    stream.write(pcm_data_length.to_bytes(4, 'little'))

def generate_tts_audio(text, output_path):
    """Generate TTS audio using pyttsx3 (offline TTS)."""
    try:
        print(f"[INFO] TTS Request: Converting {len(text)} characters to speech...")
        
        # Initialize the TTS engine
        engine = pyttsx3.init()
        
        # Configure voice properties
        voices = engine.getProperty('voices')
        if voices:
            # Try to use a female voice if available
            for voice in voices:
                if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break
        
        # Set speech rate and volume
        engine.setProperty('rate', 150)  # Speed of speech
        engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)
        
        # Generate output file path
        output_wav_path = output_path.replace('.mp3', '.wav')
        
        # Save to file
        engine.save_to_file(text, output_wav_path)
        engine.runAndWait()
        
        # Check if file was created successfully
        if not os.path.exists(output_wav_path):
            raise Exception("TTS audio file was not created")
        
        print(f"[SUCCESS] Generated TTS audio: {output_wav_path}")
        return f'/{UPLOAD_FOLDER}/{os.path.basename(output_wav_path)}'
        
    except Exception as e:
        print(f"[ERROR] TTS generation error: {e}")
        # Fallback: create a simple audio file
        try:
            print("[INFO] Using fallback audio generation...")
            sample_rate = 24000
            duration_seconds = max(3, len(text) / 50)
            num_samples = int(sample_rate * duration_seconds)
            silence_data = b'\x00' * (num_samples * 2)
            
            output_wav_path = output_path.replace('.mp3', '.wav')
            with open(output_wav_path, 'wb') as f:
                write_wav_header(f, len(silence_data), sample_rate)
                f.write(silence_data)
            
            print(f"[SUCCESS] Generated fallback audio: {output_wav_path}")
            return f'/{UPLOAD_FOLDER}/{os.path.basename(output_wav_path)}'
        except Exception as fallback_error:
            print(f"[ERROR] Fallback TTS also failed: {fallback_error}")
            raise Exception(f"TTS generation failed: {e}")

def save_text_summary(text: str, job_id: str) -> str:
    folder = _get_user_folder()
    path = os.path.join(folder, f"{job_id}_summary.txt")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    # static route available via send_from_directory at '/<path>'
    return f"/{os.path.relpath(path).replace('\\', '/')}"

def save_pdf_summary(text: str, job_id: str) -> str:
    folder = _get_user_folder()
    path = os.path.join(folder, f"{job_id}_summary.pdf")
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(36, 36, 559, 806)
    page.insert_textbox(rect, text, fontsize=11, lineheight=1.2)
    doc.save(path)
    doc.close()
    return f"/{os.path.relpath(path).replace('\\', '/')}"

# --- Flask Routes ---

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    if not username:
        return jsonify({"error": "Username required"}), 400
    session['user_id'] = username
    _ = _get_user_folder()
    return jsonify({"ok": True, "user": username})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"ok": True})

@app.route('/api/me', methods=['GET'])
def me():
    return jsonify({"user": session.get('user_id', 'anonymous')})

@app.route('/api/status/<job_id>', methods=['GET'])
def status(job_id):
    return jsonify(progress_store.get(job_id, {"status": "unknown", "detail": ""}))

@app.route('/api/process-pdf', methods=['POST'])
def process_pdf():
    if 'pdfFile' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    pdf_file = request.files['pdfFile']
    
    if pdf_file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if pdf_file and pdf_file.filename.endswith('.pdf'):
        temp_file_path = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
        pdf_file.save(temp_file_path)
        # Default medium length (~1000 words) now that dropdown is removed
        length_choice = 'medium'
        min_words, max_words = _get_summary_targets(length_choice)
        import uuid
        job_id = str(uuid.uuid4())
        _update_progress(job_id, 'received', 'PDF uploaded')

        # Prefer chunked extraction so we can summarize large docs progressively
        _update_progress(job_id, 'extracting', 'Extracting text and running OCR when needed')
        chunks = extract_text_chunks_from_pdf(temp_file_path, pages_per_chunk=10)
        # If chunking failed, fallback to whole-document extraction
        if not chunks:
            whole_text = extract_text_from_pdf(temp_file_path)
            if not whole_text or len(whole_text.strip()) < 50:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                return jsonify({
                    "error": "Could not extract sufficient text from PDF.",
                    "hint": "If your PDF is scanned/image-based, install Tesseract OCR and set TESSERACT_CMD env to its binary path."
                }), 400
            chunks = [whole_text]

        try:
            # Summarize each chunk
            print(f"[INFO] Summarizing {len(chunks)} chunk(s)...")
            _update_progress(job_id, 'summarizing', f'Summarizing {len(chunks)} chunk(s)')
            chunk_summaries = []
            for idx, chunk_text in enumerate(chunks):
                cs = generate_summary_for_chunk(chunk_text, chunk_index=idx, total_chunks=len(chunks))
                chunk_summaries.append(cs)

            # Synthesize final long summary
            print("[INFO] Generating final synthesis...")
            _update_progress(job_id, 'synthesizing', 'Combining chunk summaries')
            final_summary = generate_final_summary_from_chunks(
                chunk_summaries,
                target_min_words=min_words,
                target_max_words=max_words,
                source_chunks=chunks
            )

            print("[INFO] Generating audio...")
            _update_progress(job_id, 'audio', 'Generating audio file')
            audio_url = generate_tts_audio(final_summary, TEMP_AUDIO_PATH)

            text_url = save_text_summary(final_summary, job_id)
            pdf_url = save_pdf_summary(final_summary, job_id)

            # Clean up temporary PDF file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print("[INFO] Cleaned up temporary files")

            print("[SUCCESS] Processing completed successfully")
            _update_progress(job_id, 'done', 'Completed')
            return jsonify({
                "summary": final_summary,
                "chunkSummaries": chunk_summaries,
                "audioUrl": audio_url,
                "textUrl": text_url,
                "pdfUrl": pdf_url,
                "jobId": job_id,
                "length": {
                    "choice": length_choice,
                    "targetMin": min_words,
                    "targetMax": max_words
                }
            })

        except Exception as e:
            print(f"[ERROR] Processing failed: {e}")
            # Clean up on error
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return jsonify({"error": str(e)}), 500

    else:
        return jsonify({"error": "Invalid file type, only PDF files are allowed."}), 400

@app.route(f'/{UPLOAD_FOLDER}/<filename>')
def serve_audio(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
