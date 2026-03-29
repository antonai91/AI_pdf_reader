import os
import tempfile
from typing import Union
from PIL import Image

class OCRService:
    def __init__(self):
        self.model_path = os.getenv("GLM_OCR_MODEL_PATH", "./models/glm-ocr-mlx")
        self.model = None
        self.processor = None

    def _load_model(self):
        if self.model is None or self.processor is None:
            try:
                from mlx_vlm import load
                print(f"Loading GLM-OCR model from {self.model_path}...")
                self.model, self.processor = load(self.model_path)
            except ImportError:
                raise ImportError("mlx-vlm is not installed. Please install it to use OCRService.")
            except Exception as e:
                raise RuntimeError(f"Failed to load GLM-OCR model: {e}")

    def extract_table(self, image_source: Union[str, Image.Image], prompt: str = "Extract the table from this image into Markdown format.") -> str:
        """
        Extracts a table from an image and returns it as a Markdown string.
        """
        self._load_model()
        
        from mlx_vlm import generate

        # Handle PIL Image by saving to a temporary file
        temp_file_path = None
        if isinstance(image_source, Image.Image):
            _, temp_file_path = tempfile.mkstemp(suffix=".png")
            image_source.save(temp_file_path)
            image_path = temp_file_path
        elif isinstance(image_source, str):
            image_path = image_source
        else:
            raise ValueError("image_source must be a file path (str) or a PIL Image.")

        try:
            # According to typical mlx-vlm usage:
            images = [image_path]
            # Some mlx-vlm models expect <image> in the prompt, some just take the image list.
            # GLM models usually work fine with standard mlx-vlm generate wrapper.
            response = generate(self.model, self.processor, prompt, images, verbose=False)
            if hasattr(response, 'text'):
                return response.text
            elif isinstance(response, str):
                return response
            else:
                return str(response)
        except Exception as e:
            raise RuntimeError(f"Failed to generate OCR output: {e}")
        finally:
            # Clean up the temporary file if one was created
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)

# Singleton instance
ocr_service = OCRService()
