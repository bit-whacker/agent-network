"""Agent logic using LangChain and Anthropic"""
import os
import json
import re
from typing import Dict, Any, List, Optional
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


class ProfileBuilderAgent:
    """Agent that builds user profiles through conversation"""

    def __init__(self):
        self.llm = ChatAnthropic(
            anthropic_api_key=ANTHROPIC_API_KEY,
            model="claude-sonnet-4-20250514",
            temperature=0.7
        )

        self.extraction_llm = ChatAnthropic(
            anthropic_api_key=ANTHROPIC_API_KEY,
            model="claude-sonnet-4-20250514",
            temperature=0
        )

        # Store per-user conversation memories
        self.user_memories: Dict[str, ConversationBufferMemory] = {}

        # Store per-user profile data being built
        self.user_profiles: Dict[str, Dict] = {}

        # Required fields for a complete profile
        self.required_fields = ['title', 'skills', 'experience_years', 'availability', 'location', 'bio']

    def _get_memory(self, user_id: str) -> ConversationBufferMemory:
        """Get or create memory for a specific user"""
        if user_id not in self.user_memories:
            self.user_memories[user_id] = ConversationBufferMemory(
                memory_key="history",
                return_messages=True
            )
        return self.user_memories[user_id]

    def _get_profile(self, user_id: str) -> Dict:
        """Get or create profile data for a specific user"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'title': None,
                'skills': [],
                'experience_years': None,
                'availability': None,
                'location': None,
                'bio': None
            }
        return self.user_profiles[user_id]

    def _get_missing_fields(self, profile: Dict) -> List[str]:
        """Get list of fields that are still missing"""
        missing = []
        for field in self.required_fields:
            value = profile.get(field)
            if value is None or (isinstance(value, list) and len(value) == 0):
                missing.append(field)
        return missing

    def _extract_profile_data(self, conversation_history: str, current_profile: Dict) -> Dict:
        """Extract profile information from conversation using Claude"""

        extraction_prompt = f"""Analyze this conversation and extract any profile information mentioned.

Current profile data (update only if new information is found):
{json.dumps(current_profile, indent=2)}

Conversation:
{conversation_history}

Extract and return a JSON object with these fields (keep existing values if no new info found):
{{
    "title": "Professional title/role (e.g., 'Senior Software Engineer', 'UX Designer')" or null,
    "skills": ["skill1", "skill2", ...] (3-5 technical or professional skills) or [],
    "experience_years": number of years of experience or null,
    "availability": "full-time" or "part-time" or "freelance" or "not-available" or null,
    "location": {{"city": "City Name", "country": "Country"}} or null,
    "bio": "Brief 2-3 sentence professional bio" or null
}}

Rules:
- Only include information explicitly stated by the user
- For skills, normalize to standard names (e.g., "React.js" -> "React", "JS" -> "JavaScript")
- For experience, extract the number only
- For availability, map to one of the four options
- Keep existing values if no new information is provided for that field
- Return ONLY the JSON object, no other text"""

        try:
            response = self.extraction_llm.invoke(extraction_prompt)
            content = response.content

            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                extracted = json.loads(json_match.group())

                # Merge with current profile, keeping existing values if new ones are null
                merged = current_profile.copy()
                for key, value in extracted.items():
                    if value is not None and value != [] and value != "":
                        merged[key] = value

                return merged
        except Exception as e:
            print(f"Extraction error: {e}")

        return current_profile

    def chat(self, user_message: str, user_id: str, user_name: str = "User") -> Dict[str, Any]:
        """Continue profile building conversation for a specific user"""

        memory = self._get_memory(user_id)
        profile = self._get_profile(user_id)

        # Get conversation history as string for extraction
        history_messages = memory.chat_memory.messages
        conversation_text = "\n".join([
            f"{'User' if isinstance(m, HumanMessage) else 'Agent'}: {m.content}"
            for m in history_messages
        ])
        conversation_text += f"\nUser: {user_message}"

        # Extract any profile data from the conversation so far
        updated_profile = self._extract_profile_data(conversation_text, profile)
        self.user_profiles[user_id] = updated_profile

        # Determine what's missing
        missing_fields = self._get_missing_fields(updated_profile)
        is_complete = len(missing_fields) == 0

        # Build the prompt for the conversation
        # Escape curly braces in JSON to prevent LangChain template interpretation
        profile_json = json.dumps(updated_profile, indent=2).replace("{", "{{").replace("}", "}}")
        missing_str = ', '.join(missing_fields) if missing_fields else 'All information collected!'

        system_prompt = f"""You are a friendly professional networking assistant helping {user_name} build their profile.

Your goal is to gather these details through natural conversation:
1. Professional title/role
2. Key skills (3-5 technical or professional skills)
3. Years of experience
4. Availability (full-time, part-time, freelance, or not available)
5. Location (city and country)
6. Brief bio (2-3 sentences about their professional background)

Current profile status:
{profile_json}

Still needed: {missing_str}

Guidelines:
- Ask ONE question at a time about the missing information
- Be conversational, warm, and encouraging
- Acknowledge information the user provides before asking the next question
- If user provides multiple pieces of info, acknowledge all of them
- When all information is collected, summarize the profile and confirm it looks good
- Keep responses concise (2-3 sentences max)
- Do NOT ask for information you already have"""

        # Build messages for the LLM
        messages = [("system", system_prompt)]

        # Add conversation history
        for msg in history_messages:
            if isinstance(msg, HumanMessage):
                messages.append(("human", msg.content))
            else:
                messages.append(("assistant", msg.content))

        # Add current message
        messages.append(("human", user_message))

        # Create prompt and get response
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | self.llm

        response = chain.invoke({})
        response_text = response.content

        # Update memory with this exchange
        memory.chat_memory.add_user_message(user_message)
        memory.chat_memory.add_ai_message(response_text)

        return {
            "message": response_text,
            "is_complete": is_complete,
            "profile_data": updated_profile,
            "missing_fields": missing_fields
        }

    def reset(self, user_id: str):
        """Reset conversation memory and profile for a specific user"""
        if user_id in self.user_memories:
            del self.user_memories[user_id]
        if user_id in self.user_profiles:
            del self.user_profiles[user_id]

    def get_profile(self, user_id: str) -> Dict:
        """Get the current profile data for a user"""
        return self._get_profile(user_id)


class SearchAgent:
    """Agent that processes search requests and creates structured queries"""

    def __init__(self):
        self.llm = ChatAnthropic(
            anthropic_api_key=ANTHROPIC_API_KEY,
            model="claude-sonnet-4-20250514",
            temperature=0
        )

    def process_search(self, query_text: str) -> Dict[str, Any]:
        """Convert natural language search to structured query"""

        prompt = f"""Convert this professional networking search request into a structured format.

Search request: "{query_text}"

Extract the following (use null if not mentioned):
1. Skills required - normalize skill names (e.g., "React.js" -> "React", "ML" -> "Machine Learning")
2. Experience level - "junior" (0-2 years), "mid" (3-5 years), "senior" (6+ years), or specific years
3. Availability preference - "full-time", "part-time", "freelance", or null
4. Location preference - city and/or country if mentioned

Return ONLY a JSON object in this exact format:
{{
    "skills": ["skill1", "skill2"],
    "experience_level": "senior" or null,
    "min_experience_years": 5 or null,
    "availability": "freelance" or null,
    "location": {{"city": "San Francisco", "country": "USA"}} or null
}}"""

        response = self.llm.invoke(prompt)

        try:
            content = response.content
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                structured_query = json.loads(json_match.group())
                return {
                    "original_query": query_text,
                    "structured_query": structured_query
                }
        except Exception as e:
            print(f"Search parsing error: {e}")

        # Fallback to basic extraction
        return {
            "original_query": query_text,
            "structured_query": {
                "skills": self._extract_skills(query_text),
                "experience_level": None,
                "min_experience_years": None,
                "availability": None,
                "location": None
            }
        }

    def _extract_skills(self, text: str) -> List[str]:
        """Simple skill extraction fallback"""
        common_skills = [
            "React", "Python", "JavaScript", "TypeScript", "Design", "Figma",
            "Node.js", "Product Management", "UI/UX", "SQL", "AWS", "Docker",
            "Kubernetes", "Machine Learning", "Data Science", "Java", "Go",
            "Ruby", "PHP", "Swift", "Kotlin", "Flutter", "Vue", "Angular"
        ]

        found_skills = []
        text_lower = text.lower()

        for skill in common_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)

        return found_skills if found_skills else ["General"]


class MatchEvaluationAgent:
    """Agent that evaluates if a candidate matches a request"""

    def __init__(self):
        self.llm = ChatAnthropic(
            anthropic_api_key=ANTHROPIC_API_KEY,
            model="claude-sonnet-4-20250514",
            temperature=0
        )

    def evaluate(self, request_query: Dict, candidate_profile: Dict) -> Dict[str, Any]:
        """Evaluate if candidate matches the request using AI"""

        prompt = f"""Evaluate how well this candidate matches the search request.

Search Request:
{json.dumps(request_query, indent=2)}

Candidate Profile:
{json.dumps(candidate_profile, indent=2)}

Evaluation criteria:
1. Skills match - How many required skills does the candidate have?
2. Experience match - Does their experience level meet requirements?
3. Availability match - Does their availability match what's needed?
4. Location match - Are they in the desired location (if specified)?

Return ONLY a JSON object:
{{
    "is_match": true or false (true if match_score >= 0.3),
    "match_score": 0.0 to 1.0 (weighted average of criteria matches),
    "matched_skills": ["skill1", "skill2"] (skills that matched),
    "explanation": "Brief 1-2 sentence explanation of why they match or don't match"
}}

Be generous with matching - consider related skills (e.g., "React" matches "Frontend Development")."""

        try:
            response = self.llm.invoke(prompt)
            content = response.content

            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                evaluation = json.loads(json_match.group())
                # Ensure required fields exist
                evaluation.setdefault('is_match', False)
                evaluation.setdefault('match_score', 0.0)
                evaluation.setdefault('matched_skills', [])
                evaluation.setdefault('explanation', 'No explanation provided')
                return evaluation
        except Exception as e:
            print(f"Match evaluation error: {e}")

        # Fallback to simple matching
        return self._simple_match(request_query, candidate_profile)

    def _simple_match(self, request: Dict, profile: Dict) -> Dict:
        """Simple matching fallback"""
        request_skills = set(s.lower() for s in request.get("skills", []))
        profile_skills = set(s.lower() for s in (profile.get("skills") or []))

        matched = request_skills.intersection(profile_skills)

        if len(request_skills) > 0:
            score = len(matched) / len(request_skills)
        else:
            score = 0.5

        return {
            "is_match": score >= 0.3,
            "match_score": round(score, 2),
            "matched_skills": list(matched),
            "explanation": f"Matched {len(matched)} of {len(request_skills)} required skills"
        }


class EmbeddingGenerator:
    """Generate embeddings for profiles and queries using Anthropic"""

    def __init__(self):
        self.llm = ChatAnthropic(
            anthropic_api_key=ANTHROPIC_API_KEY,
            model="claude-sonnet-4-20250514",
            temperature=0
        )

    def generate_profile_text(self, profile: Dict) -> str:
        """Convert profile to searchable text representation"""
        parts = []

        if profile.get('title'):
            parts.append(f"Title: {profile['title']}")

        if profile.get('skills'):
            skills = profile['skills'] if isinstance(profile['skills'], list) else []
            parts.append(f"Skills: {', '.join(skills)}")

        if profile.get('experience_years'):
            parts.append(f"Experience: {profile['experience_years']} years")

        if profile.get('availability'):
            parts.append(f"Availability: {profile['availability']}")

        if profile.get('location'):
            loc = profile['location']
            if isinstance(loc, dict):
                loc_str = f"{loc.get('city', '')}, {loc.get('country', '')}".strip(', ')
                parts.append(f"Location: {loc_str}")

        if profile.get('bio'):
            parts.append(f"Bio: {profile['bio']}")

        return " | ".join(parts)

    def generate_search_text(self, query: Dict) -> str:
        """Convert search query to text representation"""
        parts = []

        if query.get('skills'):
            parts.append(f"Looking for skills: {', '.join(query['skills'])}")

        if query.get('experience_level'):
            parts.append(f"Experience level: {query['experience_level']}")

        if query.get('min_experience_years'):
            parts.append(f"Minimum {query['min_experience_years']} years experience")

        if query.get('availability'):
            parts.append(f"Availability: {query['availability']}")

        if query.get('location'):
            loc = query['location']
            if isinstance(loc, dict):
                loc_str = f"{loc.get('city', '')}, {loc.get('country', '')}".strip(', ')
                parts.append(f"Location: {loc_str}")

        return " | ".join(parts) if parts else "General search"


# Create singleton instances
profile_builder = ProfileBuilderAgent()
search_agent = SearchAgent()
match_evaluator = MatchEvaluationAgent()
embedding_generator = EmbeddingGenerator()
