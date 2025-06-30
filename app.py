import os
import re
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Import library dari pihak ketiga
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
from youtube_transcript_api._errors import TranscriptsDisabled, RequestBlocked

# Import dari file lokal Anda
from auth import require_custom_authentication

# 1. Muat environment variables dari file .env (Harus di paling atas)
load_dotenv()

# 2. Inisialisasi Aplikasi Flask dan Logging
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 3. Konfigurasi Google Gemini API
try:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("Variabel GOOGLE_API_KEY tidak ditemukan di environment.")
    
    genai.configure(api_key=api_key)
    
    system_instruction = """You are a helpful assistant that improves text formatting and adds punctuation.
You will be given texts from YouTube transcriptions and your task is to apply good formatting.
Do NOT modify individual words. Your output should only be the corrected text."""

    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        system_instruction=system_instruction
    )
except Exception as e:
    logger.error(f"Gagal mengkonfigurasi Gemini API: {e}")
    model = None

# 4. Definisi Fungsi-Fungsi Pembantu

def get_youtube_id(url):
    """Mengekstrak ID video dari URL YouTube."""
    video_id = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    return video_id.group(1) if video_id else None

def process_transcript(video_id):
    """Mengambil transkrip dari YouTube menggunakan metode Webshare yang andal."""
    proxy_user = os.environ.get("WEBSHARE_USER")
    proxy_pass = os.environ.get("WEBSHARE_PASS")

    # FIX: Menambahkan logging untuk memastikan kredensial terbaca dengan benar
    logger.info(f"Mencoba menggunakan kredensial Webshare. User: '{proxy_user}'")

    # Jika kredensial proxy tidak ada, server akan gagal dengan error yang jelas.
    if not (proxy_user and proxy_pass):
        logger.error("Kredensial WEBSHARE_USER atau WEBSHARE_PASS tidak ditemukan!")
        raise Exception("Konfigurasi proxy server tidak lengkap.")
        
    # Membuat objek API dengan konfigurasi proxy Webshare
    ytt_api = YouTubeTranscriptApi(
        proxy_config=WebshareProxyConfig(
            proxy_username=proxy_user,
            proxy_password=proxy_pass,
        )
    )
        
    logger.info(f"Mencoba mengambil transkrip untuk video {video_id} melalui Webshare...")
    transcript_list = ytt_api.get_transcript(video_id)

    full_text = ' '.join([entry['text'] for entry in transcript_list])
    return full_text

def improve_text_with_gemini(text):
    """Memperbaiki format teks menggunakan Gemini."""
    # FIX: Pengecekan 'genai.api_key' dihapus karena tidak valid.
    # Pengecekan 'not model' sudah cukup untuk memastikan konfigurasi berhasil.
    if not model:
        raise Exception("Konfigurasi Gemini API tidak lengkap atau gagal.")

    try:
        response = model.generate_content(text)
        return response.text
    except Exception as e:
        logger.error(f"Terjadi error saat panggilan ke API Gemini: {e}")
        # Meneruskan error ke blok penanganan utama
        raise e

# 5. Endpoint Utama Aplikasi

@app.route('/transcribe', methods=['POST'])
@require_custom_authentication
def transcribe():
    youtube_url = request.json.get('url')
    if not youtube_url:
        return jsonify({"error": "No YouTube URL provided"}), 400

    video_id = get_youtube_id(youtube_url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    try:
        logger.info(f"Processing video_id = {video_id}")
        
        transcript_text = process_transcript(video_id)
        logger.info(f"Panjang transkrip asli: {len(transcript_text)} karakter")

        improved_text = improve_text_with_gemini(transcript_text)

        return jsonify({"result": improved_text})

  # Penanganan error yang lebih baik dan spesifik
    except TranscriptsDisabled:
        error_message = f"Subtitles are disabled for video: {video_id}"
        logger.warning(error_message)
        return jsonify({"error": error_message}), 400
        
    except RequestBlocked:
        error_message = f"Request was blocked by YouTube for video: {video_id}. Proxy may be blacklisted."
        logger.error(error_message)
        return jsonify({"error": error_message}), 503 # Service Unavailable
    
    except Exception as e:
        logger.exception(f"Terjadi error yang tidak terduga: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# 6. Menjalankan Server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
