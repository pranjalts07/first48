"""Sentence embeddings of article text at the end of day 0 and day 1.

The model and its revision are fixed so every fold uses the same encoder.

    python -m first48.embed
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


def load_content(folder):
    frames = [pd.read_json(path, lines=True) for path in sorted(Path(folder).glob("content_*.jsonl"))]
    return pd.concat(frames, ignore_index=True).drop_duplicates("page_id")


def encode(texts, batch_size=256):
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL, revision=REVISION)
    return model.encode(list(texts), batch_size=batch_size, show_progress_bar=True,
                        normalize_embeddings=True).astype(np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--content", type=Path, default=Path("data/content"))
    parser.add_argument("--out", type=Path, default=Path("data/embeddings.parquet"))
    args = parser.parse_args()

    content = load_content(args.content)
    out = pd.DataFrame({"page_id": content["page_id"]})
    for day in ("d0", "d1"):
        texts = content[f"text_{day}"].fillna("")
        vectors = encode(texts)
        vectors[texts.str.len().to_numpy() == 0] = np.nan
        out[f"emb_{day}"] = list(vectors)
    out.to_parquet(args.out)
    print(f"{len(out):,} articles embedded to {args.out}")


if __name__ == "__main__":
    main()
