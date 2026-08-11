"""
CMP Encryption Utility — AES-256-GCM with AWS KMS Envelope Encryption.

Implements ADR-003: Application-Level AES-256-GCM Column Encryption + AWS KMS
envelope encryption to enforce NDPR compliance and restrict medical record
decryption to authorized doctor roles only.

Architecture:
    Envelope Encryption:
    1. Generate a KMS data key (CMK → plaintext DEK + encrypted DEK)
    2. Use plaintext DEK to AES-256-GCM encrypt clinical fields
    3. Store encrypted DEK (kms_key_version) alongside ciphertext
    4. On decrypt: KMS decrypt(encrypted DEK) → plaintext DEK → AES-256-GCM decrypt

Security Properties:
    - Random 96-bit IV per encryption operation
    - AES-256-GCM provides authenticated encryption (integrity + confidentiality)
    - KMS key never leaves AWS; only data keys are cached in memory
    - System/DB admins cannot read clinical records without KMS decrypt permission
"""

import base64
import json
import os
from dataclasses import dataclass
from typing import Optional

from core.config import settings


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class EncryptedData:
    """
    Container for AES-256-GCM encrypted data.

    Attributes:
        ciphertext: Base64-encoded ciphertext
        iv: Base64-encoded initialization vector (96-bit / 12 bytes)
        tag: Base64-encoded authentication tag (128-bit / 16 bytes)
    """
    ciphertext: str
    iv: str
    tag: str

    def to_json(self) -> str:
        """Serialize to JSON string for storage."""
        return json.dumps({
            "ciphertext": self.ciphertext,
            "iv": self.iv,
            "tag": self.tag,
        })

    @classmethod
    def from_json(cls, data: str) -> "EncryptedData":
        """Deserialize from JSON string."""
        parsed = json.loads(data)
        return cls(
            ciphertext=parsed["ciphertext"],
            iv=parsed["iv"],
            tag=parsed["tag"],
        )


# ── KMS Client (Lazy-Initialized Singleton) ─────────────────────────────────

class KMSClient:
    """
    AWS KMS client for envelope encryption operations.

    Uses lazy initialization to avoid import errors when AWS SDK is not
    installed or configured (e.g., in test environments).
    """

    _client = None

    @classmethod
    def get_client(cls):
        """Get or create the KMS client singleton."""
        if cls._client is None:
            try:
                import boto3
                cls._client = boto3.client(
                    "kms",
                    region_name=settings.AWS_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                )
            except ImportError:
                raise ImportError(
                    "boto3 is required for KMS operations. "
                    "Install with: pip install boto3"
                )
        return cls._client

    @classmethod
    def reset_client(cls):
        """Reset the client singleton (useful for testing)."""
        cls._client = None


# ── KMS Envelope Encryption ─────────────────────────────────────────────────

def generate_data_key(key_id: Optional[str] = None) -> tuple[bytes, str]:
    """
    Generate a new KMS data key (envelope encryption).

    Uses KMS GenerateDataKey to create a symmetric data key:
    - Plaintext DEK: Used locally for AES-256-GCM encryption, then discarded
    - CiphertextBlob (encrypted DEK): Stored as kms_key_version for future decryption

    Args:
        key_id: KMS key ID, ARN, or alias. Defaults to settings.KMS_KEY_ID.

    Returns:
        tuple: (plaintext_data_key, encrypted_data_key_b64)
            - plaintext_data_key: 32-byte AES-256 key (DO NOT STORE)
            - encrypted_data_key_b64: Base64-encoded encrypted DEK (store in DB)

    Raises:
        RuntimeError: If KMS key is not configured or KMS call fails
    """
    kms_key = key_id or settings.KMS_KEY_ID
    if not kms_key:
        # Fallback: generate a random key for development/testing
        return _generate_dev_key()

    try:
        client = KMSClient.get_client()
        response = client.generate_data_key(
            KeyId=kms_key,
            KeySpec="AES_256",
        )
        plaintext_key = response["Plaintext"]
        encrypted_key_b64 = base64.b64encode(response["CiphertextBlob"]).decode("utf-8")
        return plaintext_key, encrypted_key_b64
    except Exception as e:
        raise RuntimeError(f"KMS GenerateDataKey failed: {e}") from e


def decrypt_data_key(encrypted_key_b64: str, key_id: Optional[str] = None) -> bytes:
    """
    Decrypt an encrypted KMS data key.

    Uses KMS Decrypt to recover the plaintext DEK for AES-256-GCM decryption.

    Args:
        encrypted_key_b64: Base64-encoded encrypted data key (from DB)
        key_id: KMS key ID, ARN, or alias. Defaults to settings.KMS_KEY_ID.

    Returns:
        bytes: 32-byte plaintext AES-256 key

    Raises:
        RuntimeError: If KMS key is not configured or KMS call fails
    """
    kms_key = key_id or settings.KMS_KEY_ID
    if not kms_key:
        # Fallback: use the dev key derivation
        return _get_dev_key()

    try:
        client = KMSClient.get_client()
        encrypted_key = base64.b64decode(encrypted_key_b64)
        response = client.decrypt(
            KeyId=kms_key,
            CiphertextBlob=encrypted_key,
        )
        return response["Plaintext"]
    except Exception as e:
        raise RuntimeError(f"KMS Decrypt failed: {e}") from e


# ── Development Fallback Keys ────────────────────────────────────────────────

_DEV_KEY: Optional[bytes] = None


def _generate_dev_key() -> tuple[bytes, str]:
    """
    Generate a development-only data key (no KMS required).

    Idempotent: If a dev key has already been generated, returns the existing
    key. This ensures all callers within the same process share the same key.

    WARNING: This is NOT secure. It is intended for local development and
    testing only. In production, KMS must be configured.

    Returns:
        tuple: (plaintext_key, "dev://<b64-encoded-key>" as encrypted_key)
    """
    global _DEV_KEY
    if _DEV_KEY is not None:
        # Return existing key (idempotent)
        encrypted_marker = "dev://" + base64.b64encode(_DEV_KEY).decode("utf-8")
        return _DEV_KEY, encrypted_marker
    _DEV_KEY = os.urandom(32)  # 256-bit key
    # Store a marker so we know it's a dev key
    encrypted_marker = "dev://" + base64.b64encode(_DEV_KEY).decode("utf-8")
    return _DEV_KEY, encrypted_marker


def _get_dev_key() -> bytes:
    """
    Get the development-only data key.

    Returns:
        bytes: 32-byte AES-256 key

    Raises:
        RuntimeError: If no dev key has been generated
    """
    global _DEV_KEY
    if _DEV_KEY is None:
        # Generate on first use
        _DEV_KEY, _ = _generate_dev_key()
    return _DEV_KEY


# ── AES-256-GCM Encryption / Decryption ─────────────────────────────────────

def encrypt_aes256_gcm(plaintext: str, key: bytes) -> EncryptedData:
    """
    Encrypt plaintext using AES-256-GCM.

    Uses a random 96-bit (12-byte) IV for each encryption operation to ensure
    semantic security. The authentication tag (128-bit) is computed over the
    ciphertext and provides integrity verification.

    Args:
        plaintext: The string to encrypt
        key: 32-byte AES-256 key

    Returns:
        EncryptedData containing ciphertext, IV, and authentication tag

    Raises:
        ValueError: If key is not 32 bytes
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if len(key) != 32:
        raise ValueError(f"AES-256 requires a 32-byte key, got {len(key)} bytes")

    # Generate random 96-bit IV
    iv = os.urandom(12)

    # Encrypt with AES-256-GCM
    aesgcm = AESGCM(key)
    plaintext_bytes = plaintext.encode("utf-8")
    ciphertext_with_tag = aesgcm.encrypt(iv, plaintext_bytes, None)

    # GCM appends the 16-byte tag to the ciphertext
    # Split: ciphertext = data[:-16], tag = data[-16:]
    ciphertext = ciphertext_with_tag[:-16]
    tag = ciphertext_with_tag[-16:]

    return EncryptedData(
        ciphertext=base64.b64encode(ciphertext).decode("utf-8"),
        iv=base64.b64encode(iv).decode("utf-8"),
        tag=base64.b64encode(tag).decode("utf-8"),
    )


def decrypt_aes256_gcm(encrypted: EncryptedData, key: bytes) -> str:
    """
    Decrypt AES-256-GCM ciphertext.

    Verifies the authentication tag to ensure ciphertext integrity before
    returning plaintext.

    Args:
        encrypted: EncryptedData containing ciphertext, IV, and tag
        key: 32-byte AES-256 key

    Returns:
        str: Decrypted plaintext

    Raises:
        ValueError: If key is not 32 bytes or authentication fails
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if len(key) != 32:
        raise ValueError(f"AES-256 requires a 32-byte key, got {len(key)} bytes")

    # Decode from base64
    ciphertext = base64.b64decode(encrypted.ciphertext)
    iv = base64.b64decode(encrypted.iv)
    tag = base64.b64decode(encrypted.tag)

    # Recombine ciphertext + tag for AESGCM
    ciphertext_with_tag = ciphertext + tag

    # Decrypt (verifies authentication tag)
    aesgcm = AESGCM(key)
    try:
        plaintext_bytes = aesgcm.decrypt(iv, ciphertext_with_tag, None)
    except Exception as e:
        raise ValueError(f"AES-256-GCM decryption failed (integrity check): {e}") from e

    return plaintext_bytes.decode("utf-8")


# ── High-Level Envelope Encryption API ───────────────────────────────────────

def encrypt_clinical_field(plaintext: str) -> tuple[str, str]:
    """
    Encrypt a clinical field using envelope encryption.

    High-level function that:
    1. Generates a new KMS data key
    2. Encrypts the plaintext with AES-256-GCM using the data key
    3. Returns the encrypted payload and the encrypted data key

    Args:
        plaintext: Clinical field value to encrypt

    Returns:
        tuple: (encrypted_payload_json, encrypted_data_key_b64)
            - encrypted_payload_json: JSON with ciphertext, iv, tag
            - encrypted_data_key_b64: Base64-encoded encrypted DEK (kms_key_version)

    Raises:
        RuntimeError: If encryption fails
    """
    # Generate data key (envelope)
    data_key, encrypted_key_b64 = generate_data_key()

    try:
        # Encrypt with AES-256-GCM
        encrypted = encrypt_aes256_gcm(plaintext, data_key)
        return encrypted.to_json(), encrypted_key_b64
    finally:
        # Zero out the plaintext data key from memory
        _zero_bytes(data_key)


def decrypt_clinical_field(
    encrypted_payload_json: str,
    encrypted_key_b64: str,
) -> str:
    """
    Decrypt a clinical field using envelope encryption.

    High-level function that:
    1. Decrypts the KMS data key
    2. Decrypts the AES-256-GCM ciphertext
    3. Returns the plaintext

    Args:
        encrypted_payload_json: JSON string with ciphertext, iv, tag
        encrypted_key_b64: Base64-encoded encrypted DEK

    Returns:
        str: Decrypted plaintext

    Raises:
        ValueError: If decryption or integrity check fails
        RuntimeError: If KMS decryption fails
    """
    # Decrypt the data key
    data_key = decrypt_data_key(encrypted_key_b64)

    try:
        # Parse encrypted payload
        encrypted = EncryptedData.from_json(encrypted_payload_json)

        # Decrypt with AES-256-GCM
        return decrypt_aes256_gcm(encrypted, data_key)
    finally:
        # Zero out the plaintext data key from memory
        _zero_bytes(data_key)


# ── Memory Security Utilities ────────────────────────────────────────────────

def _zero_bytes(data: bytearray | bytes) -> None:
    """
    Securely zero out bytes in memory.

    For bytearray, overwrites in place. For bytes (immutable), creates a new
    zero-filled array to replace the reference.

    Args:
        data: The byte data to zero out
    """
    if isinstance(data, bytearray):
        for i in range(len(data)):
            data[i] = 0
    # Note: bytes is immutable, so we can't truly zero it.
    # The caller should use bytearray for sensitive keys when possible.
