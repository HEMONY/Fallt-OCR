import requests
import pytesseract
from PIL import Image
import pdf2image
import io
import logging
from config import *

logger = logging.getLogger(__name__)

# Image OCR

def extract_text_from_image_ocr_api(image_data):
    """
    Extract text from an image using OCR.space API
    """
    try:
        url = 'https://api.ocr.space/parse/image'

        # Prepare image data
        if isinstance(image_data, str):
            with open(image_data, 'rb') as image_file:
                image_bytes = image_file.read()
        elif isinstance(image_data, bytes):
            image_bytes = image_data
        else:
            return "ERROR: Invalid image data type"

        payload = {
            'apikey': OCR_API_KEY,
            'language': 'ara',
            'isOverlayRequired': False,
            'detectOrientation': True,
            'scale': True,
            'OCREngine': 2
        }

        files = {
            'file': ('image.jpg', image_bytes, 'image/jpeg')
        }

        response = requests.post(url, data=payload, files=files, timeout=30)

        if response.ok:
            result = response.json()

            if result.get('IsErroredOnProcessing'):
                error_msg = result.get('ErrorMessage', ['Unknown error'])[0]
                return f"ERROR: OCR processing failed: {error_msg}"

            parsed_results = result.get('ParsedResults', [])
            if not parsed_results:
                return "WARNING: No text detected in image"

            extracted_text = parsed_results[0].get('ParsedText', '').strip()

            if not extracted_text:
                return "WARNING: No text detected in image"

            return extracted_text
        else:
            return f"ERROR: Server connection failed ({response.status_code})"

    except requests.exceptions.Timeout:
        return "ERROR: OCR API request timed out"
    except Exception as e:
        logger.error(f"OCR API error: {e}")
        return f"ERROR: {str(e)}"


def extract_text_from_image_tesseract(image, page_number=None):
    """
    Extract text from an image using local Tesseract OCR
    """
    try:
        if isinstance(image, bytes):
            image = Image.open(io.BytesIO(image))

        image = image.convert('RGB')

        text = pytesseract.image_to_string(
            image,
            lang=OCR_LANGUAGES,
            config=OCR_CONFIG
        ).strip()

        if page_number is not None:
            header = f"{'=' * 50}\nPage {page_number}\n{'=' * 50}\n\n"
            return header + text

        return text

    except Exception as e:
        logger.error(f"Tesseract OCR error: {e}")
        return f"ERROR: Image processing failed: {str(e)}"


# PDF OCR

def extract_text_from_pdf(pdf_file):
    """
    Extract text from a PDF file using OCR
    """
    try:
        if isinstance(pdf_file, bytes):
            images = pdf2image.convert_from_bytes(pdf_file, dpi=OCR_DPI, fmt='png')
        else:
            images = pdf2image.convert_from_bytes(pdf_file.read(), dpi=OCR_DPI, fmt='png')

        all_text = []
        total_pages = len(images)

        for i, image in enumerate(images, 1):
            page_text = extract_text_from_image_tesseract(image, page_number=i)
            all_text.append(page_text)

            if i < total_pages:
                all_text.append("\n\n" + "=" * 50 + "\n\n")

        header = f"Total Pages: {total_pages}\n" + "=" * 50 + "\n\n"
        return header + "\n".join(all_text)

    except Exception as e:
        logger.error(f"PDF OCR error: {e}")
        return f"ERROR: PDF processing failed: {str(e)}"


# Text Utilities

def split_message(text, max_length=MAX_MESSAGE_LENGTH):
    """
    Split long text into smaller chunks
    """
    messages = []
    current_message = ""

    for line in text.split('\n'):
        if len(current_message) + len(line) + 1 <= max_length:
            current_message += line + '\n'
        else:
            if current_message:
                messages.append(current_message.strip())

            if len(line) > max_length:
                words = line.split()
                temp = ""
                for word in words:
                    if len(temp) + len(word) + 1 <= max_length:
                        temp += word + ' '
                    else:
                        messages.append(temp.strip())
                        temp = word + ' '
                current_message = temp
            else:
                current_message = line + '\n'

    if current_message:
        messages.append(current_message.strip())

    return messages if messages else [""]


# Image Validation & Enhancement

def validate_image(image_data):
    """
    Validate image size and format
    """
    try:
        image = Image.open(io.BytesIO(image_data) if isinstance(image_data, bytes) else image_data)

        if image.size[0] > MAX_IMAGE_SIZE[0] or image.size[1] > MAX_IMAGE_SIZE[1]:
            return False, "Image size exceeds allowed limits"

        if image.format not in ['JPEG', 'PNG', 'BMP', 'TIFF']:
            return False, "Unsupported image format"

        return True, "OK"

    except Exception as e:
        return False, str(e)


def enhance_image_for_ocr(image):
    """
    Enhance image quality for better OCR results
    """
    try:
        from PIL import ImageEnhance, ImageOps

        if image.mode != 'RGB':
            image = image.convert('RGB')

        image = ImageEnhance.Sharpness(image).enhance(2.0)
        image = ImageEnhance.Contrast(image).enhance(1.5)
        image = ImageOps.grayscale(image)

        return image

    except Exception as e:
        logger.error(f"Image enhancement error: {e}")
        return image


def get_text_statistics(text):
    """
    Return basic statistics about extracted text
    """
    try:
        return {
            'lines': len(text.split('\n')),
            'words': len(text.split()),
            'characters': len(text)
        }
    except Exception as e:
        logger.error(f"Text statistics error: {e}")
        return None
