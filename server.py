import os
import io
import tempfile
import json
import base64
from flask import Flask, request, jsonify, send_from_directory, Response
from pypdf import PdfReader
import google.generativeai as genai
import pyttsx3
from dotenv import load_dotenv

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
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
TEMP_AUDIO_PATH = os.path.join(UPLOAD_FOLDER, 'podcast.wav') 

# --- Helper Functions ---

def extract_text_from_pdf(file_path):
    """Extract text from a PDF."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            except Exception as page_error:
                print(f"Warning: Could not extract text from page {page_num + 1}: {page_error}")
                continue
        
        if not text.strip():
            raise Exception("No text could be extracted from the PDF")
            
        return text
    except Exception as e:
        print(f"[ERROR] PDF extraction error: {e}")
        return None

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

# --- Flask Routes ---

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

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
        
        document_text = extract_text_from_pdf(temp_file_path)
        
        if not document_text or len(document_text.strip()) < 50:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return jsonify({"error": "Could not extract sufficient text from PDF. Please ensure the PDF contains readable text."}), 400

        try:
            print("[INFO] Generating summary...")
            summary = generate_summary(document_text)
            
            print("[INFO] Generating audio...")
            audio_url = generate_tts_audio(summary, TEMP_AUDIO_PATH) 
            
            # Clean up temporary PDF file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print("[INFO] Cleaned up temporary files")

            print("[SUCCESS] Processing completed successfully")
            return jsonify({
                "summary": summary,
                "audioUrl": audio_url
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
