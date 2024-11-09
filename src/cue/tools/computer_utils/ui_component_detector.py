"""
This module provides tools for detecting and analyzing UI components in screenshots and images
using computer vision and OCR techniques. It helps AI agents better understand and interact
with graphical user interfaces by providing accurate coordinate data and component classification.

Key features:
- UI component detection using contours
- Text extraction and OCR using Tesseract
- Component classification (buttons, text fields, icons, etc.)
- Coordinate extraction for UI automation
- Visualization tools for debugging
"""

import logging

import cv2
import numpy as np
import pytesseract
from PIL import Image
from pytesseract import Output

logger = logging.getLogger(__name__)


def sharpen_image(image):
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(image, -1, kernel)
    return sharpened


# Preprocess image for OCR
def preprocess_for_ocr(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Use adaptive thresholding
    ocr_ready = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return ocr_ready


def detect_ui_components(image_path, min_component_area=100):
    image = cv2.imread(image_path)
    image = sharpen_image(image)
    # Preprocess for contour detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Find contours
    contours, hierarchy = cv2.findContours(morph, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Preprocess for OCR
    ocr_ready = preprocess_for_ocr(image)
    # Save the OCR preprocessed image for debugging
    cv2.imwrite("ocr_ready.png", ocr_ready)

    # Convert image for OCR
    pil_image = Image.fromarray(ocr_ready)

    # Get OCR data
    custom_config = r"--oem 3 --psm 6"
    ocr_data = pytesseract.image_to_data(pil_image, output_type=Output.DICT, config=custom_config)

    # Process components
    components = []
    for _i, contour in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h

        if area < min_component_area:
            continue

        # Find text within this component
        component_text = []
        for j in range(len(ocr_data["text"])):
            text = ocr_data["text"][j].strip()
            if not text:
                continue

            text_x = ocr_data["left"][j]
            text_y = ocr_data["top"][j]
            text_w = ocr_data["width"][j]
            text_h = ocr_data["height"][j]

            if text_x >= x and text_x + text_w <= x + w and text_y >= y and text_y + text_h <= y + h:
                component_text.append(text)

        # Classify the component
        if component_text:
            text_str = " ".join(component_text)
            component_type = classify_component(w, h, text_str)
            components.append(
                {
                    "type": component_type,
                    "box": (x, y, x + w, y + h),
                    "text": text_str,
                    "area": area,
                }
            )
        else:
            # For non-text components
            component_type = classify_non_text_component(w, h)
            components.append(
                {
                    "type": component_type,
                    "box": (x, y, x + w, y + h),
                    "text": "",
                    "area": area,
                }
            )

    return components


def classify_non_text_component(width, height):
    aspect_ratio = width / height if height > 0 else 0

    # Simple heuristics for non-text components
    if aspect_ratio > 5:
        return "separator"  # Likely a horizontal line or separator
    elif aspect_ratio < 0.2:
        return "vertical_line"  # Likely a vertical line
    elif width > 50 and height > 50:
        return "image"  # Possibly an image or large icon
    else:
        return "icon"  # Default to icon


def classify_component(width, height, text):
    aspect_ratio = width / height if height > 0 else 0
    _area = width * height
    text = text.lower()

    button_keywords = ["submit", "login", "sign", "send", "start", "post", "subscribe", "follow"]
    # Use fuzzy matching or partial matching
    if text:
        for keyword in button_keywords:
            if keyword in text:
                return "button"
        if "?" in text:
            return "help_text"
        elif "@" in text:
            return "email_field"
        else:
            return "text"
    else:
        # Non-text components
        if aspect_ratio > 5 and height < 50:
            return "separator"
        elif aspect_ratio < 0.2 and width < 50:
            return "vertical_line"
        elif width > 50 and height > 50:
            return "image"
        else:
            return "icon"


def visualize_components(image_path, components):
    """
    Visualize detected UI components.
    """
    image = cv2.imread(image_path)

    # Color mapping for different component types
    color_map = {
        "button": (0, 255, 0),  # Green
        "text_field": (255, 0, 0),  # Blue
        "icon": (0, 0, 255),  # Red
        "help_text": (255, 255, 0),  # Cyan
        "text": (128, 0, 128),  # Purple
        "email_field": (255, 165, 0),  # Orange
    }

    for component in components:
        x1, y1, x2, y2 = component["box"]
        comp_type = component["type"]
        color = color_map.get(comp_type, (200, 200, 200))

        # Draw rectangle
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 1)

        # Add label
        label = f"{comp_type}: {component['text'][:30]}..."
        cv2.putText(image, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # Save result
    output_path = image_path.rsplit(".", 1)[0] + "_components.png"
    cv2.imwrite(output_path, image)
    return output_path


def format_box_info(components):
    formatted = []
    for comp in components:
        x1, y1, x2, y2 = comp["box"]
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        # Handle empty text
        text = comp["text"] if comp["text"] else ""
        if not text or len(text) <= 2:
            # ignore component with empty text
            continue
        res = f"{comp['type']} ({text}): {x1},{y1},{x2},{y2},{cx},{cy}"
        formatted.append(res)

    return formatted


def get_bounding_box_info(image_path) -> str:
    components = detect_ui_components(image_path)
    output_path = visualize_components(image_path, components)
    logger.debug(f"\nAnnotated image saved to: {output_path}")
    lines = ""
    for line in format_box_info(components):
        lines += f"\n {line}"
    return lines
