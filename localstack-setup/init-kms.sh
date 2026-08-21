#!/bin/bash
# LocalStack KMS initialization script
# This script creates a test KMS key for local development

set -e

echo "Waiting for LocalStack to be ready..."
until curl -s http://localhost:4566/health | grep -q 'running' || curl -s http://localhost:4566/_localstack/health | grep -q 'kms'; do
  sleep 2
done

echo "Creating KMS key for CMP development..."
KEY_ID=$(awslocal kms create-key \
  --description "CMP Development Master Key" \
  --key-usage "ENCRYPT_DECRYPT" \
  --query 'KeyMetadata.KeyId' \
  --output text)

echo "KMS Key created: $KEY_ID"

# Create a key alias
awslocal kms create-alias \
  --alias-name "alias/cmp-master-key" \
  --target-key-id "$KEY_ID"

echo "Alias 'cmp-master-key' created successfully"

# Output the key ID for use in environment
echo "KMS_KEY_ID=$KEY_ID" > /tmp/kms-key-id.txt

echo "LocalStack KMS setup complete!"