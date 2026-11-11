#!/usr/bin/env python3
"""Build the encrypted family copy of Dani's Updates.

Usage: DANI_PW=... python3 _build/build.py <data_dir> <repo_root>
data_dir/site.json  -> {"config": {...}, "posts": [...]}
data_dir/photos/<assetId>.<ext>
"""
import base64, hashlib, io, json, os, sys
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from PIL import Image, ImageOps

ITER = 250_000
here = Path(__file__).parent
data, out = Path(sys.argv[1]), Path(sys.argv[2])
pw = os.environ["DANI_PW"].encode()
(out / "img").mkdir(parents=True, exist_ok=True)

meta_path = out / "meta.json"
meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
if "salt" not in meta:
    meta["salt"] = base64.b64encode(os.urandom(16)).decode()
meta["iter"] = ITER
salt = base64.b64decode(meta["salt"])
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(pw)
aes = AESGCM(key)

def enc(b: bytes) -> bytes:
    iv = os.urandom(12)
    return iv + aes.encrypt(iv, b, None)

def img_name(asset_id: str) -> str:
    # opaque, stable file name that does not reveal the asset id
    return hashlib.sha256(salt + asset_id.encode()).hexdigest()[:20]

site = json.loads((data / "site.json").read_text())
photos = {p.stem: p for p in (data / "photos").iterdir() if p.is_file()}
used = set()

def photo_ref(asset_id):
    name = img_name(asset_id)
    target = out / "img" / (name + ".bin")
    if not target.exists() and asset_id not in photos:
        print("missing photo", asset_id, file=sys.stderr); return None
    used.add(name)
    if not target.exists():
        im = ImageOps.exif_transpose(Image.open(photos[asset_id])).convert("RGB")
        im.thumbnail((1600, 1600))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=82, optimize=True, progressive=True)
        target.write_bytes(enc(buf.getvalue()))
    return name

cfg = dict(site.get("config", {}))
if cfg.get("portraitId"):
    cfg["portrait"] = photo_ref(cfg["portraitId"])
cfg.pop("portraitId", None)
posts = []
for p in sorted(site.get("posts", []), key=lambda p: p.get("createdAt", ""), reverse=True):
    posts.append({
        "id": p["id"], "title": p.get("title", ""), "body": p.get("body", ""),
        "byline": p.get("byline", ""), "createdAt": p.get("createdAt", ""),
        "photos": [r for r in (photo_ref(a) for a in p.get("photos", [])) if r],
    })

plain = json.dumps({"config": cfg, "posts": posts}, sort_keys=True).encode()
digest = hashlib.sha256(salt + plain).hexdigest()
if meta.get("data_hash") != digest or not (out / "data.bin").exists():
    (out / "data.bin").write_bytes(enc(plain)); meta["data_hash"] = digest
    print("data changed")
else:
    print("data unchanged")
for f in (out / "img").glob("*.bin"):
    if f.stem not in used: f.unlink()
meta_path.write_text(json.dumps(meta))
html = (here / "template.html").read_text()
if not (out / "index.html").exists() or (out / "index.html").read_text() != html:
    (out / "index.html").write_text(html)
(out / ".nojekyll").write_text("")
print(f"built {len(posts)} posts, {len(used)} photos")
