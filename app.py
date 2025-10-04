"""
Production WSGI entry point for PDF to Podcast Generator
This file is required for deployment with gunicorn
"""

from server import app

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
