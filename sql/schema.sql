-- ============================================================================
-- SIMPLE AGENT-BASED NETWORKING DATABASE SCHEMA
-- For MCP Server with Vector Store & Tool Calling
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";  -- pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Users table - People in the network
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User profiles - What each user offers/can do
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Basic profile info
    title VARCHAR(255),              -- e.g., "Senior Product Designer"
    bio TEXT,                         -- Brief description
    skills JSONB DEFAULT '[]',        -- ["UI/UX", "Figma", "Design Systems"]
    experience_years INTEGER,         -- Years of experience
    availability VARCHAR(50),         -- "full-time", "part-time", "freelance"
    location JSONB,                   -- {"city": "San Francisco", "country": "USA"}
    
    -- Vector embedding for semantic search
    embedding vector(1536),           -- OpenAI ada-002 embedding dimension
    
    -- Metadata
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id)
);

-- Connections - Who is connected to whom (bidirectional trust)
CREATE TABLE connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_a_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_b_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Connection metadata
    established_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trust_score FLOAT DEFAULT 1.0,    -- 0.0 to 1.0, affects ranking
    
    -- Ensure no self-connections
    CONSTRAINT no_self_connection CHECK (user_a_id != user_b_id)
);

-- Create unique index to prevent duplicate connections (bidirectional)
CREATE UNIQUE INDEX idx_unique_connection ON connections (
    LEAST(user_a_id, user_b_id), 
    GREATEST(user_a_id, user_b_id)
);

-- ============================================================================
-- AGENT QUERY SYSTEM
-- ============================================================================

-- Service requests - When a user asks their agent to find someone
CREATE TABLE service_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    requesting_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- The request
    query_text TEXT NOT NULL,         -- "Looking for a designer with Figma experience"
    structured_query JSONB NOT NULL,  -- {"skills": ["Design", "Figma"], "availability": "freelance"}
    query_embedding vector(1536),     -- For semantic matching
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'completed', 'cancelled'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Agent responses - When agents evaluate if their user matches
CREATE TABLE agent_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL REFERENCES service_requests(id) ON DELETE CASCADE,
    responding_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Match evaluation
    is_match BOOLEAN NOT NULL,
    match_score FLOAT,                -- 0.0 to 1.0, how well they match
    match_explanation TEXT,           -- Why they match or don't match
    
    -- Matched attributes
    matched_skills JSONB,             -- Which skills matched
    
    -- Response metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- One response per user per request
    UNIQUE(request_id, responding_user_id)
);

-- ============================================================================
-- AGENT COMMUNICATION LOG
-- ============================================================================

-- Messages between agents (for audit and debugging)
CREATE TABLE agent_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    to_user_id UUID REFERENCES users(id) ON DELETE CASCADE, -- NULL for broadcast
    
    -- Message content
    message_type VARCHAR(50) NOT NULL, -- 'query_broadcast', 'response', 'clarification'
    payload JSONB NOT NULL,
    
    -- Tracking
    request_id UUID REFERENCES service_requests(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- MCP SERVER TOOL FUNCTIONS
-- ============================================================================

-- Function: Get user profile (MCP tool)
CREATE OR REPLACE FUNCTION get_user_profile(p_user_id UUID)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'user_id', u.id,
        'name', u.name,
        'email', u.email,
        'profile', json_build_object(
            'title', p.title,
            'bio', p.bio,
            'skills', p.skills,
            'experience_years', p.experience_years,
            'availability', p.availability,
            'location', p.location
        )
    )
    INTO result
    FROM users u
    LEFT JOIN profiles p ON u.id = p.user_id
    WHERE u.id = p_user_id;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function: Get connected users (MCP tool)
CREATE OR REPLACE FUNCTION get_connections(p_user_id UUID)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_agg(
        json_build_object(
            'user_id', connected_user_id,
            'name', u.name,
            'trust_score', c.trust_score,
            'connected_since', c.established_at
        )
    )
    INTO result
    FROM (
        SELECT 
            CASE 
                WHEN user_a_id = p_user_id THEN user_b_id 
                ELSE user_a_id 
            END AS connected_user_id,
            trust_score,
            established_at
        FROM connections
        WHERE user_a_id = p_user_id OR user_b_id = p_user_id
    ) c
    JOIN users u ON u.id = c.connected_user_id;
    
    RETURN COALESCE(result, '[]'::json);
END;
$$ LANGUAGE plpgsql;

-- Function: Search profiles by skills (MCP tool with vector similarity)
CREATE OR REPLACE FUNCTION search_profiles(
    p_query_embedding vector(1536),
    p_skills JSONB DEFAULT NULL,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    user_id UUID,
    name VARCHAR,
    title VARCHAR,
    skills JSONB,
    similarity_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id,
        u.name,
        p.title,
        p.skills,
        1 - (p.embedding <=> p_query_embedding) AS similarity_score
    FROM profiles p
    JOIN users u ON u.id = p.user_id
    WHERE 
        p.embedding IS NOT NULL
        AND (
            p_skills IS NULL 
            OR p.skills ?| array(SELECT jsonb_array_elements_text(p_skills))
        )
    ORDER BY p.embedding <=> p_query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function: Evaluate if user matches request (Agent logic)
CREATE OR REPLACE FUNCTION evaluate_match(
    p_request_id UUID,
    p_candidate_user_id UUID
)
RETURNS JSON AS $$
DECLARE
    request_data JSONB;
    profile_data JSONB;
    matched_skills JSONB;
    match_score FLOAT;
    is_match BOOLEAN;
    explanation TEXT;
    result JSON;
BEGIN
    -- Get request requirements
    SELECT structured_query INTO request_data
    FROM service_requests WHERE id = p_request_id;
    
    -- Get candidate profile
    SELECT row_to_json(p)::jsonb INTO profile_data
    FROM profiles p WHERE user_id = p_candidate_user_id;
    
    -- Simple skill matching logic
    SELECT jsonb_agg(skill)
    INTO matched_skills
    FROM jsonb_array_elements_text(profile_data->'skills') AS skill
    WHERE skill IN (
        SELECT jsonb_array_elements_text(request_data->'skills')
    );
    
    -- Calculate match score (simple version)
    IF matched_skills IS NOT NULL THEN
        match_score := (
            jsonb_array_length(matched_skills)::FLOAT / 
            GREATEST(jsonb_array_length(request_data->'skills'), 1)
        );
        is_match := match_score >= 0.3; -- 30% match threshold
        explanation := format('Matched %s of %s required skills', 
            jsonb_array_length(matched_skills),
            jsonb_array_length(request_data->'skills')
        );
    ELSE
        match_score := 0.0;
        is_match := FALSE;
        explanation := 'No matching skills found';
    END IF;
    
    -- Build result
    result := json_build_object(
        'is_match', is_match,
        'match_score', match_score,
        'matched_skills', COALESCE(matched_skills, '[]'::jsonb),
        'explanation', explanation
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function: Broadcast request to network (Agent action)
CREATE OR REPLACE FUNCTION broadcast_request(
    p_requesting_user_id UUID,
    p_request_id UUID
)
RETURNS JSON AS $$
DECLARE
    connected_users UUID[];
    response_count INTEGER := 0;
BEGIN
    -- Get all connected users
    SELECT array_agg(
        CASE 
            WHEN user_a_id = p_requesting_user_id THEN user_b_id 
            ELSE user_a_id 
        END
    )
    INTO connected_users
    FROM connections
    WHERE user_a_id = p_requesting_user_id OR user_b_id = p_requesting_user_id;
    
    -- Log broadcast message
    INSERT INTO agent_messages (from_user_id, to_user_id, message_type, payload, request_id)
    SELECT 
        p_requesting_user_id,
        unnest(connected_users),
        'query_broadcast',
        json_build_object('request_id', p_request_id),
        p_request_id;
    
    response_count := array_length(connected_users, 1);
    
    RETURN json_build_object(
        'broadcast_to', response_count,
        'request_id', p_request_id,
        'status', 'sent'
    );
END;
$$ LANGUAGE plpgsql;

-- Function: Record agent response
CREATE OR REPLACE FUNCTION record_agent_response(
    p_request_id UUID,
    p_responding_user_id UUID,
    p_match_evaluation JSON
)
RETURNS UUID AS $$
DECLARE
    response_id UUID;
BEGIN
    INSERT INTO agent_responses (
        request_id,
        responding_user_id,
        is_match,
        match_score,
        match_explanation,
        matched_skills
    )
    VALUES (
        p_request_id,
        p_responding_user_id,
        (p_match_evaluation->>'is_match')::BOOLEAN,
        (p_match_evaluation->>'match_score')::FLOAT,
        p_match_evaluation->>'explanation',
        (p_match_evaluation->>'matched_skills')::JSONB
    )
    RETURNING id INTO response_id;
    
    -- Log response message
    INSERT INTO agent_messages (from_user_id, to_user_id, message_type, payload, request_id)
    SELECT 
        p_responding_user_id,
        sr.requesting_user_id,
        'response',
        json_build_object(
            'response_id', response_id,
            'is_match', p_match_evaluation->>'is_match'
        ),
        p_request_id
    FROM service_requests sr WHERE sr.id = p_request_id;
    
    RETURN response_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Get ranked results for a request
CREATE OR REPLACE FUNCTION get_ranked_results(p_request_id UUID)
RETURNS JSON AS $$
BEGIN
    RETURN (
        SELECT json_agg(
            json_build_object(
                'user_id', ar.responding_user_id,
                'name', u.name,
                'title', p.title,
                'match_score', ar.match_score,
                'matched_skills', ar.matched_skills,
                'explanation', ar.match_explanation,
                'trust_score', COALESCE(c.trust_score, 1.0),
                'final_score', (ar.match_score * 0.7 + COALESCE(c.trust_score, 1.0) * 0.3)
            )
            ORDER BY (ar.match_score * 0.7 + COALESCE(c.trust_score, 1.0) * 0.3) DESC
        )
        FROM agent_responses ar
        JOIN users u ON u.id = ar.responding_user_id
        LEFT JOIN profiles p ON p.user_id = ar.responding_user_id
        LEFT JOIN service_requests sr ON sr.id = ar.request_id
        LEFT JOIN connections c ON (
            (c.user_a_id = sr.requesting_user_id AND c.user_b_id = ar.responding_user_id) OR
            (c.user_b_id = sr.requesting_user_id AND c.user_a_id = ar.responding_user_id)
        )
        WHERE ar.request_id = p_request_id AND ar.is_match = TRUE
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- User lookups
CREATE INDEX idx_users_email ON users(email);

-- Profile searches
CREATE INDEX idx_profiles_user_id ON profiles(user_id);
CREATE INDEX idx_profiles_skills ON profiles USING GIN(skills);
CREATE INDEX idx_profiles_embedding ON profiles USING ivfflat(embedding vector_cosine_ops);

-- Connection queries
CREATE INDEX idx_connections_user_a ON connections(user_a_id);
CREATE INDEX idx_connections_user_b ON connections(user_b_id);

-- Request tracking
CREATE INDEX idx_requests_user ON service_requests(requesting_user_id);
CREATE INDEX idx_requests_status ON service_requests(status);
CREATE INDEX idx_requests_embedding ON service_requests USING ivfflat(query_embedding vector_cosine_ops);

-- Response lookups
CREATE INDEX idx_responses_request ON agent_responses(request_id);
CREATE INDEX idx_responses_user ON agent_responses(responding_user_id);
CREATE INDEX idx_responses_match ON agent_responses(is_match) WHERE is_match = TRUE;

-- Message audit trail
CREATE INDEX idx_messages_from ON agent_messages(from_user_id);
CREATE INDEX idx_messages_to ON agent_messages(to_user_id);
CREATE INDEX idx_messages_request ON agent_messages(request_id);
CREATE INDEX idx_messages_created ON agent_messages(created_at);

-- ============================================================================
-- SAMPLE DATA FOR TESTING
-- ============================================================================

-- Insert sample users
INSERT INTO users (id, email, name) VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'alice@example.com', 'Alice Designer'),
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', 'bob@example.com', 'Bob Developer'),
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 'carol@example.com', 'Carol Product Manager');

-- Insert sample profiles
INSERT INTO profiles (user_id, title, bio, skills, experience_years, availability, location) VALUES
    (
        'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
        'Senior UX Designer',
        'Passionate about creating intuitive user experiences',
        '["UI/UX Design", "Figma", "Design Systems", "User Research"]',
        8,
        'freelance',
        '{"city": "San Francisco", "country": "USA"}'
    ),
    (
        'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12',
        'Full-Stack Developer',
        'Building scalable web applications',
        '["React", "Node.js", "PostgreSQL", "TypeScript"]',
        5,
        'full-time',
        '{"city": "New York", "country": "USA"}'
    ),
    (
        'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13',
        'Product Manager',
        'Focused on product strategy and user-centric design',
        '["Product Strategy", "User Research", "Agile", "Roadmapping"]',
        6,
        'part-time',
        '{"city": "Austin", "country": "USA"}'
    );

-- Create connections (Alice knows Bob, Bob knows Carol, Alice knows Carol)
INSERT INTO connections (user_a_id, user_b_id, trust_score) VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', 0.9),
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', 'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 0.85),
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 0.95);

-- ============================================================================
-- MCP SERVER TOOL DEFINITIONS (JSON Format for Claude)
-- ============================================================================

/*
MCP Tools Configuration for Claude:

{
  "tools": [
    {
      "name": "get_user_profile",
      "description": "Retrieve a user's profile information including skills, experience, and availability",
      "input_schema": {
        "type": "object",
        "properties": {
          "user_id": {
            "type": "string",
            "description": "UUID of the user"
          }
        },
        "required": ["user_id"]
      }
    },
    {
      "name": "get_connections",
      "description": "Get all users connected to a specific user in the network",
      "input_schema": {
        "type": "object",
        "properties": {
          "user_id": {
            "type": "string",
            "description": "UUID of the user"
          }
        },
        "required": ["user_id"]
      }
    },
    {
      "name": "search_profiles",
      "description": "Search for profiles matching specific skills using vector similarity",
      "input_schema": {
        "type": "object",
        "properties": {
          "query_embedding": {
            "type": "array",
            "items": {"type": "number"},
            "description": "1536-dimensional embedding vector"
          },
          "skills": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Required skills to filter by"
          },
          "limit": {
            "type": "integer",
            "default": 10,
            "description": "Maximum number of results"
          }
        },
        "required": ["query_embedding"]
      }
    },
    {
      "name": "evaluate_match",
      "description": "Evaluate if a candidate user matches a service request",
      "input_schema": {
        "type": "object",
        "properties": {
          "request_id": {
            "type": "string",
            "description": "UUID of the service request"
          },
          "candidate_user_id": {
            "type": "string",
            "description": "UUID of the candidate user"
          }
        },
        "required": ["request_id", "candidate_user_id"]
      }
    },
    {
      "name": "broadcast_request",
      "description": "Broadcast a service request to all connected users in the network",
      "input_schema": {
        "type": "object",
        "properties": {
          "requesting_user_id": {
            "type": "string",
            "description": "UUID of the user making the request"
          },
          "request_id": {
            "type": "string",
            "description": "UUID of the service request"
          }
        },
        "required": ["requesting_user_id", "request_id"]
      }
    },
    {
      "name": "record_agent_response",
      "description": "Record an agent's response to a service request",
      "input_schema": {
        "type": "object",
        "properties": {
          "request_id": {
            "type": "string",
            "description": "UUID of the service request"
          },
          "responding_user_id": {
            "type": "string",
            "description": "UUID of the responding user"
          },
          "match_evaluation": {
            "type": "object",
            "description": "Match evaluation result from evaluate_match"
          }
        },
        "required": ["request_id", "responding_user_id", "match_evaluation"]
      }
    },
    {
      "name": "get_ranked_results",
      "description": "Get ranked results for a service request, ordered by match and trust scores",
      "input_schema": {
        "type": "object",
        "properties": {
          "request_id": {
            "type": "string",
            "description": "UUID of the service request"
          }
        },
        "required": ["request_id"]
      }
    }
  ]
}
*/

-- ============================================================================
-- EXAMPLE USAGE WORKFLOW
-- ============================================================================

/*
WORKFLOW: User looking for a designer

1. User (Bob) creates a service request:
   INSERT INTO service_requests (requesting_user_id, query_text, structured_query)
   VALUES (
       'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12',
       'Looking for a designer with Figma experience',
       '{"skills": ["UI/UX Design", "Figma"], "availability": "freelance"}'
   )
   RETURNING id;
   -- Returns: request_id = 'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14'

2. Agent broadcasts request to network:
   SELECT broadcast_request(
       'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12',
       'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14'
   );
   -- Sends to connected users (Alice and Carol)

3. Each connected agent evaluates their user's match:
   SELECT evaluate_match(
       'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14',
       'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'  -- Alice
   );
   -- Returns: {"is_match": true, "match_score": 0.5, ...}

4. Agents record their responses:
   SELECT record_agent_response(
       'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14',
       'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
       '{"is_match": true, "match_score": 0.5, "matched_skills": ["UI/UX Design", "Figma"], "explanation": "Matched 2 of 2 required skills"}'::JSON
   );

5. Get ranked results:
   SELECT get_ranked_results('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14');
   -- Returns: Ranked list with Alice (high match + trust score)
*/

COMMENT ON DATABASE postgres IS 'Simple Agent-Based Networking System with MCP Integration';
