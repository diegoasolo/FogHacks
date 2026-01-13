#IQA
#  1. DISTS  – Structural fidelity (lower = better)
#  2. MUSIQ  – Perceptual transformer (higher = better)
#  3. Combined score – Unified normalized IQA metric
import os
import torch
from torchvision import transforms
from PIL import Image
from tabulate import tabulate
from DISTS.DISTS_pytorch.DISTS_pt import DISTS
import pyiqa

def load_image(img_path, size):
    img = Image.open(img_path).convert("RGB")
    img = img.resize(size, Image.BICUBIC)
    return img

def evaluate_dists(clear_path, blurry_path):
    clear_img = load_image(clear_path, (512, 512))
    blurry_img = load_image(blurry_path, (512, 512))

    transform = transforms.ToTensor()
    x = transform(clear_img).unsqueeze(0)
    y = transform(blurry_img).unsqueeze(0)

    dists_model = DISTS()
    dists_model.eval()

    with torch.no_grad():
        score = dists_model(x, y).item()

    print(f"DISTS score (lower = better): {score:.4f}")
    return score

def evaluate_musiq(image_path):
    print("\n• Evaluating MUSIQ (pyiqa):")
    try:
        metric = pyiqa.create_metric('musiq', device='cpu')
        to_tensor = transforms.ToTensor()
        img = Image.open(image_path).convert('RGB')
        raw_score = metric(to_tensor(img).unsqueeze(0)).item()

        # Normalize from 0–100 range → 0–1 range
        normalized_score = raw_score / 100.0

        print(f"MUSIQ score (higher = better): {raw_score:.4f} (raw), normalized: {normalized_score:.4f}")
        return float(normalized_score)
    except Exception as e:
        print(f"⚠️ MUSIQ (pyiqa) error: {e}")
        return None

def combine_scores(dists_score, musiq_score):
    """
    Fuse DISTS and MUSIQ scores into a single normalized metric.
    Lower DISTS → higher quality, so invert via normalization.
    """
    dists_norm = 1 / (1 + dists_score)   # maps 0→1 inversely
    combined = 0.5 * musiq_score + 0.5 * dists_norm
    return combined

if __name__ == "__main__":
    clear_path = os.path.join(os.getcwd(), "clear.png")
    blurry_path = os.path.join(os.getcwd(), "blurry2.png")

    if not os.path.exists(clear_path) or not os.path.exists(blurry_path):
        exit()

    # --- Run evaluations ---
    dists_score = evaluate_dists(clear_path, blurry_path)
    musiq_score = evaluate_musiq(blurry_path)
    combined_score = combine_scores(dists_score, musiq_score)

    # --- Print summary table ---
    headers = ["Metric", "Description", "Value", "Interpret"]
    data = [
        ["DISTS", "Structural fidelity (↓ better)", f"{dists_score:.4f}", "Lower = closer to reference"],
        ["MUSIQ", "Perceptual quality (↑ better)", f"{musiq_score:.4f}", "Higher = more visually pleasing"],
        ["Combined", "Unified IQA Score (↑ better)", f"{combined_score:.4f}", "Overall visual quality"],
    ]
    print("\n" + tabulate(data, headers=headers, tablefmt="fancy_grid"))
    