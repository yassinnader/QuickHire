import asyncio
import json
from typing import Any, Optional, Dict
from datetime import datetime, timedelta

class CacheService:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl: Dict[str, datetime] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        if key in self._cache:
            # Check if expired
            if key in self._ttl and datetime.now() > self._ttl[key]:
                await self.delete(key)
                return None
            return self._cache[key].get('value')
        return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set a value in cache with TTL"""
        self._cache[key] = {
            'value': value,
            'created_at': datetime.now()
        }
        
        # Set expiration time
        if ttl_seconds > 0:
            self._ttl[key] = datetime.now() + timedelta(seconds=ttl_seconds)
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        deleted = False
        if key in self._cache:
            del self._cache[key]
            deleted = True
        if key in self._ttl:
            del self._ttl[key]
        return deleted
    
    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        if key not in self._cache:
            return False
        
        if key in self._ttl and datetime.now() > self._ttl[key]:
            await self.delete(key)
            return False
        
        return True
    
    async def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()
        self._ttl.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'total_keys': len(self._cache),
            'expired_keys': len([k for k, exp in self._ttl.items() if datetime.now() > exp]),
            'cache_size_bytes': len(json.dumps(self._cache)),
        }
    
    async def cleanup_expired(self) -> int:
        """Clean up expired keys and return count of deleted keys"""
        expired_keys = [k for k, exp in self._ttl.items() if datetime.now() > exp]
        for key in expired_keys:
            await self.delete(key)
        return len(expired_keys)