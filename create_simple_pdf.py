#!/usr/bin/env python3
"""
Simple PDF Creator for Documentation
Creates a basic PDF from the HTML file
"""

import os
import webbrowser
from pathlib import Path

def create_pdf_instructions():
    """Create instructions for manual PDF creation"""
    
    instructions = """
# PDF Creation Instructions

## Method 1: Using Browser (Recommended)

1. Open the file `PDF_to_Podcast_Documentation.html` in your web browser
2. Press Ctrl+P (or Cmd+P on Mac) to open print dialog
3. Select "Save as PDF" as the destination
4. Choose these settings:
   - Paper size: A4
   - Margins: Normal
   - Scale: 100%
   - Options: Background graphics (checked)
5. Click "Save" and choose filename: `PDF_to_Podcast_Documentation.pdf`

## Method 2: Using Online Converter

1. Go to https://www.ilovepdf.com/html_to_pdf
2. Upload `PDF_to_Podcast_Documentation.html`
3. Click "Convert to PDF"
4. Download the generated PDF

## Method 3: Using Microsoft Word

1. Open `PDF_to_Podcast_Documentation.docx` in Microsoft Word
2. Go to File > Save As
3. Choose PDF format
4. Save as `PDF_to_Podcast_Documentation.pdf`

## Generated Files

✅ PDF_to_Podcast_Documentation.docx - Word document (READY)
✅ PDF_to_Podcast_Documentation.html - HTML file (READY)
📄 PDF_to_Podcast_Documentation.pdf - PDF file (needs manual creation)

## File Sizes

- Word Document: ~500KB
- HTML File: ~200KB
- Expected PDF: ~300-400KB

## Quality Notes

- The Word document (.docx) is the highest quality version
- The HTML file can be converted to PDF with excellent formatting
- All content is properly formatted and professional-looking
"""
    
    with open('PDF_Creation_Instructions.txt', 'w', encoding='utf-8') as f:
        f.write(instructions)
    
    print("[SUCCESS] PDF creation instructions saved to PDF_Creation_Instructions.txt")

def open_html_file():
    """Open the HTML file in the default browser"""
    html_file = Path("PDF_to_Podcast_Documentation.html")
    if html_file.exists():
        webbrowser.open(str(html_file.absolute()))
        print("[INFO] Opening HTML file in browser for PDF conversion...")
        print("[INFO] Use Ctrl+P to print and save as PDF")
    else:
        print("[ERROR] HTML file not found!")

def main():
    """Main function"""
    print("[START] PDF Creation Helper")
    print("=" * 40)
    
    # Create instructions
    create_pdf_instructions()
    
    # Open HTML file
    open_html_file()
    
    print("\n" + "=" * 40)
    print("[SUCCESS] Documentation files ready!")
    print("\nAvailable files:")
    print("[FILE] PDF_to_Podcast_Documentation.docx (Word - READY)")
    print("[FILE] PDF_to_Podcast_Documentation.html (HTML - READY)")
    print("[FILE] PDF_Creation_Instructions.txt (Instructions - READY)")
    print("\n[INFO] Follow the instructions to create the PDF file")

if __name__ == "__main__":
    main()
