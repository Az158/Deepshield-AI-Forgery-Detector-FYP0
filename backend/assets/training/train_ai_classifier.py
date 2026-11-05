"""
Training Script — AI Image Classifier (EfficientNet-B0)
=========================================================
Run this on Google Colab (T4 GPU) or locally with a GPU.
Output: ai_classifier.pth  →  copy to backend/weights/

Dataset: ArtiFact (recommended)
  https://huggingface.co/datasets/awsaf49/artifact-dataset

Directory structure expected:
  data/
  ├── train/
  │   ├── real/      (real photographs)
  │   └── fake/      (AI-generated images)
  └── val/
      ├── real/
      └── fake/
"""
import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

# ── Adjust these ─────────────────────────────────────────────────────────────
DATA_DIR    = "./data"          # path to your dataset
EPOCHS      = 10
BATCH_SIZE  = 32
LR          = 1e-4
WEIGHT_DECAY= 1e-4
SAVE_PATH   = "./ai_classifier.pth"
# ─────────────────────────────────────────────────────────────────────────────

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {DEVICE}")

# ── Transforms ───────────────────────────────────────────────────────────────
transform_train = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.05),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])
transform_val = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

# ── Dataset ───────────────────────────────────────────────────────────────────
train_ds = datasets.ImageFolder(os.path.join(DATA_DIR, "train"), transform=transform_train)
val_ds   = datasets.ImageFolder(os.path.join(DATA_DIR, "val"),   transform=transform_val)
print(f"Train: {len(train_ds)} images | Val: {len(val_ds)} images")
print(f"Classes: {train_ds.classes}")  # should be ['fake', 'real'] or ['real', 'fake']

# IMPORTANT: ImageFolder sorts alphabetically.
# Verify that class index 1 = AI-generated / fake:
print(f"Class-to-index mapping: {train_ds.class_to_idx}")
# Expected: {'fake': 0, 'real': 1} OR {'real': 0, 'fake': 1}
# Our model outputs index 1 = AI-Generated.
# If your mapping is {'real': 0, 'fake': 1} → perfect.
# If your mapping is {'fake': 0, 'real': 1} → swap labels below.
FAKE_IDX = train_ds.class_to_idx.get("fake", train_ds.class_to_idx.get("ai", 1))
print(f"Fake class index: {FAKE_IDX}")

train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=2, pin_memory=True)
val_dl   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=2, pin_memory=True)

# ── Model ─────────────────────────────────────────────────────────────────────
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.ai_classifier import AIImageClassifier

model = AIImageClassifier(pretrained=True).to(DEVICE)

optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
criterion = nn.CrossEntropyLoss()
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

# ── Training loop ─────────────────────────────────────────────────────────────
best_val_acc = 0.0

for epoch in range(EPOCHS):
    # Train
    model.train()
    train_loss = train_correct = train_total = 0
    for imgs, labels in train_dl:
        # Remap labels so AI-generated always = index 1
        if FAKE_IDX == 0:
            labels = 1 - labels   # flip 0↔1

        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        logits = model(imgs)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()

        train_loss    += loss.item()
        train_correct += (logits.argmax(1) == labels).sum().item()
        train_total   += labels.size(0)

    scheduler.step()
    train_acc = train_correct / train_total

    # Validate
    model.eval()
    val_correct = val_total = 0
    with torch.no_grad():
        for imgs, labels in val_dl:
            if FAKE_IDX == 0:
                labels = 1 - labels
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            val_correct += (model(imgs).argmax(1) == labels).sum().item()
            val_total   += labels.size(0)

    val_acc = val_correct / val_total
    print(
        f"Epoch {epoch+1:02d}/{EPOCHS} | "
        f"loss={train_loss/len(train_dl):.4f} | "
        f"train_acc={train_acc:.4f} | val_acc={val_acc:.4f}"
    )

    if val_acc > best_val_acc:
        best_val_acc = val_acc
        torch.save(model.state_dict(), SAVE_PATH)
        print(f"  Saved best model (val_acc={val_acc:.4f}) -> {SAVE_PATH}")

print(f"\nTraining complete. Best val_acc={best_val_acc:.4f}")
print(f"Weights saved to: {SAVE_PATH}")
print(f"Copy to: backend/weights/ai_classifier.pth")
