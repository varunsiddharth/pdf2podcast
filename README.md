# PDF to Podcast Generator

Transform any PDF document into an engaging audio podcast using AI technology.

## Features

- 📄 **PDF Text Extraction**: Automatically extracts text from PDF files
- 🤖 **AI Summarization**: Uses Google's Gemini AI to create concise summaries
- 🎵 **Text-to-Speech**: Converts summaries into natural-sounding audio
- 🎨 **Modern UI**: Beautiful, responsive web interface
- 📱 **Mobile Friendly**: Works on all devices

## Setup Instructions

### 1. Install Dependencies

```bash
# Install required Python packages
pip install -r requirements.txt
```

### 2. Set Up API Key

The application uses a `.env` file for configuration. You have two options:

#### Option A: Use the provided .env file (Quick Start)
The project includes a `.env` file with a working API key for testing.

#### Option B: Use your own API key (Recommended for production)
1. Get your Gemini API key from: https://makersuite.google.com/app/apikey
2. Edit the `.env` file and replace the API key:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

#### Option C: Set environment variable directly
```bash
# Windows
set GEMINI_API_KEY=your_api_key_here

# Linux/Mac
export GEMINI_API_KEY=your_api_key_here
```

### 3. Start the Server

```bash
# Option 1: Use the startup script (recommended)
python start_server.py

# Option 2: Run directly
python server.py
```

### 4. Open in Browser

Navigate to: http://127.0.0.1:5000

## Usage

1. **Upload PDF**: Drag and drop or click to select a PDF file
2. **Process**: Click "Process PDF" to start conversion
3. **Listen**: Play the generated audio podcast
4. **Download**: Save the audio file to your device

## Requirements

- Python 3.7+
- Flask
- pypdf
- google-generativeai

## Troubleshooting

### Common Issues

1. **"Gemini client not initialized"**
   - Check your API key is valid
   - Ensure you have internet connection

2. **"Could not extract text from PDF"**
   - Ensure the PDF contains readable text (not just images)
   - Try with a different PDF file

3. **"Processing failed"**
   - Check server logs for detailed error messages
   - Ensure all dependencies are installed

### File Size Limits

- Maximum PDF size: 50MB
- Supported formats: PDF only

## Technical Details

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **AI Service**: Google Gemini API
- **Audio Format**: WAV (16-bit PCM)

## Deployment

### Local Development
```bash
python start_server.py
```

### Production Deployment

#### Using Gunicorn
```bash
gunicorn app:app --config gunicorn.conf.py
```

#### Using Docker
```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
```

#### Environment Variables for Production
Set these environment variables in your production environment:
- `GEMINI_API_KEY`: Your Google Gemini API key
- `PORT`: Port number (default: 5000)
- `FLASK_ENV`: Set to `production`
- `WEB_CONCURRENCY`: Number of worker processes (default: 2)

### Deployment Platforms

#### Render.com
1. Connect your GitHub repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Add environment variable: `GEMINI_API_KEY`
5. Set Python version: `3.13.4`

#### Heroku
1. Create a Heroku app
2. Set environment variables:
   ```bash
   heroku config:set GEMINI_API_KEY=your_api_key_here
   ```
3. Deploy:
   ```bash
   git push heroku main
   ```

#### Railway
1. Connect your repository
2. Set environment variables in dashboard
3. Deploy automatically

## License

This project is for educational and personal use.
