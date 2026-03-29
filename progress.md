# OCR Module Tests Progress
- **Created test file:** `tests/test_ocr.py`
- **Fixed bug in `backend/services/ocr.py`:** The local `mlx_vlm` generate function returned a `GenerationResult` object instead of a string. Updated the method to return the `.text` attribute instead.
- **Tests run:** 
  - `test_extract_table_with_pil_image`: Verification using a synthetic PIL image. **PASSED**
  - `test_extract_table_with_image_path`: Verification using a temporary file. **PASSED**