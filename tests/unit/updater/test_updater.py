"""Unit tests for DTAUpdater process and SHA-512 verification."""

import hashlib
import os
import tempfile

from dta_autolive.updater.installer_process import DTAUpdater


def test_verify_sha512_success() -> None:
    """Verify SHA-512 checksum validation matches correct hash."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"DTA AutoLive Test Binary Package Data")
        tmp_path = tmp.name

    try:
        hasher = hashlib.sha512()
        hasher.update(b"DTA AutoLive Test Binary Package Data")
        expected_hash = hasher.hexdigest()

        updater = DTAUpdater(staging_dir="", install_dir="", backup_dir="")
        assert updater.verify_sha512(tmp_path, expected_hash) is True
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_verify_sha512_mismatch_fails() -> None:
    """Verify SHA-512 checksum validation fails on mismatched hash."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"DTA AutoLive Test Data")
        tmp_path = tmp.name

    try:
        updater = DTAUpdater(staging_dir="", install_dir="", backup_dir="")
        assert updater.verify_sha512(tmp_path, "wrong_hash_value_12345") is False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
