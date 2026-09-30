"""Small immutable local stores; hashes detect alteration, not adversarial tampering."""

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile


def canonical_json(value: object) -> bytes:
    """Stable UTF-8 JSON; missing numbers must be explicit nulls, never NaN."""
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def safe_key(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,119}", value):
        raise ValueError("Invalid archive key")
    return value


def publish(path: Path, data: bytes) -> bool:
    """Fsync then atomically hard-link a same-directory temporary file, without overwrite.

    Identical existing bytes are an idempotent retry; conflicts raise. A killed
    writer may leave .pending files, which readers ignore and never auto-promote.
    Requires local filesystem hard-link support (NTFS/ext4); no unsafe fallback.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Conflicting immutable write: {path.name}")
        return False
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != data:
                raise ValueError(f"Conflicting immutable write: {path.name}") from None
            return False
        return True
    finally:
        Path(temporary).unlink(missing_ok=True)


def put_object(root: Path, data: bytes) -> str:
    key = digest(data)
    publish(Path(root) / "objects" / key, data)
    return key


def get_object(root: Path, key: str) -> bytes:
    if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key):
        raise ValueError("Invalid object hash")
    data = (Path(root) / "objects" / key).read_bytes()
    if digest(data) != key:
        raise ValueError("Snapshot hash mismatch")
    return data


def write_record(path: Path, payload: dict) -> bool:
    return publish(path, canonical_json({"sha256": digest(canonical_json(payload)), "payload": payload}))


def read_record(path: Path) -> dict:
    envelope = json.loads(Path(path).read_bytes())
    if set(envelope) != {"sha256", "payload"} or digest(canonical_json(envelope["payload"])) != envelope["sha256"]:
        raise ValueError("Record hash mismatch")
    return envelope["payload"]
