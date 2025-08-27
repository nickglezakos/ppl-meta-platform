"""
Platform and Licensing Data Models for PPL Meta BootCore Service

These models define the core data structures for:
- Platform instance identity
- License information and validation
- User accounts and management
- API request/response models

GitHub Issue: #44
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field, validator


class LicenseType(str, Enum):
    """License type enumeration"""

    TRIAL = "trial"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    DEVELOPER = "developer"


class ActivationStatus(str, Enum):
    """License activation status"""

    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    INVALID = "invalid"


class UserRole(str, Enum):
    """User role enumeration"""

    OWNER = "owner"
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


# Core Data Models


class PlatformInstance(BaseModel):
    """Platform instance identity and configuration"""

    instance_id: UUID = Field(
        default_factory=uuid4, description="Unique platform instance identifier"
    )
    license_key: Optional[str] = Field(None, description="Associated license key")
    owner_email: Optional[str] = Field(None, description="Platform owner email address")
    installation_date: datetime = Field(
        default_factory=datetime.now, description="Installation timestamp"
    )
    activation_date: Optional[datetime] = Field(
        None, description="License activation timestamp"
    )
    platform_version: str = Field("1.0.0", description="Platform version")
    hardware_fingerprint: Optional[str] = Field(
        None, description="Hardware identification fingerprint"
    )
    activation_status: ActivationStatus = Field(
        ActivationStatus.PENDING, description="Current activation status"
    )
    license_type: Optional[LicenseType] = Field(None, description="Type of license")
    expires_date: Optional[datetime] = Field(
        None, description="License expiration date"
    )
    last_validation: Optional[datetime] = Field(
        None, description="Last license validation timestamp"
    )
    validation_count: int = Field(0, description="Number of validation attempts")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional platform metadata"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class LicenseInfo(BaseModel):
    """License information and features"""

    license_key: str = Field(..., description="License key identifier")
    license_type: LicenseType = Field(..., description="Type of license")
    issued_date: datetime = Field(
        default_factory=datetime.now, description="License issue date"
    )
    expires_date: Optional[datetime] = Field(
        None, description="License expiration date"
    )
    max_users: int = Field(1, description="Maximum number of users allowed")
    features_enabled: List[str] = Field(
        default_factory=list, description="List of enabled features"
    )
    activation_limit: int = Field(
        1, description="Maximum number of activations allowed"
    )
    current_activations: int = Field(
        0, description="Current number of active installations"
    )
    customer_id: Optional[UUID] = Field(None, description="Customer account identifier")
    purchase_order: Optional[str] = Field(None, description="Purchase order reference")
    is_active: bool = Field(True, description="License active status")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional license metadata"
    )

    @validator("license_key")
    def validate_license_key(cls, v):
        if not v or len(v) < 10:
            raise ValueError("License key must be at least 10 characters")
        return v

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class UserAccount(BaseModel):
    """User account information"""

    user_id: UUID = Field(default_factory=uuid4, description="Unique user identifier")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="User email address")
    password_hash: Optional[str] = Field(None, description="Hashed password")
    role: UserRole = Field(UserRole.USER, description="User role")
    created_date: datetime = Field(
        default_factory=datetime.now, description="Account creation date"
    )
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    is_active: bool = Field(True, description="Account active status")
    preferences: Dict[str, Any] = Field(
        default_factory=dict, description="User preferences"
    )
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional user metadata"
    )

    @validator("username")
    def validate_username(cls, v):
        if not v.isalnum() and "_" not in v and "-" not in v:
            raise ValueError(
                "Username can only contain alphanumeric characters, underscores, and hyphens"
            )
        return v

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


# API Request/Response Models


class LicenseActivationRequest(BaseModel):
    """License activation request"""

    license_key: str = Field(..., description="License key to activate")
    owner_email: EmailStr = Field(..., description="Owner email address")
    hardware_info: Optional[Dict[str, Any]] = Field(
        None, description="Hardware information for fingerprinting"
    )
    platform_info: Optional[Dict[str, Any]] = Field(
        None, description="Platform information"
    )

    @validator("license_key")
    def validate_license_key(cls, v):
        if not v or len(v) < 10:
            raise ValueError("License key must be at least 10 characters")
        return v


class LicenseActivationResponse(BaseModel):
    """License activation response"""

    success: bool = Field(..., description="Activation success status")
    instance_id: UUID = Field(..., description="Platform instance identifier")
    activation_status: ActivationStatus = Field(..., description="Activation status")
    license_type: Optional[LicenseType] = Field(None, description="License type")
    expires_date: Optional[datetime] = Field(
        None, description="License expiration date"
    )
    features_enabled: List[str] = Field(
        default_factory=list, description="Enabled features"
    )
    max_users: int = Field(1, description="Maximum users allowed")
    message: str = Field("", description="Activation message")
    next_validation: Optional[datetime] = Field(
        None, description="Next validation required"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class LicenseStatusResponse(BaseModel):
    """License status response"""

    license_active: bool = Field(..., description="License active status")
    license_type: Optional[LicenseType] = Field(None, description="License type")
    activation_status: ActivationStatus = Field(..., description="Activation status")
    expires_date: Optional[datetime] = Field(None, description="Expiration date")
    days_remaining: Optional[int] = Field(None, description="Days until expiration")
    features_enabled: List[str] = Field(
        default_factory=list, description="Enabled features"
    )
    max_users: int = Field(1, description="Maximum users allowed")
    current_users: int = Field(0, description="Current user count")
    last_validation: Optional[datetime] = Field(
        None, description="Last validation timestamp"
    )
    next_validation: Optional[datetime] = Field(
        None, description="Next validation required"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class PlatformIdentityResponse(BaseModel):
    """Platform identity information response"""

    instance_id: UUID = Field(..., description="Platform instance identifier")
    installation_date: datetime = Field(..., description="Installation date")
    platform_version: str = Field(..., description="Platform version")
    owner_email: Optional[str] = Field(None, description="Owner email")
    activation_status: ActivationStatus = Field(..., description="Activation status")
    license_type: Optional[LicenseType] = Field(None, description="License type")
    hardware_fingerprint: Optional[str] = Field(
        None, description="Hardware fingerprint"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Platform metadata"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class UserManagementRequest(BaseModel):
    """User management request"""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="User email")
    role: UserRole = Field(UserRole.USER, description="User role")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    send_invitation: bool = Field(True, description="Send invitation email")

    @validator("username")
    def validate_username(cls, v):
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username can only contain alphanumeric characters, underscores, and hyphens"
            )
        return v


class UserManagementResponse(BaseModel):
    """User management response"""

    success: bool = Field(..., description="Operation success")
    user_id: UUID = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email")
    role: UserRole = Field(..., description="User role")
    activation_link: Optional[str] = Field(None, description="User activation link")
    message: str = Field("", description="Operation message")

    class Config:
        json_encoders = {UUID: lambda v: str(v)}


class UserListResponse(BaseModel):
    """User list response"""

    users: List[UserAccount] = Field(..., description="List of users")
    total_count: int = Field(..., description="Total user count")
    owner_info: Optional[UserAccount] = Field(
        None, description="Platform owner information"
    )
    max_users: int = Field(1, description="Maximum users allowed")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


# Health Check Models


class ServiceHealthResponse(BaseModel):
    """Service health check response"""

    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Check timestamp"
    )
    version: str = Field("1.0.0", description="Service version")
    components: Dict[str, str] = Field(
        default_factory=dict, description="Component status"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Validation and Error Models


class ValidationError(BaseModel):
    """Validation error details"""

    field: str = Field(..., description="Field with error")
    message: str = Field(..., description="Error message")
    value: Optional[Any] = Field(None, description="Invalid value")


class APIError(BaseModel):
    """API error response"""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[List[ValidationError]] = Field(
        None, description="Validation errors"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Error timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
