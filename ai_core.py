import google.generativeai as genai
from typing import List, Dict, Optional
import random
import re
from colorama import Fore, Style, init

# Initialize colorama for colored output
init(autoreset=True)

class AICore:
    """
    Handles AI interactions using Google Gemini for generating responses and chat messages.
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        """
        Initialize the AI core with Gemini API.
        
        Args:
            api_key: Google Gemini API key
            model_name: Model to use (default: gemini-1.5-flash)
        """
        self.api_key = api_key
        self.model_name = model_name
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            print(f"{Fore.GREEN}[AI] Initialized Gemini model: {model_name}")
        except Exception as e:
            print(f"{Fore.RED}[AI] Failed to initialize Gemini: {str(e)}")
            self.model = None
    
    async def generate_reply(self, original_message: str, replying_message: str, context: List[Dict] = None) -> Optional[str]:
        """
        Generate a reply to a message that responded to our original message.
        
        Args:
            original_message: Our original message content
            replying_message: The message replying to ours
            context: Optional context from recent conversation
            
        Returns:
            Generated reply or None if error
        """
        if not self.model:
            return None
        
        try:
            # Build context string
            context_str = ""
            if context:
                for msg in context:
                    author = msg.get("author", {})
                    author_name = author.get("username", "Unknown")
                    content = msg.get("content", "")
                    context_str += f"{author_name}: {content}\n"
            
            # Build Chain-of-Thought prompt
            prompt = f"""You are an Regular User participating in a Discord conversation. Someone has replied to your message, and you need to respond naturally.

Original conversation context:
{context_str}

Your original message: {original_message}

The reply you received: {replying_message}

Think through your response step by step:

1) Analyze: First, analyze the reply and understand what the user is asking or saying. Consider any questions, sentiment, or information they've shared.

2) Plan: Consider how you should respond. What information or perspective would be helpful? How can you keep the conversation engaging?

3) Respond: Write a natural, conversational response that addresses their message directly. Keep your tone casual and friendly. Don't write too long or complex; it should feel like a real chat message. Don't use emojis or overly casual language unless it fits the context. Don't use capital case.

Your response should be brief and feel like a natural part of the ongoing conversation. Avoid sounding robotic or overly formal. Don't use these words:
- Gm / Gn
- Hello / Hi
- Role
- Good
- Bitch
- Jack of
- Hentai
- Kill yourself
- Bondage
- Shitty

Format your answer as:
Analyze: [your analysis]
Plan: [your plan]
Response: [your final response]"""

            # Generate response
            generation = await self.model.generate_content_async(prompt)
            response_text = generation.text
            
            # Extract the "Response:" part from Chain-of-Thought output
            match = re.search(r'Response:\s*(.*?)(?=$|\n\n|\Z)', response_text, re.DOTALL)
            if match:
                final_response = match.group(1).strip()
            else:
                # Fallback if we can't find the response part
                final_response = response_text.split('\n')[-1].strip()
            
            print(f"{Fore.CYAN}[AI] Generated reply: {final_response}...")
            return final_response
            
        except Exception as e:
            print(f"{Fore.RED}[AI] Error generating reply: {str(e)}")
            return None
    
    async def generate_random_chat(self, context: List[Dict] = None) -> Optional[str]:
        """
        Generate a random chat message to start a conversation.
        
        Args:
            context: Optional context from recent conversation
            
        Returns:
            Generated message or None if error
        """
        if not self.model:
            return None
        
        try:
            # Build context string
            context_str = ""
            if context:
                for msg in context:
                    author = msg.get("author", {})
                    author_name = author.get("username", "Unknown")
                    content = msg.get("content", "")
                    context_str += f"{author_name}: {content}\n"
            
            # Build Chain-of-Thought prompt
            prompt = f"""You are an Regular User participating in a Discord conversation. You're looking to start or contribute to a conversation with a message that feels natural and engaging.

Recent conversation context:
{context_str}

Think through your message step by step:

1) Analyze: First, analyze the recent conversation. What topics are being discussed? What's the tone and style of the conversation?

2) Plan: Consider what kind of message would fit naturally into this conversation. Should you ask a question, share an observation, or introduce a new but related topic?

3) Respond: Write a natural, conversational message that would fit well in this chat. Keep your tone casual and friendly. Don't write too long or complex; it should feel like a real chat message. Don't use emojis or overly casual language unless it fits the context. Don't use capital case. Don't mention or tag anyone specifically.

Your message should be brief and feel like it's coming from a real person. Avoid sounding robotic or overly formal. Don't use these words:
- Gm / Gn
- Hello / Hi
- Role
- Good
- Bitch
- Jack of
- Hentai
- Kill yourself
- Bondage
- Shitty

Format your answer as:
Analyze: [your analysis]
Plan: [your plan]
Response: [your final message]"""

            # Generate response
            generation = await self.model.generate_content_async(prompt)
            response_text = generation.text
            
            # Extract the "Response:" part from Chain-of-Thought output
            match = re.search(r'Response:\s*(.*?)(?=$|\n\n|\Z)', response_text, re.DOTALL)
            if match:
                final_response = match.group(1).strip()
            else:
                # Fallback if we can't find the response part
                final_response = response_text.split('\n')[-1].strip()
            
            print(f"{Fore.CYAN}[AI] Generated random chat: {final_response}...")
            return final_response
            
        except Exception as e:
            print(f"{Fore.RED}[AI] Error generating random chat: {str(e)}")
            return None
    
    async def generate_response(self, user_message: str, context: List[Dict] = None, technical_context: List[Dict] = None) -> Optional[str]:
        """
        Generate a response to a user message.
        
        Args:
            user_message: The user's message content
            context: Optional context from recent conversation
            technical_context: Optional technical context from knowledge base
            
        Returns:
            Generated response or None if error
        """
        if not self.model:
            return None
        
        try:
            # Build conversation context string
            context_str = ""
            if context:
                for msg in context:
                    author = msg.get("author", {})
                    author_name = author.get("username", "Unknown")
                    content = msg.get("content", "")
                    context_str += f"{author_name}: {content}\n"
            
            # Build technical context string
            tech_context_str = ""
            if technical_context:
                tech_context_str = "Relevant information from our knowledge base:\n"
                for i, chunk in enumerate(technical_context, 1):
                    content = chunk.get("content", "")
                    source = chunk.get("source_url", "Unknown source")
                    tech_context_str += f"{i}. {content}\nSource: {source}\n\n"
            
            # Build Chain-of-Thought prompt
            prompt = f"""You are an Regular User participating in a Discord conversation. Someone has sent a message, and you need to respond helpfully and naturally.

Recent conversation context:
{context_str}

The message you need to respond to: {user_message}

{tech_context_str}

Think through your response step by step:

1) Analyze: First, analyze the message and understand what the user is asking or saying. Consider any questions, sentiment, or information they've shared. If there's relevant technical information in the context provided, consider how it applies.

2) Plan: Consider how you should respond. What information or perspective would be helpful? How can you keep the conversation engaging? If you're using information from the knowledge base, plan how to integrate it naturally.

3) Respond: Write a natural, conversational response that addresses their message directly. Keep your tone casual and friendly.

Your response should be brief and feel like a natural part of the ongoing conversation. Avoid sounding robotic or overly formal. Don't write too long or complex; it should feel like a real chat message. Don't use emojis or overly casual language unless it fits the context. Don't use capital case. Don't use these words:
- Gm / Gn
- Hello / Hi
- Role
- Good
- Bitch
- Jack of
- Hentai
- Kill yourself
- Bondage
- Shitty

Format your answer as:
Analyze: [your analysis]
Plan: [your plan]
Response: [your final response]"""            # Generate response
            generation = await self.model.generate_content_async(prompt)
            response_text = generation.text
            
            # Extract the "Response:" part from Chain-of-Thought output
            match = re.search(r'Response:\s*(.*?)(?=$|\n\n|\Z)', response_text, re.DOTALL)
            if match:
                final_response = match.group(1).strip()
            else:
                # Fallback if we can't find the response part
                final_response = response_text.split('\n')[-1].strip()
            
            print(f"{Fore.CYAN}[AI] Generated response: {final_response}...")
            return final_response
            
        except Exception as e:
            print(f"{Fore.RED}[AI] Error generating response: {str(e)}")
            return None
    
    async def generate_embedding(self, text: str, task_type: str = "RETRIEVAL_QUERY") -> List[float]:
        """
        Generate an embedding vector for the text.
        
        Args:
            text: Text to generate embedding for
            task_type: Type of embedding task (RETRIEVAL_QUERY or RETRIEVAL_DOCUMENT)
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            # Use the embedding model
            embedding = await genai.embed_content_async(
                model="models/text-embedding-004",
                content=text,
                task_type=task_type
            )
            
            # Return the embedding values
            return embedding['embedding']
            
        except Exception as e:
            print(f"{Fore.RED}[AI] Error generating embedding: {str(e)}")
            return []
        
    async def generate_search_query(self, text: str) -> str:
        """
        Generate an optimized search query from user text using Gemini AI.
        
        Args:
            text: User's message or query text
            
        Returns:
            Optimized search query string
        """
        if not self.model or not text:
            return text
        
        try:
            prompt = f"""Based on the user's message, what is the core topic or question? 
Formulate a clean search query of 3-5 keywords that would be perfect for finding relevant documents in a technical knowledge base.
Focus on extracting the most important technical terms, concepts, and entities.

User Message: "{text}"

Search Query:"""

            generation = await self.model.generate_content_async(prompt)
            query = generation.text.strip()
            
            print(f"{Fore.CYAN}[AI] Generated search query: {query}")
            return query
            
        except Exception as e:
            print(f"{Fore.RED}[AI] Error generating search query: {str(e)}")
            return text
        
    async def generate_proactive_chat(self, context: List[Dict]) -> Optional[str]:
        """Analyzes a conversation and generates a relevant message to join in."""
        if not self.model or not context:
            return None
        
        context_str = "\n".join([f"{msg.get('author', {}).get('username', 'Unknown')}: {msg.get('content', '')}" for msg in context])

        prompt = f"""You are an Regular User analyzing a Discord conversation between other users. Your goal is to decide if it's a good time to join the conversation and, if so, what to say. 
Don't use these words:
- Gm / Gn
- Hello / Hi
- Role
- Good
- Bitch
- Jack of
- Hentai
- Kill yourself
- Bondage
- Shitty

Recent Conversation:
{context_str}

Think step-by-step:

1. Analyze: Read the conversation. What is the topic? What is the mood? Is the conversation open-ended, or does it seem like a private or finished discussion?
2. Decide: Based on your analysis, should you join in? Only join if you have something relevant and non-intrusive to add. If it's a simple back-and-forth, a sensitive topic, or seems resolved, decide 'no'.
3. Plan (if joining): If you decide to join, plan a brief, casual message that adds to the conversation. This could be a related thought, a question, or a supportive comment.
4. Respond: If your decision was 'yes', write your message. If 'no', simply write "PASS".

Format your answer as:
Analyze: [your analysis]
Decide: [Yes or No]
Plan: [your plan if the decision is Yes]
Response: [your final message, or PASS]"""

        try:
            generation = await self.model.generate_content_async(prompt)
            response_text = generation.text

            # Check if the AI decided to pass
            if "pass" in response_text.lower():
                print(f"{Fore.YELLOW}[AI] Decided to pass on proactive chat.")
                return None

            match = re.search(r'Response:\s*(.*)', response_text, re.DOTALL | re.IGNORECASE)
            if match:
                final_response = match.group(1).strip()
                # Final check to ensure we don't return "PASS"
                if "pass" in final_response.lower(): 
                    return None
                print(f"{Fore.CYAN}[AI] Generated proactive chat: {final_response}...")
                return final_response
            return None
        except Exception as e:
            print(f"{Fore.RED}[AI] Error generating proactive chat: {str(e)}")
            return None
    
    async def classify_intent(self, message: str) -> str:
        """
        Quickly classifies the user's intent to decide if a full RAG process is needed.
        Returns one of: 'question', 'social_reply', 'statement'.
        """
        if not self.model:
            return "unknown"

        prompt = f"""Analyze the user's message and classify its primary intent. Choose only from the following categories:
- 'question' (if the user is asking for information, help, or clarification)
- 'social_reply' (for simple agreements, disagreements, jokes, thanks, or greetings like 'lol', 'gm', 'ty')
- 'statement' (if the user is just stating an opinion or fact without asking a question)

Message: "{message}"

Classification:"""

        try:
            # Use a specific, lean generation config for this cheap and fast call
            generation_config = genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=10, # Restrict output to just a few tokens
                temperature=0.0      # Be deterministic for classification
            )
            generation = await self.model.generate_content_async(prompt, generation_config=generation_config)
            
            # Clean the output to get just the category word
            intent = generation.text.strip().lower().replace("'", "")
            return intent
        except Exception as e:
            print(f"{Fore.RED}[AI] Error classifying intent: {str(e)}")
            return "unknown"
