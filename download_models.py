import os
import urllib.request
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "static", "models")
JS_DIR = os.path.join(BASE_DIR, "static", "js")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(JS_DIR, exist_ok=True)

BASE_URL = "https://raw.githubusercontent.com/justadudewhohacks/face-api.js/master/weights/"

FILES_TO_DOWNLOAD = [
    # Tiny Face Detector (lightweight, high FPS for sweeping rotations)
    "tiny_face_detector_model-weights_manifest.json",
    "tiny_face_detector_model-shard1",
    # 68 Landmarks
    "face_landmark_68_model-weights_manifest.json",
    "face_landmark_68_model-shard1",
    # Face Recognition (128-D embedding extraction)
    "face_recognition_model-weights_manifest.json",
    "face_recognition_model-shard1",
    "face_recognition_model-shard2",
    # SSD Mobilenet V1 (High accuracy detector for classroom sweeps)
    "ssd_mobilenetv1_model-weights_manifest.json",
    "ssd_mobilenetv1_model-shard1",
    "ssd_mobilenetv1_model-shard2"
]

def download_file(url, dest_path):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        print(f"[EXISTS] {os.path.basename(dest_path)} ({os.path.getsize(dest_path)} bytes)")
        return True
    
    print(f"[DOWNLOADING] {os.path.basename(dest_path)} from {url}...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, 'wb') as out_f:
            out_f.write(resp.read())
        print(f"[SAVED] {os.path.basename(dest_path)} ({os.path.getsize(dest_path)} bytes)")
        return True
    except Exception as e:
        print(f"[ERROR] Failed downloading {url}: {e}")
        return False

def main():
    print("=== Downloading Face-API Deep Learning Models ===")
    all_ok = True
    for fname in FILES_TO_DOWNLOAD:
        url = BASE_URL + fname
        dest = os.path.join(MODELS_DIR, fname)
        ok = download_file(url, dest)
        if not ok:
            all_ok = False

    # Download face-api.min.js
    face_api_js_url = "https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js"
    face_api_dest = os.path.join(JS_DIR, "face-api.min.js")
    print("\n=== Downloading face-api.min.js ===")
    download_file(face_api_js_url, face_api_dest)

    if all_ok:
        print("\n[SUCCESS] All AI models and face-api library downloaded successfully!")
    else:
        print("\n[WARNING] Some models failed to download. Check network connection.")

if __name__ == "__main__":
    main()
