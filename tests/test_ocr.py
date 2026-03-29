import pytest
from PIL import Image, ImageDraw
import tempfile
import os
from backend.services.ocr import OCRService

def create_dummy_image():
    image = Image.new('RGB', (200, 100), color='white')
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), "Header 1 | Header 2\nValue 1 | Value 2", fill='black')
    return image

@pytest.fixture
def ocr_service():
    return OCRService()

def test_extract_table_with_pil_image(ocr_service):
    image = create_dummy_image()
    result = ocr_service.extract_table(image, prompt="Read the text in the image.")
    assert isinstance(result, str)
    assert len(result) > 0

def test_extract_table_with_image_path(ocr_service):
    image = create_dummy_image()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        image.save(tmp.name)
        tmp_path = tmp.name
        
    try:
        result = ocr_service.extract_table(tmp_path, prompt="Read the text in the image.")
        assert isinstance(result, str)
        assert len(result) > 0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
