import asyncio
import asyncpg
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.pool = None
        self.db_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/quickhire")
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            await self._create_tables()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connections closed")
    
    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            if not self.pool:
                return False
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False
    
    async def _create_tables(self):
        """Create necessary database tables"""
        async with self.pool.acquire() as conn:
            # Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(255) PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    full_name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Generation requests table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS generation_requests (
                    request_id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    request_type VARCHAR(50) NOT NULL,
                    request_data JSONB NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'processing',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            # Generated files table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS generated_files (
                    file_id SERIAL PRIMARY KEY,
                    request_id VARCHAR(255) NOT NULL,
                    file_type VARCHAR(50) NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    file_content BYTEA NOT NULL,
                    file_size INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (request_id) REFERENCES generation_requests(request_id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better performance
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_generation_requests_user_id 
                ON generation_requests(user_id)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_generation_requests_created_at 
                ON generation_requests(created_at)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_generated_files_request_id 
                ON generated_files(request_id)
            """)
    
    async def store_generation_request(
        self, 
        user_id: str, 
        request_id: str, 
        request_type: str, 
        request_data: Dict[str, Any], 
        status: str = "processing"
    ):
        """Store a new generation request"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO generation_requests 
                    (request_id, user_id, request_type, request_data, status)
                    VALUES ($1, $2, $3, $4, $5)
                """, request_id, user_id, request_type, json.dumps(request_data), status)
                
                logger.info(f"Stored generation request {request_id} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to store generation request {request_id}: {str(e)}")
            raise
    
    async def update_request_status(
        self, 
        request_id: str, 
        status: str, 
        error_message: Optional[str] = None
    ):
        """Update the status of a generation request"""
        try:
            async with self.pool.acquire() as conn:
                if status == "completed":
                    await conn.execute("""
                        UPDATE generation_requests 
                        SET status = $1, completed_at = $2
                        WHERE request_id = $3
                    """, status, datetime.utcnow(), request_id)
                else:
                    await conn.execute("""
                        UPDATE generation_requests 
                        SET status = $1, error_message = $2
                        WHERE request_id = $3
                    """, status, error_message, request_id)
                
                logger.info(f"Updated request {request_id} status to {status}")
        except Exception as e:
            logger.error(f"Failed to update request status {request_id}: {str(e)}")
            raise
    
    async def get_generation_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get generation request details"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT request_id, user_id, request_type, request_data, 
                           status, error_message, created_at, completed_at
                    FROM generation_requests 
                    WHERE request_id = $1
                """, request_id)
                
                if row:
                    return {
                        'request_id': row['request_id'],
                        'user_id': row['user_id'],
                        'request_type': row['request_type'],
                        'request_data': json.loads(row['request_data']),
                        'status': row['status'],
                        'error_message': row['error_message'],
                        'created_at': row['created_at'],
                        'completed_at': row['completed_at']
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get generation request {request_id}: {str(e)}")
            raise
    
    async def store_generated_file(
        self, 
        request_id: str, 
        file_type: str, 
        file_content: bytes, 
        filename: str
    ) -> str:
        """Store generated file and return download URL"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO generated_files 
                    (request_id, file_type, filename, file_content, file_size)
                    VALUES ($1, $2, $3, $4, $5)
                """, request_id, file_type, filename, file_content, len(file_content))
                
                # Return download URL
                download_url = f"/api/v1/download/{request_id}"
                logger.info(f"Stored generated file for request {request_id}")
                return download_url
        except Exception as e:
            logger.error(f"Failed to store generated file for request {request_id}: {str(e)}")
            raise
    
    async def get_generated_file(self, request_id: str) -> Optional[bytes]:
        """Get generated file content"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT file_content 
                    FROM generated_files 
                    WHERE request_id = $1
                """, request_id)
                
                if row:
                    return row['file_content']
                return None
        except Exception as e:
            logger.error(f"Failed to get generated file for request {request_id}: {str(e)}")
            raise
    
    async def get_user_generation_history(
        self, 
        user_id: str, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's generation history"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT gr.request_id, gr.request_type, gr.status, 
                           gr.created_at, gr.completed_at, gr.error_message,
                           gf.filename, gf.file_size
                    FROM generation_requests gr
                    LEFT JOIN generated_files gf ON gr.request_id = gf.request_id
                    WHERE gr.user_id = $1
                    ORDER BY gr.created_at DESC
                    LIMIT $2 OFFSET $3
                """, user_id, limit, offset)
                
                history = []
                for row in rows:
                    history.append({
                        'request_id': row['request_id'],
                        'request_type': row['request_type'],
                        'status': row['status'],
                        'created_at': row['created_at'],
                        'completed_at': row['completed_at'],
                        'error_message': row['error_message'],
                        'filename': row['filename'],
                        'file_size': row['file_size']
                    })
                
                return history
        except Exception as e:
            logger.error(f"Failed to get generation history for user {user_id}: {str(e)}")
            raise
    
    async def cleanup_old_files(self, user_id: str, days_old: int = 30):
        """Clean up old generated files"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            async with self.pool.acquire() as conn:
                # Get old request IDs
                old_requests = await conn.fetch("""
                    SELECT request_id 
                    FROM generation_requests 
                    WHERE user_id = $1 AND created_at < $2
                """, user_id, cutoff_date)
                
                if old_requests:
                    request_ids = [row['request_id'] for row in old_requests]
                    
                    # Delete old files
                    await conn.execute("""
                        DELETE FROM generated_files 
                        WHERE request_id = ANY($1)
                    """, request_ids)
                    
                    # Delete old requests
                    await conn.execute("""
                        DELETE FROM generation_requests 
                        WHERE request_id = ANY($1)
                    """, request_ids)
                    
                    logger.info(f"Cleaned up {len(request_ids)} old files for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to cleanup old files for user {user_id}: {str(e)}")
            raise
    
    async def create_user(self, user_id: str, email: str, full_name: str = None):
        """Create a new user"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (user_id, email, full_name)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id) DO UPDATE SET
                    email = $2, full_name = $3, updated_at = CURRENT_TIMESTAMP
                """, user_id, email, full_name)
                
                logger.info(f"Created/updated user {user_id}")
        except Exception as e:
            logger.error(f"Failed to create user {user_id}: {str(e)}")
            raise
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT user_id, email, full_name, created_at, updated_at
                    FROM users 
                    WHERE user_id = $1
                """, user_id)
                
                if row:
                    return {
                        'user_id': row['user_id'],
                        'email': row['email'],
                        'full_name': row['full_name'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {str(e)}")
            raise