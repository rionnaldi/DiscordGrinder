#!/usr/bin/env python3
"""
Discord AI Chat Bot - Main Application

An AI-powered Discord chat automation bot that:
- Fetches messages from Discord channels
- Stores conversation data in MongoDB
- Uses Google Gemini AI to generate natural responses
- Responds to replies and participates in conversations
- Operates with human-like timing and behavior
"""

import os
import sys
import time
import signal
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from colorama import Fore, Style, init

# Import our modules
from discord_comm import DiscordCommunicator
from data_handler import MongoManager
from ai_core import AICore
from scheduler import Scheduler
from knowledge_retriever import KnowledgeRetriever

# Initialize colorama
init(autoreset=True)

class DiscordAIBot:
    """
    Main bot application that orchestrates all components.
    """
    
    def __init__(self):
        """Initialize the bot with all required components."""
        self.running = False
        self.discord_comm = None
        self.mongo_manager = None
        self.ai_core = None
        self.scheduler = None
        self.knowledge_retriever = None
          # State variables for behavioral governor
        self.agent_last_post_time = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n{Fore.YELLOW}[MAIN] Received shutdown signal. Stopping bot...")
        self.running = False
    
    def load_config(self) -> bool:
        """
        Load configuration from environment variables.
        
        Returns:
            True if config loaded successfully, False otherwise
        """
        try:
            # Load .env file
            load_dotenv()
            
            # Required environment variables
            required_vars = [
                'DISCORD_USER_TOKEN',
                'DISCORD_CHANNEL_ID',
                'MY_USER_ID',
                'GEMINI_API_KEY',
                'MONGODB_CONNECTION_STRING'
            ]
            
            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if missing_vars:
                print(f"{Fore.RED}[MAIN] Missing required environment variables:")
                for var in missing_vars:
                    print(f"{Fore.RED}[MAIN] - {var}")
                print(f"{Fore.YELLOW}[MAIN] Please check your .env file")
                return False
            
            # Store config
            self.config = {
                'discord_token': os.getenv('DISCORD_USER_TOKEN'),
                'channel_id': os.getenv('DISCORD_CHANNEL_ID'),
                'my_user_id': os.getenv('MY_USER_ID'),
                'gemini_api_key': os.getenv('GEMINI_API_KEY'),
                'mongodb_connection': os.getenv('MONGODB_CONNECTION_STRING'),
                'mongodb_database': os.getenv('MONGODB_DATABASE', 'discord_bot'),
                'mongodb_collection': os.getenv('MONGODB_COLLECTION', 'messages'),
                'min_delay': int(os.getenv('MIN_DELAY_SECONDS', 120)),
                'max_delay': int(os.getenv('MAX_DELAY_SECONDS', 420)),
                
                # Load scheduler configuration parameters
                'data_retrieval_interval': int(os.getenv('SCHEDULER_DATA_RETRIEVAL_INTERVAL', 60)),
                'chat_check_interval': int(os.getenv('SCHEDULER_CHAT_CHECK_INTERVAL', 30)),
                'min_time_between_messages': int(os.getenv('SCHEDULER_MIN_TIME_BETWEEN_MESSAGES', 600)),
                
                # Load RAG configuration parameters
                'rag_confidence_threshold': float(os.getenv('RAG_CONFIDENCE_THRESHOLD', 0.78)),
                'rag_max_results': int(os.getenv('RAG_MAX_RESULTS', 8))
            }
            
            print(f"{Fore.GREEN}[MAIN] Configuration loaded successfully")
            print(f"{Fore.CYAN}[MAIN] Channel ID: {self.config['channel_id']}")
            print(f"{Fore.CYAN}[MAIN] User ID: {self.config['my_user_id']}")
            print(f"{Fore.CYAN}[MAIN] Message delays: {self.config['min_delay']}-{self.config['max_delay']}s")
            
            return True
            
        except Exception as e:
            print(f"{Fore.RED}[MAIN] Error loading configuration: {str(e)}")
            return False
    
    async def initialize_components(self) -> bool:
        """
        Initialize all bot components.
        
        Returns:
            True if all components initialized successfully, False otherwise
        """
        try:
            print(f"{Fore.CYAN}[MAIN] Initializing components...")
            
            # Initialize Discord Communicator
            print(f"{Fore.CYAN}[MAIN] Initializing Discord communicator...")
            self.discord_comm = DiscordCommunicator(
                token=self.config['discord_token'],
                channel_id=self.config['channel_id'],
                my_user_id=self.config['my_user_id']
            )
            
            # Initialize MongoDB Manager
            print(f"{Fore.CYAN}[MAIN] Initializing MongoDB manager...")
            self.mongo_manager = MongoManager(
                connection_string=self.config['mongodb_connection'],
                database_name=self.config['mongodb_database'],
                collection_name=self.config['mongodb_collection']
            )
            
            # Connect to MongoDB
            if not await self.mongo_manager.connect():
                print(f"{Fore.RED}[MAIN] Failed to connect to MongoDB")
                return False
            
            # Initialize AI Core
            print(f"{Fore.CYAN}[MAIN] Initializing AI core...")
            self.ai_core = AICore(api_key=self.config['gemini_api_key'])
            
            if not self.ai_core.model:
                print(f"{Fore.RED}[MAIN] Failed to initialize AI core")
                return False
            
            # Initialize Knowledge Retriever
            print(f"{Fore.CYAN}[MAIN] Initializing Knowledge Retriever...")
            self.knowledge_retriever = KnowledgeRetriever(api_key=self.config['gemini_api_key'], base_urls=[""]) # Fill base_urls optionally
            
            # Initialize Scheduler
            print(f"{Fore.CYAN}[MAIN] Initializing scheduler...")
            self.scheduler = Scheduler(
                discord_comm=self.discord_comm,
                mongo_manager=self.mongo_manager,
                ai_core=self.ai_core,
                my_user_id=self.config['my_user_id']
                # min_delay=self.config['min_delay'],
                # max_delay=self.config['max_delay']
            )
            
            print(f"{Fore.GREEN}[MAIN] All components initialized successfully")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}[MAIN] Error initializing components: {str(e)}")
            return False
    
    async def test_connections(self) -> bool:
        """
        Test all connections to ensure they're working.
        
        Returns:
            True if all tests pass, False otherwise
        """
        try:
            print(f"{Fore.CYAN}[MAIN] Testing connections...")
            
            # Test Discord API
            print(f"{Fore.CYAN}[MAIN] Testing Discord connection...")
            test_messages = await self.discord_comm.get_messages(limit=1)
            if test_messages is None:
                print(f"{Fore.RED}[MAIN] Discord connection test failed")
                return False
            
            # Test MongoDB
            print(f"{Fore.CYAN}[MAIN] Testing MongoDB connection...")
            stats = await self.mongo_manager.get_stats()
            if not stats:
                print(f"{Fore.RED}[MAIN] MongoDB connection test failed")
                return False
            
            print(f"{Fore.GREEN}[MAIN] Database stats: {stats['total_messages']} messages from {stats['unique_authors']} authors")
            
            print(f"{Fore.GREEN}[MAIN] All connection tests passed")
            return True
        except Exception as e:
            print(f"{Fore.RED}[MAIN] Error testing connections: {str(e)}")
            return False
    
    async def run_main_loop(self):
        """
        Main event loop for the bot.
        """
        try:
            print(f"{Fore.GREEN}[MAIN] Starting main event loop...")
            self.running = True
            # Main loop
            while self.running:
                try:
                    # Fetch and store new messages
                    if not self.scheduler.last_data_retrieval or \
                       (datetime.now() - self.scheduler.last_data_retrieval).total_seconds() >= self.scheduler.data_retrieval_interval:
                        await self.scheduler.run_data_retrieval()
                    
                    # Check for replies and run chat logic
                    if not self.scheduler.last_message_check or \
                       (datetime.now() - self.scheduler.last_message_check).total_seconds() >= self.scheduler.chat_check_interval:
                        await self.scheduler.run_chat_logic()
                        self.scheduler.last_message_check = datetime.now()
                    # Update agent_last_post_time if a message was sent
                    if self.scheduler.last_sent_message_time != self.agent_last_post_time:
                        self.agent_last_post_time = self.scheduler.last_sent_message_time
                    
                    # Print status every 10 minutes
                    if int(time.time()) % 600 < 1:
                        await self.print_status()
                    
                    # Sleep to avoid excessive CPU usage
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"{Fore.RED}[MAIN] Error in main loop iteration: {str(e)}")
                    await asyncio.sleep(5)  # Sleep longer on error
            
            print(f"{Fore.YELLOW}[MAIN] Main event loop stopped")
            
        except Exception as e:
            print(f"{Fore.RED}[MAIN] Error in main event loop: {str(e)}")
    
    async def print_status(self):
        """Print current status information."""
        try:
            print(f"{Fore.MAGENTA}{'='*60}")
            print(f"{Fore.MAGENTA}Discord AI Bot Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{Fore.MAGENTA}{'='*60}")
            
            # Get scheduler status
            status = await self.scheduler.get_status()
            for key, value in status.items():
                print(f"{Fore.CYAN}[STATUS] {key.replace('_', ' ').title()}: {value}")
            
            # Print behavioral governor status
            print(f"{Fore.CYAN}[STATUS] Agent Last Post Time: {self.agent_last_post_time}")
            print(f"{Fore.MAGENTA}{'='*60}\n")
            
        except Exception as e:
            print(f"{Fore.RED}[MAIN] Error printing status: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources before shutdown."""
        try:
            print(f"{Fore.YELLOW}[MAIN] Cleaning up...")
            
            if self.discord_comm:
                await self.discord_comm.close()
            
            if self.mongo_manager:
                await self.mongo_manager.close_connection()
            
            print(f"{Fore.GREEN}[MAIN] Cleanup completed")
            
        except Exception as e:
            print(f"{Fore.RED}[MAIN] Error during cleanup: {str(e)}")
    
    async def run(self) -> int:
        """
        Main entry point for the bot.
        
        Returns:
            Exit code (0 for success, 1 for error)
        """
        try:
            print(f"{Fore.GREEN}{'='*60}")
            print(f"{Fore.GREEN}Discord AI Chat Bot Starting...")
            print(f"{Fore.GREEN}{'='*60}")
            
            # Load configuration
            if not self.load_config():
                return 1
            
            # Initialize components
            if not await self.initialize_components():
                return 1
              # Test connections
            if not await self.test_connections():
                return 1
            
            # Populate knowledge base (optional)
            populate_knowledge = input(f"{Fore.CYAN}Do you want to populate the knowledge base? (y/n): ").lower() == 'y'
            if populate_knowledge:
                print(f"{Fore.CYAN}[MAIN] Populating knowledge base...")
                stored_count = await self.knowledge_retriever.populate_knowledge_base(self.mongo_manager)
                print(f"{Fore.GREEN}[MAIN] Knowledge base populated with {stored_count} chunks")
            
            # Prune old messages (optional)
            prune_messages = input(f"{Fore.CYAN}Do you want to prune old messages from the database? (y/n): ").lower() == 'y'
            if prune_messages:
                days_to_keep = input(f"{Fore.CYAN}How many days of messages do you want to keep? (Enter for today only): ")
                if days_to_keep and days_to_keep.isdigit():
                    days = int(days_to_keep)
                    print(f"{Fore.CYAN}[MAIN] Pruning messages older than {days} days...")
                    deleted_count = await self.mongo_manager.prune_old_messages(days)
                else:
                    print(f"{Fore.CYAN}[MAIN] Pruning messages older than today...")
                    deleted_count = await self.mongo_manager.prune_old_messages()
                print(f"{Fore.GREEN}[MAIN] Successfully pruned {deleted_count} old messages")
            
            # Run main loop
            await self.run_main_loop()
            
            # Cleanup
            await self.cleanup()
            
            print(f"{Fore.GREEN}[MAIN] Bot stopped successfully")
            return 0
            
        except Exception as e:
            print(f"{Fore.RED}[MAIN] Error running bot: {str(e)}")
            return 1

def main():
    """Main function."""
    bot = DiscordAIBot()
    return asyncio.run(bot.run())

if __name__ == "__main__":
    sys.exit(main())
