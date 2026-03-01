# AVIF Mini - Forensic-Aware Image Compressor

Sleek, premium image optimizer built for AI image detection pipelines.

## Features
- **Forensic-Aware Logic**: Preserves ML features (noise/artifacts) while reducing file size.
- **HEIC/HEIF Support**: Native support for iPhone photos via `pillow-heif`.
- **Automatic Optimization**: No manual tweaking needed; intelligent thresholds based on input format.
- **AVIF Conversion**: Highly efficient next-gen compression.
- **Glassmorphic UI**: Premium dark-mode interface.

## Quick Start
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the server:
   ```bash
   python app.py
   ```
3. Open [http://localhost:5001](http://localhost:5001) in your browser.

## Tech Stack
- **Backend**: Flask
- **Processing**: Pillow + pillow-heif
- **Frontend**: Vanilla HTML/CSS/JS (Glassmorphic Design)

Crafted for Ishan & Antigravity.
