"""
Test script to verify Docker development environment setup.
Run this after starting the Docker containers.
"""
import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_docker_environment():
    """Test that all required environment variables are set for Docker."""
    required_vars = [
        'DATABASE_URL',
        'REDIS_URL',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'AWS_DEFAULT_REGION',
        'AWS_ENDPOINT_URL',
        'KMS_KEY_ID',
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        return False
    
    print("✓ All required environment variables are set")
    return True


def test_database_connection():
    """Test database connection."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.exc import SQLAlchemyError
        
        db_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://cmp_user:cmp_password@localhost:5432/cmp_db')
        
        # For async, we need to use async engine
        from sqlalchemy.ext.asyncio import create_async_engine
        
        engine = create_async_engine(db_url, echo=False)
        
        async def check_connection():
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
        
        asyncio.run(check_connection())
        print("✓ Database connection successful")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def test_redis_connection():
    """Test Redis connection."""
    try:
        import redis
        
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        r.ping()
        print("✓ Redis connection successful")
        return True
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False


def test_localstack_kms():
    """Test LocalStack KMS connection."""
    try:
        import boto3
        from botocore.config import Config
        
        endpoint_url = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
        
        kms = boto3.client(
            'kms',
            endpoint_url=endpoint_url,
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
            config=Config(region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'))
        )
        
        response = kms.list_keys()
        print(f"✓ LocalStack KMS connection successful ({len(response.get('Keys', []))} keys found)")
        return True
    except Exception as e:
        print(f"✗ LocalStack KMS connection failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("CMP Docker Development Environment Tests")
    print("=" * 50)
    print()
    
    results = []
    
    print("Testing environment variables...")
    results.append(test_docker_environment())
    print()
    
    print("Testing database connection...")
    results.append(test_database_connection())
    print()
    
    print("Testing Redis connection...")
    results.append(test_redis_connection())
    print()
    
    print("Testing LocalStack KMS...")
    results.append(test_localstack_kms())
    print()
    
    print("=" * 50)
    if all(results):
        print("All tests passed! ✓")
        return 0
    else:
        print("Some tests failed! ✗")
        return 1


if __name__ == "__main__":
    sys.exit(main())