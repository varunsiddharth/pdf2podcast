#!/usr/bin/env python3
"""
PDF to Podcast Generator - Startup Script
This script starts the Flask server with proper configuration.
"""

import os
import sys
from server import app

def main():
    """Start the Flask development server."""
    print("[STARTUP] Starting PDF to Podcast Generator...")
    print("[INFO] Working directory:", os.getcwd())
    print("[INFO] Server will be available at: http://127.0.0.1:5000")
    print("[INFO] Upload a PDF file to convert it to a podcast!")
    print("-" * 50)
    
    try:
        app.run(debug=True, port=5000, host='127.0.0.1')
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user")
    except Exception as e:
        print(f"[ERROR] Server error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
