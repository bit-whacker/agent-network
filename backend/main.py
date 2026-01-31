"""Main FastAPI application"""
import os
import json
from uuid import UUID, uuid4
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.models import (
    ProfileQuestion, ProfileData, SearchRequest,
    SearchResponse, MatchResult, AgentResponse, ConnectionCreate
)
from backend.database import execute_query, execute_function
from backend.agent import profile_builder, search_agent, match_evaluator, embedding_generator

app = FastAPI(title="Agent Network API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store user names for conversation context
user_names = {}


@app.get("/")
def read_root():
    return {"message": "Agent Network API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# ============================================================================
# Profile Building Endpoints
# ============================================================================

@app.post("/api/profile/start")
def start_profile_building(email: str, name: str):
    """Start profile building process"""
    try:
        # Create user if doesn't exist
        existing = execute_query(
            "SELECT id FROM users WHERE email = :email",
            {"email": email}
        )

        if existing:
            user_id = existing[0]['id']
        else:
            result = execute_query(
                "INSERT INTO users (email, name) VALUES (:email, :name) RETURNING id",
                {"email": email, "name": name}
            )
            user_id = result[0]['id']

        user_id_str = str(user_id)

        # Store user name for conversation context
        user_names[user_id_str] = name

        # Reset agent memory for new conversation
        profile_builder.reset(user_id_str)

        # Get first question from agent
        response = profile_builder.chat(
            f"Hi! I'm {name}. I'd like to build my professional profile.",
            user_id_str,
            name
        )

        return {
            "user_id": user_id_str,
            "message": response["message"],
            "is_complete": response["is_complete"],
            "profile_data": response["profile_data"],
            "missing_fields": response.get("missing_fields", [])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/profile/chat")
def continue_profile_chat(question: ProfileQuestion, user_id: UUID):
    """Continue profile building conversation"""
    try:
        user_id_str = str(user_id)

        # Get user name
        user_name = user_names.get(user_id_str, "User")

        # If we don't have the name, try to get it from DB
        if user_name == "User":
            user_data = execute_query(
                "SELECT name FROM users WHERE id = :user_id",
                {"user_id": user_id_str}
            )
            if user_data:
                user_name = user_data[0]['name']
                user_names[user_id_str] = user_name

        # Chat with agent
        response = profile_builder.chat(
            question.user_message,
            user_id_str,
            user_name
        )

        return {
            "message": response["message"],
            "is_complete": response["is_complete"],
            "profile_data": response["profile_data"],
            "missing_fields": response.get("missing_fields", [])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/profile/save")
def save_profile(profile: ProfileData):
    """Save completed profile"""
    try:
        user_id_str = str(profile.user_id)

        # Check if profile exists
        existing = execute_query(
            "SELECT id FROM profiles WHERE user_id = :user_id",
            {"user_id": user_id_str}
        )

        # Prepare profile data
        skills_json = json.dumps(profile.skills) if profile.skills else '[]'
        location_json = json.dumps(profile.location) if profile.location else None

        if existing:
            # Update existing
            execute_query("""
                UPDATE profiles
                SET title = :title, bio = :bio, skills = :skills::jsonb,
                    experience_years = :exp, availability = :avail,
                    location = :loc::jsonb, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :user_id
            """, {
                "user_id": user_id_str,
                "title": profile.title,
                "bio": profile.bio,
                "skills": skills_json,
                "exp": profile.experience_years,
                "avail": profile.availability,
                "loc": location_json
            })
        else:
            # Insert new
            execute_query("""
                INSERT INTO profiles (user_id, title, bio, skills, experience_years, availability, location)
                VALUES (:user_id, :title, :bio, :skills::jsonb, :exp, :avail, :loc::jsonb)
            """, {
                "user_id": user_id_str,
                "title": profile.title,
                "bio": profile.bio,
                "skills": skills_json,
                "exp": profile.experience_years,
                "avail": profile.availability,
                "loc": location_json
            })

        # Clear conversation state
        profile_builder.reset(user_id_str)
        user_names.pop(user_id_str, None)

        return {"message": "Profile saved successfully", "user_id": user_id_str}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Search Endpoints
# ============================================================================

@app.post("/api/search")
async def search_network(search: SearchRequest):
    """Search for matching professionals"""
    try:
        # Get user's connections
        connections = execute_function("get_connections", str(search.user_id))
        
        if not connections or len(connections) == 0:
            return {
                "request_id": str(uuid4()),
                "matches": [],
                "total_contacted": 0,
                "message": "No connections found. Connect with others first!"
            }
        
        # Process search query with agent
        search_result = search_agent.process_search(search.query_text)
        structured_query = search_result["structured_query"]
        
        # Create service request
        request_result = execute_query("""
            INSERT INTO service_requests (requesting_user_id, query_text, structured_query)
            VALUES (:user_id, :query, :structured::jsonb)
            RETURNING id
        """, {
            "user_id": str(search.user_id),
            "query": search.query_text,
            "structured": json.dumps(structured_query)
        })
        
        request_id = request_result[0]['id']
        
        # Broadcast to network
        broadcast_result = execute_function(
            "broadcast_request",
            str(search.user_id),
            str(request_id)
        )
        
        # Evaluate each connected user
        matches = []
        for conn in connections:
            conn_user_id = conn['user_id']
            
            # Get candidate profile
            profile_data = execute_function("get_user_profile", conn_user_id)
            
            if not profile_data or not profile_data.get('profile'):
                continue
            
            # Evaluate match using agent
            evaluation = match_evaluator.evaluate(
                structured_query,
                profile_data['profile']
            )
            
            # Record response
            execute_function(
                "record_agent_response",
                str(request_id),
                conn_user_id,
                json.dumps(evaluation)
            )
            
            if evaluation.get('is_match'):
                matches.append({
                    "user_id": conn_user_id,
                    "name": profile_data['name'],
                    "title": profile_data['profile'].get('title'),
                    "match_score": evaluation['match_score'],
                    "matched_skills": evaluation.get('matched_skills', []),
                    "explanation": evaluation.get('explanation', ''),
                    "trust_score": conn.get('trust_score', 1.0),
                    "final_score": evaluation['match_score'] * 0.7 + conn.get('trust_score', 1.0) * 0.3
                })
        
        # Sort by final score
        matches.sort(key=lambda x: x['final_score'], reverse=True)
        
        return {
            "request_id": str(request_id),
            "matches": matches,
            "total_contacted": len(connections)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Connection Endpoints
# ============================================================================

@app.post("/api/connections")
def create_connection(connection: ConnectionCreate):
    """Create connection between two users"""
    try:
        execute_query("""
            INSERT INTO connections (user_a_id, user_b_id, trust_score)
            VALUES (:user_a, :user_b, 1.0)
            ON CONFLICT DO NOTHING
        """, {
            "user_a": str(connection.user_a_id),
            "user_b": str(connection.user_b_id)
        })
        
        return {"message": "Connection created successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/connections/{user_id}")
def get_user_connections(user_id: UUID):
    """Get all connections for a user"""
    try:
        connections = execute_function("get_connections", str(user_id))
        return {"connections": connections or []}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# User Endpoints
# ============================================================================

@app.get("/api/users")
def list_users():
    """List all users"""
    try:
        users = execute_query("""
            SELECT u.id, u.email, u.name, u.created_at,
                   p.title, p.skills
            FROM users u
            LEFT JOIN profiles p ON u.id = p.user_id
            ORDER BY u.created_at DESC
        """)
        
        return {"users": users or []}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/profile/{user_id}")
def get_profile(user_id: UUID):
    """Get user profile"""
    try:
        profile = execute_function("get_user_profile", str(user_id))
        
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        
        return profile
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
