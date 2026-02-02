import os
import re
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

class AuthError(Exception):
    """Custom exception for authentication-related errors"""
    pass

class APIKeyValidator:
    """Validates API keys for different services"""
    
    # API key patterns for validation
    PATTERNS = {
        'openai': re.compile(r'^sk-[A-Za-z0-9]{48}$'),
        'anthropic': re.compile(r'^sk-ant-[A-Za-z0-9\-_]{95,}$'),
        'google': re.compile(r'^AIza[A-Za-z0-9\-_]{35}$'),
        'azure': re.compile(r'^[A-Za-z0-9]{32}$')
    }
    
    @classmethod
    def validate_openai_key(cls, api_key: str) -> bool:
        """Validate OpenAI API key format"""
        if not api_key or not isinstance(api_key, str):
            return False
        return bool(cls.PATTERNS['openai'].match(api_key.strip()))
    
    @classmethod
    def validate_key_format(cls, api_key: str, service: str) -> bool:
        """Validate API key format for specific service"""
        if service.lower() not in cls.PATTERNS:
            logger.warning(f"No validation pattern for service: {service}")
            return True  # Allow unknown services
        
        pattern = cls.PATTERNS[service.lower()]
        return bool(pattern.match(api_key.strip()))

class SecureConfigManager:
    """Secure configuration manager for API keys and settings"""
    
    def __init__(self, env_file: Optional[str] = None, encoding: str = 'utf-8'):
        self.env_file = env_file
        self.encoding = encoding
        self._config_cache: Dict[str, Any] = {}
        self._loaded = False
        
    def _load_environment(self) -> None:
        """Load environment variables with proper error handling"""
        try:
            # Try multiple common .env file locations
            env_paths = [
                self.env_file,
                '.env',
                '.env.local',
                Path.home() / '.env',
                Path.cwd() / 'config' / '.env'
            ]
            
            loaded = False
            for env_path in env_paths:
                if env_path and Path(env_path).exists():
                    load_dotenv(env_path, encoding=self.encoding, override=True)
                    logger.info(f"Loaded environment from: {env_path}")
                    loaded = True
                    break
            
            if not loaded and not any(os.getenv(key) for key in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']):
                logger.warning("No .env file found and no API keys in environment")
                
            self._loaded = True
            
        except Exception as e:
            logger.error(f"Failed to load environment: {str(e)}")
            raise AuthError(f"Environment loading failed: {str(e)}")
    
    def _sanitize_key(self, api_key: str) -> str:
        """Sanitize API key by removing whitespace and quotes"""
        if not api_key:
            return api_key
        
        # Remove common formatting issues
        sanitized = api_key.strip().strip('"').strip("'")
        return sanitized
    
    def get_api_key(self, 
                   service: str, 
                   key_name: Optional[str] = None, 
                   validate: bool = True,
                   required: bool = True) -> Optional[str]:
        """
        Get API key for specified service with validation and caching
        
        Args:
            service: Service name (e.g., 'openai', 'anthropic')
            key_name: Custom environment variable name
            validate: Whether to validate key format
            required: Whether key is required (raises error if missing)
        
        Returns:
            API key string or None if not required and not found
        """
        if not self._loaded:
            self._load_environment()
        
        # Determine environment variable name
        if key_name:
            env_var = key_name
        else:
            env_var = f"{service.upper()}_API_KEY"
        
        # Check cache first
        cache_key = f"{service}_{env_var}"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        # Get from environment
        api_key = os.getenv(env_var)
        
        if not api_key:
            if required:
                available_keys = [k for k in os.environ.keys() if 'API_KEY' in k]
                raise AuthError(
                    f"{env_var} not found in environment variables. "
                    f"Available API keys: {available_keys or 'None'}"
                )
            return None
        
        # Sanitize the key
        api_key = self._sanitize_key(api_key)
        
        # Validate format if requested
        if validate and not APIKeyValidator.validate_key_format(api_key, service):
            if required:
                raise AuthError(f"Invalid {service} API key format")
            logger.warning(f"Invalid {service} API key format detected")
        
        # Cache and return
        self._config_cache[cache_key] = api_key
        logger.info(f"Successfully retrieved {service} API key")
        return api_key
    
    def get_config_value(self, 
                        key: str, 
                        default: Any = None, 
                        data_type: type = str,
                        required: bool = False) -> Any:
        """Get configuration value with type conversion"""
        if not self._loaded:
            self._load_environment()
        
        value = os.getenv(key, default)
        
        if value is None and required:
            raise AuthError(f"Required configuration '{key}' not found")
        
        if value is None:
            return default
        
        # Type conversion
        try:
            if data_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif data_type == int:
                return int(value)
            elif data_type == float:
                return float(value)
            else:
                return data_type(value)
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to convert {key}={value} to {data_type.__name__}")
            if required:
                raise AuthError(f"Invalid type for required config '{key}': {str(e)}")
            return default
    
    def validate_all_keys(self) -> Dict[str, bool]:
        """Validate all API keys in environment"""
        if not self._loaded:
            self._load_environment()
        
        results = {}
        
        # Check for common API key patterns
        for key, value in os.environ.items():
            if 'API_KEY' in key:
                # Try to determine service from key name
                service = None
                for svc in APIKeyValidator.PATTERNS.keys():
                    if svc.upper() in key.upper():
                        service = svc
                        break
                
                if service:
                    is_valid = APIKeyValidator.validate_key_format(value, service)
                    results[key] = is_valid
                    if not is_valid:
                        logger.warning(f"Invalid format for {key}")
                else:
                    results[key] = True  # Unknown service, assume valid
        
        return results
    
    def clear_cache(self) -> None:
        """Clear the configuration cache"""
        self._config_cache.clear()
        logger.info("Configuration cache cleared")

# Global instance for convenience
_config_manager = SecureConfigManager()

# Enhanced functions with backward compatibility
@lru_cache(maxsize=1)
def get_openai_api_key(validate: bool = True, env_file: Optional[str] = None) -> str:
    """
    Get OpenAI API key with enhanced security and validation
    
    Args:
        validate: Whether to validate the API key format
        env_file: Custom .env file path
    
    Returns:
        OpenAI API key
        
    Raises:
        AuthError: If API key is not found or invalid
    """
    if env_file:
        manager = SecureConfigManager(env_file)
    else:
        manager = _config_manager
    
    try:
        api_key = manager.get_api_key('openai', validate=validate, required=True)
        
        # Additional security checks
        if len(api_key) < 20:
            raise AuthError("API key appears to be too short")
        
        # Log successful retrieval (without exposing key)
        masked_key = f"{api_key[:8]}...{api_key[-4:]}"
        logger.info(f"OpenAI API key retrieved successfully: {masked_key}")
        
        return api_key
        
    except Exception as e:
        logger.error(f"Failed to get OpenAI API key: {str(e)}")
        raise AuthError(f"OpenAI API key retrieval failed: {str(e)}")

def get_anthropic_api_key(validate: bool = True) -> str:
    """Get Anthropic API key"""
    return _config_manager.get_api_key('anthropic', validate=validate, required=True)

def get_google_api_key(validate: bool = True) -> str:
    """Get Google API key"""
    return _config_manager.get_api_key('google', validate=validate, required=True)

def get_azure_api_key(validate: bool = True) -> str:
    """Get Azure API key"""
    return _config_manager.get_api_key('azure', validate=validate, required=True)

def get_api_key_safe(service: str, default: Optional[str] = None) -> Optional[str]:
    """
    Safely get API key without raising errors
    
    Args:
        service: Service name
        default: Default value if key not found
        
    Returns:
        API key or default value
    """
    try:
        return _config_manager.get_api_key(service, required=False)
    except Exception as e:
        logger.warning(f"Failed to get {service} API key: {str(e)}")
        return default

def validate_environment() -> Dict[str, Any]:
    """
    Validate the entire environment configuration
    
    Returns:
        Dictionary with validation results
    """
    try:
        validation_results = _config_manager.validate_all_keys()
        
        return {
            'status': 'success',
            'api_keys_found': len(validation_results),
            'valid_keys': sum(validation_results.values()),
            'invalid_keys': len(validation_results) - sum(validation_results.values()),
            'details': validation_results
        }
    except Exception as e:
        logger.error(f"Environment validation failed: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }

def setup_environment(env_file: str = '.env', 
                     sample_keys: Optional[Dict[str, str]] = None) -> None:
    """
    Setup environment file with sample keys
    
    Args:
        env_file: Path to .env file
        sample_keys: Dictionary of sample API keys to write
    """
    env_path = Path(env_file)
    
    if env_path.exists():
        logger.warning(f"{env_file} already exists, skipping setup")
        return
    
    default_keys = sample_keys or {
        'OPENAI_API_KEY': 'sk-your-openai-key-here',
        'ANTHROPIC_API_KEY': 'sk-ant-your-anthropic-key-here',
        'GOOGLE_API_KEY': 'your-google-api-key-here',
        'AI_MODEL': 'gpt-4',
        'AI_TEMPERATURE': '0.7',
        'AI_MAX_TOKENS': '2000',
        'DEBUG': 'false'
    }
    
    try:
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write("# AI Service Configuration\n")
            f.write("# Replace placeholder values with your actual API keys\n\n")
            
            for key, value in default_keys.items():
                f.write(f"{key}={value}\n")
        
        logger.info(f"Environment template created at {env_file}")
        
    except Exception as e:
        logger.error(f"Failed to create environment file: {str(e)}")
        raise AuthError(f"Environment setup failed: {str(e)}")

# Convenience function for backward compatibility
def check_api_keys() -> bool:
    """
    Quick check if required API keys are available
    
    Returns:
        True if at least one valid API key is found
    """
    try:
        validation = validate_environment()
        return validation.get('valid_keys', 0) > 0
    except Exception:
        return False

# Usage examples:
"""
# Basic usage (backward compatible)
api_key = get_openai_api_key()

# Advanced usage with custom validation
api_key = get_openai_api_key(validate=True, env_file='custom.env')

# Safe retrieval without errors
api_key = get_api_key_safe('openai', default='fallback-key')

# Multiple services
openai_key = get_openai_api_key()
anthropic_key = get_anthropic_api_key()

# Environment validation
results = validate_environment()
print(f"Found {results['valid_keys']} valid API keys")

# Setup new environment
setup_environment('.env.example')

# Configuration values
debug_mode = _config_manager.get_config_value('DEBUG', False, bool)
max_tokens = _config_manager.get_config_value('AI_MAX_TOKENS', 1000, int)
"""