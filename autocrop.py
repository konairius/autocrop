#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import sys
import tempfile
import numpy as np

try:
    from PIL import Image, ImageOps
except ImportError:
    print("Error: 'Pillow' is not installed. please install it with 'pip install Pillow'", file=sys.stderr)
    sys.exit(1)

try:
    import cv2
except ImportError:
    print("Error: 'opencv-python' is not installed. please install it with 'pip install opencv-python'", file=sys.stderr)
    sys.exit(1)

try:
    from pdf2image import convert_from_path
except ImportError:
    print("Error: 'pdf2image' is not installed. please install it with 'pip install pdf2image'", file=sys.stderr)
    print("You also need to install poppler.", file=sys.stderr)
    sys.exit(1)

try:
    import pytesseract
except ImportError:
    print("Error: 'pytesseract' is not installed. please install it with 'pip install pytesseract'", file=sys.stderr)
    sys.exit(1)


def convert_pdf_to_images(input_file, temp_dir):
    """Converts a PDF file to a list of image files."""
    print("Input is a PDF. Converting to JPG images first.")
    try:
        images = convert_from_path(input_file, dpi=300, fmt='jpeg', output_folder=temp_dir)
        image_paths = [image.filename for image in images]
    except Exception as e:
        print(f"Error converting PDF: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not image_paths:
        print(f"Error: 'pdf2image' could not extract any images from '{input_file}'.", file=sys.stderr)
        sys.exit(1)
    print(f"Extracted {len(image_paths)} page-image(s) to process.")
    return image_paths

def find_sub_images(image_file):
    """Finds the bounding boxes of sub-images within a larger image."""
    print("---")
    print(f"Processing image: {os.path.basename(image_file)}")
    try:
        img = cv2.imread(image_file)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Use a lower threshold to detect white areas on a dark background
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

        # Invert the thresholded image so that the white areas become black,
        # and the black background becomes white.
        thresh = cv2.bitwise_not(thresh)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        boxes = []
        for cnt in contours:
            if cv2.contourArea(cnt) > 5000:
                x, y, w, h = cv2.boundingRect(cnt)
                boxes.append(f'{w}x{h}+{x}+{y}')
        
        if not boxes:
            print(" -> No images found on this page (or settings are wrong). Skipping.")
        
        return boxes
            
    except Exception as e:
        print(f"Error finding sub-images: {e}", file=sys.stderr)
        return []

def process_sub_image(input_image, box, output_name):
    """Crops, rotates, and saves a sub-image."""
    width, height, x, y = map(int, re.findall(r'\d+', box))
    print(f" -> Found sub-image at {box} (WxH: {width}x{height}).")

    with Image.open(input_image) as img:
        cropped_img = img.crop((x, y, x + width, y + height))
        
        best_rotation = 0
        best_text = ""
        found_orientation = False
        print("    -> Detecting orientation...")
        for rotation in [0, 270, 90, 180]:
            print(f"       - Trying rotation {rotation}...")
            rotated_img = cropped_img.rotate(rotation, expand=True)
            
            # Slice the top 10% of the image
            slice_height = int(rotated_img.height * 0.10)
            if slice_height == 0: continue
            top_slice = rotated_img.crop((0, 0, rotated_img.width, slice_height))

            # Convert to cv2 image to analyze
            top_slice_cv = cv2.cvtColor(np.array(top_slice), cv2.COLOR_RGB2BGR)
            gray_slice = cv2.cvtColor(top_slice_cv, cv2.COLOR_BGR2GRAY)
            mean_pixel = np.mean(gray_slice)
            print(f"         - Mean pixel value of top slice: {mean_pixel:.2f}")

            # Check if the slice is predominantly black
            if mean_pixel < 100:
                print(f"         - Top slice is predominantly black. Running OCR...")
                # Invert the slice to make text black on white for OCR
                _, ocr_slice = cv2.threshold(gray_slice, 128, 255, cv2.THRESH_BINARY_INV)
                
                try:
                    text = pytesseract.image_to_string(ocr_slice, config='--psm 1').strip()
                    print(f'         - OCR result: "{text}"')
                    
                    if len(text) > len(best_text) and ' ' in text:
                        best_text = text
                        best_rotation = rotation
                        found_orientation = True
                except Exception as e:
                    print(f"    -> OCR failed for rotation {rotation}: {e}", file=sys.stderr)
                    continue
            else:
                print("         - Top slice is not predominantly black. Skipping OCR.")
        
        if found_orientation:
            print(f"    -> Detected rotation: {best_rotation} degrees. Correcting...")
        else:
            print("    -> Could not detect orientation. Using original orientation.")

        final_image = cropped_img.rotate(best_rotation, expand=True, fillcolor='white')

        # Autocrop border
        final_image = ImageOps.invert(final_image.convert('L'))
        bbox = final_image.getbbox()
        if bbox:
            final_image = final_image.crop(bbox)
        final_image = ImageOps.invert(final_image).convert('RGB')
        
        final_image.save(output_name, "JPEG")
        print(f"    -> Saved to: {output_name}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Automatically crops sub-images from a larger image.")
    parser.add_argument("input_file", help="Path to the input file (PDF, PNG, or JPG).")
    args = parser.parse_args()

    temp_dir = tempfile.mkdtemp()
    try:
        if args.input_file.lower().endswith(".pdf"):
            image_files = convert_pdf_to_images(args.input_file, temp_dir)
        else:
            image_files = [args.input_file]

        total_images_saved = 0
        for image_file in image_files:
            boxes = find_sub_images(image_file)
            for i, box in enumerate(boxes):
                total_images_saved += 1
                output_name = f"final_image_{total_images_saved}.jpg"
                
                process_sub_image(image_file, box, output_name)

    finally:
        shutil.rmtree(temp_dir)

    print("---")
    print(f"Processing complete. Saved {total_images_saved} final image(s).")


if __name__ == "__main__":
    main()
