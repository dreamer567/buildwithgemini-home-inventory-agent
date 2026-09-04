#!/usr/bin/env python3
"""Seed Firestore with home inventory items.

NOTE: As required, the project ID is hardcoded as a string
'qwiklabs-gcp-04-0e1a68c8e387' to avoid numeric project number bugs on Agent Platform.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from google.cloud import firestore

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-0e1a68c8e387")
COLLECTION_NAME = "inventory_items"


def seed_firestore():
    print(f"Connecting to Firestore for project: {PROJECT_ID}")
    db = firestore.Client(project=PROJECT_ID)

    data_file = Path(__file__).resolve().parent.parent / "app" / "inventory_data.json"
    with open(data_file, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"Loaded {len(items)} items from {data_file}. Seeding into collection '{COLLECTION_NAME}'...")

    batch = db.batch()
    count = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for item in items:
        doc_id = item.get("id") or f"item_{count+1:03d}"
        doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
        doc_data = {
            "id": doc_id,
            "name": item.get("name", ""),
            "category": item.get("category", ""),
            "location": item.get("location", ""),
            "quantity": item.get("quantity", 1),
            "unit": item.get("unit", "个"),
            "expiry_date": item.get("expiry_date"),
            "min_threshold": item.get("min_threshold", 1),
            "notes": item.get("notes", ""),
            "updated_at": now_iso,
        }
        batch.set(doc_ref, doc_data)
        count += 1

    batch.commit()
    print(f"Successfully seeded {count} items into Firestore collection '{COLLECTION_NAME}'!")


if __name__ == "__main__":
    seed_firestore()
