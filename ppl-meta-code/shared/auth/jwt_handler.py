"""JWT token handling utilities."""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class JWTHandler:
    """Handles JWT token creation and validation."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_token(self, payload: Dict[str, Any], expires_in: Optional[timedelta] = None) -> str:
        """Create a JWT token."""
        if expires_in:
            payload["exp"] = datetime.utcnow() + expires_in
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a JWT token."""
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
    
    def is_token_valid(self, token: str) -> bool:
        """Check if a token is valid."""
        try:
            self.decode_token(token)
            return True
        except jwt.InvalidTokenError:
            return False
