from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.common import TimestampedModel


class Tenant(TimestampedModel):
    """
    A tenant represents one business using the platform (one WhatsApp Business
    number). All other collections carry a `tenant_id` foreign key to this.
    """

    name: str
    slug: str = Field(description="URL-safe unique identifier, e.g. 'acme-co'")
    is_active: bool = True

    # WhatsApp Cloud API credentials, scoped per tenant so one deployment can
    # serve many businesses, each with their own Meta app / number.
    whatsapp_phone_number_id: str
    whatsapp_business_account_id: str
    whatsapp_access_token: str  # stored encrypted at rest in production (see README security note)

    timezone: str = "UTC"


class TenantCreate(BaseModel):
    name: str
    slug: str
    whatsapp_phone_number_id: str
    whatsapp_business_account_id: str
    whatsapp_access_token: str
    timezone: str = "UTC"


class UserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    AGENT = "agent"  # human handoff operator


class User(TimestampedModel):
    tenant_id: str  # the user's "home"/primary tenant, and what's embedded in the JWT
    email: EmailStr
    hashed_password: str
    full_name: str
    role: UserRole = UserRole.AGENT
    is_active: bool = True
    # Design decision: most users belong to exactly one tenant (tenant_id above),
    # which is why every JWT and every repository call is scoped by a single
    # tenant_id claim. A small number of platform-admin users (e.g. an agency
    # managing several client WhatsApp numbers) may additionally have read/write
    # access to other tenants without those tenants becoming their "home" tenant.
    # This list drives the frontend's Tenant Switcher; switching tenants re-issues
    # a JWT scoped to the newly selected tenant (see auth.switch_tenant).
    additional_tenant_ids: list[str] = Field(default_factory=list)


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.AGENT


class UserPublic(BaseModel):
    id: str
    tenant_id: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    additional_tenant_ids: list[str] = Field(default_factory=list)
