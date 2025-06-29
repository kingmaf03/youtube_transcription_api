from functools import wraps
from flask import request, jsonify
import os
import logging

# Dapatkan logger yang sudah dikonfigurasi di app.py
logger = logging.getLogger(__name__)

def require_custom_authentication(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Ambil custom header dan secret code
        custom_header = request.headers.get('X-YTAPI-Secret')
        secret_code = os.environ.get('SECRET_CODE')

        # --- BAGIAN DEBUGGING BARU ---
        # Kita akan mencatat nilai yang diterima dan yang diharapkan ke log
        logger.info("--- Authentication Check ---")
        logger.info(f"Header diterima dari Make.com ('X-YTAPI-Secret'): '{custom_header}'")
        logger.info(f"Secret diharapkan dari Render Env ('SECRET_CODE'): '{secret_code}'")
        # ---------------------------

        # Lakukan pengecekan
        if not secret_code:
            logger.error("FATAL: Variabel SECRET_CODE tidak diatur di lingkungan Render!")
            return jsonify({"error": "Server configuration error"}), 500

        if custom_header != secret_code:
            logger.warning("Authentication FAILED: Header tidak cocok dengan secret code.")
            return jsonify({"error": "Unauthorized"}), 401
        
        logger.info("Authentication SUCCESS: Header cocok!")
        return f(*args, **kwargs)
    
    return decorated_function


# def require_custom_authentication(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         # Get the custom header and secret code
#         custom_header = request.headers.get('X-YTAPI-Secret')
#         secret_code = os.environ.get('SECRET_CODE')

#         # Check if the header is present and matches the secret code
#         if custom_header != secret_code:
#             return jsonify({"error": "Unauthorized"}), 401
        
#         return f(*args, **kwargs)
    
#     return decorated_function