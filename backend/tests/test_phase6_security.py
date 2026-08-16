import time
from app.core.security import SecurityManager
from app.cache.redis_cache import RedisCacheManager


def test_phase6_security_pipeline():
    # 1. Test Password Hashing
    raw_pass = "EnterprisePass2026!"
    hashed = SecurityManager.hash_password(raw_pass)
    assert hashed != raw_pass
    assert SecurityManager.verify_password(raw_pass, hashed) is True
    assert SecurityManager.verify_password("WrongPass", hashed) is False

    # 2. Test JWT Token Handling
    token = SecurityManager.create_access_token({"sub": "admin@decisionlens.ai", "role": "Administrator"})
    assert isinstance(token, str) and len(token.split(".")) == 3

    decoded = SecurityManager.decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "admin@decisionlens.ai"
    assert decoded["role"] == "Administrator"

    # 3. Test Redis / Memory Cache
    cache_key = "test_kpi_query_key_001"
    cache_data = {"total_records": 10000, "metric": "revenue", "sum": 500000.0}

    RedisCacheManager.set(cache_key, cache_data, ttl_seconds=10)
    cached_val = RedisCacheManager.get(cache_key)
    assert cached_val == cache_data
