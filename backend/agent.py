"""Agent logic using LangChain"""
import os
import json
from typing import Dict, Any, List
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

class ProfileBuilderAgent:
    """Agent that builds user profiles through conversation"""
    
    def __init__(self):
        self.llm = ChatAnthropic(
            anthropic_api_key=ANTHROPIC_API_KEY,
            model="claude-3-5-sonnet-20241022",
            temperature=0.7
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a friendly professional networking assistant helping build a user profile.
            
Your goal: Ask questions to gather these details:
1. Professional title/role
2. Key skills (3-5 technical or professional skills)
3. Years of experience
4. Availability (full-time, part-time, freelance, not available)
5. Location (city and country)
6. Brief bio (2-3 sentences)

Guidelines:
- Ask ONE question at a time
- Be conversational and friendly
- If user provides multiple pieces of info, acknowledge and ask for what's still missing
- When you have all information, confirm and say "PROFILE_COMPLETE" at the end
- Keep responses brief and natural

Current profile data: {profile_data}"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        self.memory = ConversationBufferMemory(
            memory_key="history",
            return_messages=True
        )
        
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            memory=self.memory,
            verbose=False
        )
    
    def chat(self, user_message: str, profile_data: Dict = None) -> Dict[str, Any]:
        """Continue profile building conversation"""
        if profile_data is None:
            profile_data = {}
        
        response = self.chain.predict(
            input=user_message,
            profile_data=json.dumps(profile_data, indent=2)
        )
        
        # Check if profile is complete
        is_complete = "PROFILE_COMPLETE" in response
        
        return {
            "message": response.replace("PROFILE_COMPLETE", "").strip(),
            "is_complete": is_complete,
            "profile_data": self._extract_profile_data(response, profile_data)
        }
    
    def _extract_profile_data(self, response: str, current_data: Dict) -> Dict:
        """Extract profile information from conversation (simple version)"""
        # In a production system, you'd use structured output or NER
        # For simplicity, we'll return current data
        return current_data
    
    def reset(self):
        """Reset conversation memory"""
        self.memory.clear()


class SearchAgent:
    """Agent that processes search requests and creates structured queries"""
    
    def __init__(self):
        self.llm = ChatAnthropic(
            anthropic_api_key=ANTHROPIC_API_KEY,
            model="claude-3-5-sonnet-20241022",
            temperature=0
        )
    
    def process_search(self, query_text: str) -> Dict[str, Any]:
        """Convert natural language search to structured query"""
        
        prompt = f"""Convert this search request into a structured format.

Search request: "{query_text}"

Extract:
1. Skills required (as array of strings)
2. Experience level if mentioned (junior/mid/senior or years)
3. Availability type if mentioned (full-time/part-time/freelance)
4. Location if mentioned

Return ONLY a JSON object with these fields (use null if not mentioned):
{{
    "skills": ["skill1", "skill2"],
    "experience_level": "senior" or null,
    "experience_years": 5 or null,
    "availability": "freelance" or null,
    "location": {{"city": "San Francisco", "country": "USA"}} or null
}}"""
        
        response = self.llm.invoke(prompt)
        
        try:
            # Extract JSON from response
            content = response.content
            # Find JSON in the response
            start = content.find('{')
            end = content.rfind('}') + 1
            json_str = content[start:end]
            structured_query = json.loads(json_str)
            
            return {
                "original_query": query_text,
                "structured_query": structured_query
            }
        except Exception as e:
            # Fallback to basic extraction
            return {
                "original_query": query_text,
                "structured_query": {
                    "skills": self._extract_skills(query_text),
                    "experience_level": None,
                    "availability": None,
                    "location": None
                }
            }
    
    def _extract_skills(self, text: str) -> List[str]:
        """Simple skill extraction fallback"""
        # Basic keyword matching (in production, use NER or LLM)
        common_skills = [
            "React", "Python", "JavaScript", "Design", "Figma", "Node.js",
            "Product Management", "UI/UX", "TypeScript", "SQL", "AWS"
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in common_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        
        return found_skills or ["General"]


class MatchEvaluationAgent:
    """Agent that evaluates if a candidate matches a request"""
    
    def __init__(self):
        self.llm = ChatAnthropic(
            anthropic_api_key=ANTHROPIC_API_KEY,
            model="claude-3-5-sonnet-20241022",
            temperature=0
        )
    
    def evaluate(self, request_query: Dict, candidate_profile: Dict) -> Dict[str, Any]:
        """Evaluate if candidate matches the request"""
        
        prompt = f"""Evaluate if this candidate matches the search request.

Search Request:
{json.dumps(request_query, indent=2)}

Candidate Profile:
{json.dumps(candidate_profile, indent=2)}

Provide:
1. Match score (0.0 to 1.0)
2. Matched skills (array)
3. Brief explanation (1-2 sentences)

Return ONLY a JSON object:
{{
    "is_match": true/false,
    "match_score": 0.85,
    "matched_skills": ["skill1", "skill2"],
    "explanation": "Brief explanation of why they match or don't"
}}"""
        
        response = self.llm.invoke(prompt)
        
        try:
            content = response.content
            start = content.find('{')
            end = content.rfind('}') + 1
            json_str = content[start:end]
            evaluation = json.loads(json_str)
            return evaluation
        except Exception:
            # Fallback to simple matching
            return self._simple_match(request_query, candidate_profile)
    
    def _simple_match(self, request: Dict, profile: Dict) -> Dict:
        """Simple matching fallback"""
        request_skills = set(s.lower() for s in request.get("skills", []))
        profile_skills = set(s.lower() for s in profile.get("skills", []))
        
        matched = request_skills.intersection(profile_skills)
        
        if len(request_skills) > 0:
            score = len(matched) / len(request_skills)
        else:
            score = 0.5
        
        return {
            "is_match": score >= 0.3,
            "match_score": score,
            "matched_skills": list(matched),
            "explanation": f"Matched {len(matched)} of {len(request_skills)} required skills"
        }


# Singleton instances
profile_builder = ProfileBuilderAgent()
search_agent = SearchAgent()
match_evaluator = MatchEvaluationAgent()
