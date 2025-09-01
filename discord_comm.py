import aiohttp
import json
import os
from typing import List, Dict, Optional
from colorama import Fore, Style, init
import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Initialize colorama for colored output
init(autoreset=True)

class DiscordCommunicator:
    """
    Handles all Discord API interactions including fetching and sending messages.
    Fully asynchronous implementation using aiohttp.
    """
    
    def __init__(self, token: str, channel_id: str, my_user_id: str):
        """
        Initialize the Discord communicator.
        
        Args:
            token: Discord user token for authentication
            channel_id: Target Discord channel ID
            my_user_id: Your user ID to identify own messages
        """
        self.token = token
        self.channel_id = channel_id
        self.my_user_id = my_user_id
        self.base_url = "https://discord.com/api/v9"
        self.headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.session = None
    
    async def _get_session(self):
        """
        Get or create an aiohttp ClientSession.
        
        Returns:
            aiohttp ClientSession
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """
        Close the aiohttp session.
        """
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_messages(self, limit: int = 100) -> Optional[List[Dict]]:
        """
        Fetch messages from the specified Discord channel.
        
        Args:
            limit: Number of messages to fetch (max 100)
            
        Returns:
            List of message dictionaries or None if error
        """
        try:
            url = f"{self.base_url}/channels/{self.channel_id}/messages"
            params = {"limit": min(limit, 100)}
            print(f"{Fore.CYAN}[DISCORD] Fetching messages from channel {self.channel_id}...")
            
            session = await self._get_session()
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    messages = await response.json()
                    print(f"{Fore.GREEN}[DISCORD] Successfully fetched {len(messages)} messages")
                    return messages
                else:
                    text = await response.text()
                    print(f"{Fore.RED}[DISCORD] Error fetching messages: {response.status} - {text}")
                    return None
                
        except Exception as e:
            print(f"{Fore.RED}[DISCORD] Exception while fetching messages: {str(e)}")
            return None
    async def send_message(self, content: str, reply_to_message_id: Optional[str] = None) -> bool:
        """
        Send a message, optionally as a reply to a specific message.
        
        Args:
            content: Message content to send
            reply_to_message_id: Optional message ID to reply to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/channels/{self.channel_id}/messages"
            
            # Construct the payload
            payload = {"content": content}
            
            # If it's a reply, add the message_reference object
            if reply_to_message_id:
                payload["message_reference"] = {
                    "message_id": reply_to_message_id,
                    "channel_id": self.channel_id
                }
                print(f"{Fore.CYAN}[DISCORD] Sending REPLY to message {reply_to_message_id}...")
            else:
                print(f"{Fore.CYAN}[DISCORD] Sending standard message...")
            
            session = await self._get_session()
            async with session.post(url, headers=self.headers, json=payload) as response:
                if response.status == 200:
                    print(f"{Fore.GREEN}[DISCORD] Message sent successfully")
                    return True
                else:
                    text = await response.text()
                    print(f"{Fore.RED}[DISCORD] Error sending message: {response.status} - {text}")
                    return False
                
        except Exception as e:
            print(f"{Fore.RED}[DISCORD] Exception while sending message: {str(e)}")
            return False
    
    async def get_my_last_message(self, limit: int = 100) -> Optional[Dict]:
        """
        Retrieve the last message sent by the user account.
        
        Args:
            limit: Number of recent messages to search through
            
        Returns:
            Last message dict sent by user or None if not found
        """
        try:
            messages = await self.get_messages(limit)
            if not messages:
                return None
            
            # Find the most recent message from this user
            for message in messages:
                if message.get("author", {}).get("id") == self.my_user_id:
                    print(f"{Fore.YELLOW}[DISCORD] Found my last message: {message.get('content', '')[:50]}...")
                    return message
            
            print(f"{Fore.YELLOW}[DISCORD] No messages found from user {self.my_user_id}")
            return None
            
        except Exception as e:
            print(f"{Fore.RED}[DISCORD] Exception while getting last message: {str(e)}")
            return None
    async def check_replies_to_message(self, message_id: str, limit: int = 100) -> List[Dict]:
        """
        Check if there are any replies to a specific message.
        
        Args:
            message_id: ID of the message to check for replies
            limit: Number of recent messages to search through
            
        Returns:
            List of messages that reply to the specified message
        """
        try:
            messages = await self.get_messages(limit)
            if not messages:
                return []
            
            replies = []
            for message in messages:
                # Check if this message is a reply to our message
                message_ref = message.get("message_reference")
                if message_ref and message_ref.get("message_id") == message_id:
                    replies.append(message)
            
            if replies:
                print(f"{Fore.YELLOW}[DISCORD] Found {len(replies)} replies to message {message_id}")
            
            return replies
            
        except Exception as e:
            print(f"{Fore.RED}[DISCORD] Exception while checking replies: {str(e)}")
            return []