#!/usr/bin/env python3
"""
Render.com startup script for PDF to Podcast Generator
Handles port binding and environment setup
"""

import os
import sys

def main():
    """Start the application for Render deployment."""
    port = os.environ.get('PORT', 5000)
    
    print(f"[RENDER] Starting PDF to Podcast Generator on port {port}")
    print(f"[RENDER] Environment: {os.environ.get('RENDER', 'Unknown')}")
    
    try:
        # Import and run the app
        from app import app
        app.run(host='0.0.0.0', port=int(port), debug=False)
    except Exception as e:
        print(f"[ERROR] Failed to start application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()




