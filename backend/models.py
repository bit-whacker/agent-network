"""Pydantic models for API requests and responses"""
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

# Request Models
class ProfileQuestion(BaseModel):
    user_message: str

class ProfileData(BaseModel):
    user_id: UUID
    title: Optional[str] = None
    bio: Optional[str] = None
    skills: List[str] = []
    experience_years: Optional[int] = None
    availability: Optional[str] = None
    location: Optional[Dict[str, str]] = None

class SearchRequest(BaseModel):
    user_id: UUID
    query_text: str

class ConnectionCreate(BaseModel):
    user_a_id: UUID
    user_b_id: UUID

# Response Models
class User(BaseModel):
    id: UUID
    email: str
    name: str
    created_at: datetime

class Profile(BaseModel):
    user_id: UUID
    title: Optional[str]
    bio: Optional[str]
    skills: List[str]
    experience_years: Optional[int]
    availability: Optional[str]
    location: Optional[Dict[str, str]]

class UserWithProfile(BaseModel):
    user: User
    profile: Optional[Profile]

class MatchResult(BaseModel):
    user_id: UUID
    name: str
    title: Optional[str]
    match_score: float
    matched_skills: List[str]
    explanation: str
    trust_score: float
    final_score: float

class SearchResponse(BaseModel):
    request_id: UUID
    matches: List[MatchResult]
    total_contacted: int

class AgentResponse(BaseModel):
    message: str
    data: Optional[Any] = None
    next_step: Optional[str] = None
