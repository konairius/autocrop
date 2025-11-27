# Autocrop

A Python script to automatically crop and orient sub-images from a single image or a PDF file.

## Description

This script processes an input file (either an image or a PDF) and identifies distinct sub-images within it. For each sub-image, it attempts to detect the correct orientation by looking for a black bar with white text at the top, which it assumes is the header. It then rotates the image accordingly and saves it as a separate JPG file.

## Requirements

- Python 3
- Pillow
- opencv-python
- pdf2image (and its dependency, poppler)
- pytesseract

You can install the Python libraries using pip:
```bash
pip install -r requirements.txt
```

## Usage

```bash
python autocrop.py <input_file>
```

Where `<input_file>` is the path to your image (PNG, JPG) or PDF file.

The cropped images will be saved in the current directory as `final_image_1.jpg`, `final_image_2.jpg`, etc.
