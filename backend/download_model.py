import os
from huggingface_hub import snapshot_download

def main():
    model_id = "mlx-community/GLM-OCR-bf16"
    target_dir = "./models/glm-ocr-mlx"
    
    print(f"Downloading {model_id} to {target_dir} natively...")
    os.makedirs(target_dir, exist_ok=True)
    
    # Download the snapshot of the required repository locally
    snapshot_download(
        repo_id=model_id,
        local_dir=target_dir,
        local_dir_use_symlinks=False
    )
    print("Download completed successfully!")

if __name__ == "__main__":
    main()
