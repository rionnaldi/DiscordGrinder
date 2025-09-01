#!/usr/bin/env python3
"""
Discord AI Chat Bot - Test Application for Phase 5: RAG Integration

This version reads from SOURCE_CHANNEL_ID, augments responses with 
technical knowledge, and posts formatted test outputs to TEST_CHANNEL_ID
for evaluation and data gathering purposes.

This version uses fully asynchronous operations.
"""

import os
import sys
import asyncio
import signal
from datetime import datetime
from dotenv import load_dotenv
from colorama import Fore, Style, init

# Import our modules
from discord_comm import DiscordCommunicator
from data_handler import MongoManager
from ai_core import AICore
from scheduler_test import SchedulerTest
from knowledge_retriever import KnowledgeRetriever

# Initialize colorama
init(autoreset=True)

class DiscordAIBotTest:
    """
    Test version of the main bot application for Phase 5 testing.
    Reads from source channel and posts formatted outputs to test channel.
    Now fully asynchronous.
    """
    
    def __init__(self):
        """Initialize the test bot with all required components."""
        self.running = False
        self.source_discord_comm = None  # For reading from source channel
        self.test_discord_comm = None    # For posting to test channel
        self.mongo_manager = None
        self.ai_core = None
        self.scheduler = None
        self.knowledge_retriever = None
        self.last_prune_time = None  # For tracking when we last pruned old messages
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n{Fore.YELLOW}[TEST] Received shutdown signal. Stopping test bot...")
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
            
            # Required environment variables for testing
            required_vars = [
                'DISCORD_USER_TOKEN',
                'SOURCE_CHANNEL_ID',
                'TEST_CHANNEL_ID',
                'MY_USER_ID',
                'GEMINI_API_KEY',
                'MONGODB_CONNECTION_STRING'
            ]
            
            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if missing_vars:
                print(f"{Fore.RED}[TEST] Missing required environment variables:")
                for var in missing_vars:
                    print(f"{Fore.RED}[TEST] - {var}")
                print(f"{Fore.YELLOW}[TEST] Please check your .env file")
                return False
            
            # Store config
            self.config = {
                'discord_token': os.getenv('DISCORD_USER_TOKEN'),
                'source_channel_id': os.getenv('SOURCE_CHANNEL_ID'),
                'test_channel_id': os.getenv('TEST_CHANNEL_ID'),
                'my_user_id': os.getenv('MY_USER_ID'),
                'gemini_api_key': os.getenv('GEMINI_API_KEY'),
                'mongodb_connection': os.getenv('MONGODB_CONNECTION_STRING'),
                'mongodb_database': os.getenv('MONGODB_DATABASE', 'discord_bot_test'),
                'mongodb_collection': os.getenv('MONGODB_COLLECTION', 'messages_test'),
                'min_delay': int(os.getenv('MIN_DELAY_SECONDS', 120)),
                'max_delay': int(os.getenv('MAX_DELAY_SECONDS', 420)),
                'context_limit': int(os.getenv('CONTEXT_LIMIT', 20)),
                'data_retrieval_interval': int(os.getenv('SCHEDULER_DATA_RETRIEVAL_INTERVAL', 60)),
                'chat_check_interval': int(os.getenv('SCHEDULER_CHAT_CHECK_INTERVAL', 30)),
                'min_time_between_messages': int(os.getenv('SCHEDULER_MIN_TIME_BETWEEN_MESSAGES', 600)),            
                'rag_confidence_threshold': float(os.getenv('RAG_CONFIDENCE_THRESHOLD', 0.78)),
                'rag_max_results': int(os.getenv('RAG_MAX_RESULTS', 8))
            }
            
            print(f"{Fore.GREEN}[TEST] Configuration loaded successfully")
            print(f"{Fore.CYAN}[TEST] Source Channel ID: {self.config['source_channel_id']}")
            print(f"{Fore.CYAN}[TEST] Test Channel ID: {self.config['test_channel_id']}")
            print(f"{Fore.CYAN}[TEST] User ID: {self.config['my_user_id']}")
            print(f"{Fore.CYAN}[TEST] Min time between messages: {self.config['min_time_between_messages']}s")
            print(f"{Fore.CYAN}[TEST] RAG confidence threshold: {self.config['rag_confidence_threshold']}")
            print(f"{Fore.CYAN}[TEST] RAG max results: {self.config['rag_max_results']}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}[TEST] Error loading configuration: {str(e)}")
            return False
    
    async def initialize_components(self) -> bool:
        """
        Initialize all bot components for testing.
        
        Returns:
            True if all components initialized successfully, False otherwise
        """
        try:
            print(f"{Fore.CYAN}[TEST] Initializing test components...")
            
            # Initialize Discord Communicator for source channel (reading)
            print(f"{Fore.CYAN}[TEST] Initializing source Discord communicator...")
            self.source_discord_comm = DiscordCommunicator(
                token=self.config['discord_token'],
                channel_id=self.config['source_channel_id'],
                my_user_id=self.config['my_user_id']
            )
            
            # Initialize Discord Communicator for test channel (posting)
            print(f"{Fore.CYAN}[TEST] Initializing test Discord communicator...")
            self.test_discord_comm = DiscordCommunicator(
                token=self.config['discord_token'],
                channel_id=self.config['test_channel_id'],
                my_user_id=self.config['my_user_id']
            )
            
            # Initialize MongoDB Manager
            print(f"{Fore.CYAN}[TEST] Initializing MongoDB manager...")
            self.mongo_manager = MongoManager(
                connection_string=self.config['mongodb_connection'],
                database_name=self.config['mongodb_database'],
                collection_name=self.config['mongodb_collection']
            )
            
            # Connect to MongoDB
            if not await self.mongo_manager.connect():
                print(f"{Fore.RED}[TEST] Failed to connect to MongoDB")
                return False
            
            # Initialize AI Core
            print(f"{Fore.CYAN}[TEST] Initializing AI core...")
            self.ai_core = AICore(api_key=self.config['gemini_api_key'])
            
            if not self.ai_core.model:
                print(f"{Fore.RED}[TEST] Failed to initialize AI core")
                return False
              # Initialize Test Scheduler
            print(f"{Fore.CYAN}[TEST] Initializing test scheduler...")
            self.scheduler = SchedulerTest(
                source_discord_comm=self.source_discord_comm,
                test_discord_comm=self.test_discord_comm,
                mongo_manager=self.mongo_manager,
                ai_core=self.ai_core,
                my_user_id=self.config['my_user_id'],
                data_retrieval_interval=self.config['data_retrieval_interval'],
                chat_check_interval=self.config['chat_check_interval'],
                min_time_between_messages=self.config['min_time_between_messages'],
                rag_confidence_threshold=self.config['rag_confidence_threshold'],
                rag_max_results=self.config['rag_max_results']
            )
              # Initialize Knowledge Retriever
            print(f"{Fore.CYAN}[TEST] Initializing knowledge retriever...")
            self.knowledge_retriever = KnowledgeRetriever(
                api_key=self.config['gemini_api_key'],
                base_urls=[""] # FILL THIS
            )
            
            print(f"{Fore.GREEN}[TEST] All test components initialized successfully")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}[TEST] Error initializing components: {str(e)}")
            return False
    
    async def test_connections(self) -> bool:
        """
        Test all connections to ensure they're working.
        
        Returns:
            True if all tests pass, False otherwise
        """
        try:
            print(f"{Fore.CYAN}[TEST] Testing connections...")
            
            # Test Source Discord API
            print(f"{Fore.CYAN}[TEST] Testing source Discord connection...")
            test_messages = await self.source_discord_comm.get_messages(limit=1)
            if test_messages is None:
                print(f"{Fore.RED}[TEST] Source Discord connection test failed")
                return False
            
            # Test Test Discord API
            print(f"{Fore.CYAN}[TEST] Testing test Discord connection...")
            test_messages_2 = await self.test_discord_comm.get_messages(limit=1)
            if test_messages_2 is None:
                print(f"{Fore.RED}[TEST] Test Discord connection test failed")
                return False
            
            # Test MongoDB
            print(f"{Fore.CYAN}[TEST] Testing MongoDB connection...")
            stats = await self.mongo_manager.get_stats()
            if not stats:
                print(f"{Fore.RED}[TEST] MongoDB connection test failed")
                return False
            
            print(f"{Fore.GREEN}[TEST] Database stats: {stats['total_messages']} messages from {stats['unique_authors']} authors")
            
            print(f"{Fore.GREEN}[TEST] All connection tests passed")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}[TEST] Error testing connections: {str(e)}")
            return False
    
    async def run_main_loop(self):
        """
        Main test application loop.
        """
        print(f"{Fore.GREEN}[TEST] Starting test main loop...")
        print(f"{Fore.YELLOW}[TEST] Press Ctrl+C to stop the test bot")
        print(f"{Fore.MAGENTA}[TEST] Reading from SOURCE channel: {self.config['source_channel_id']}")
        print(f"{Fore.MAGENTA}[TEST] Posting to TEST channel: {self.config['test_channel_id']}")
        
        self.running = True
        loop_count = 0
        
        try:
            while self.running:
                loop_count += 1
                # Print status every 10 loops (approximately every 5 minutes)
                if loop_count % 10 == 1:
                    await self._print_status(loop_count)
                
                # Daily message pruning job
                now = datetime.now()
                if self.last_prune_time is None or (now - self.last_prune_time).days >= 1:
                    if now.hour == 5:  # Run at 5 AM to avoid peak times
                        print(f"{Fore.CYAN}[TEST] Running daily message pruning job...")
                        await self.mongo_manager.prune_old_messages()
                        self.last_prune_time = now
                
                # Data retrieval (from source channel)
                # Run every minute
                current_time = datetime.now()
                if not self.scheduler.last_data_retrieval or (
                    (current_time - self.scheduler.last_data_retrieval).total_seconds() >= 
                    self.scheduler.data_retrieval_interval
                ):
                    print(f"{Fore.CYAN}[TEST] Running data retrieval from source channel...")
                    await self.scheduler.run_data_retrieval()
                
                # Chat logic (posts to test channel)
                # Run every 30 seconds
                if not self.scheduler.last_message_check or (
                    (current_time - self.scheduler.last_message_check).total_seconds() >= 
                    self.scheduler.chat_check_interval
                ):
                    print(f"{Fore.CYAN}[TEST] Running chat logic...")
                    self.scheduler.last_message_check = current_time
                    await self.scheduler.run_chat_logic()
                
                # Sleep for 10 seconds before next iteration
                await asyncio.sleep(10)
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}[TEST] Keyboard interrupt received")
        except Exception as e:
            print(f"{Fore.RED}[TEST] Error in main loop: {str(e)}")
        finally:
            self.running = False
    
    async def _print_status(self, loop_count: int):
        """
        Print current test bot status.
        
        Args:
            loop_count: Current loop iteration number
        """
        try:
            print(f"\n{Fore.MAGENTA}{'='*60}")
            print(f"{Fore.MAGENTA}[TEST-STATUS] Test Bot Status Report - Loop #{loop_count}")
            print(f"{Fore.MAGENTA}{'='*60}")
              # Get scheduler status
            status = await self.scheduler.get_status()
            for key, value in status.items():
                print(f"{Fore.CYAN}[TEST-STATUS] {key.replace('_', ' ').title()}: {value}")
            
            # Get database stats
            stats = await self.mongo_manager.get_stats()
            if stats:
                print(f"{Fore.CYAN}[TEST-STATUS] Total Messages in DB: {stats.get('total_messages', 0)}")
                print(f"{Fore.CYAN}[TEST-STATUS] Unique Authors: {stats.get('unique_authors', 0)}")
            
            # Get knowledge base stats
            kb_stats = await self.mongo_manager.get_technical_knowledge_stats()
            if kb_stats:
                print(f"{Fore.CYAN}[TEST-STATUS] Knowledge Base Chunks: {kb_stats.get('chunk_count', 0)}")
                print(f"{Fore.CYAN}[TEST-STATUS] Knowledge Base Sources: {kb_stats.get('source_count', 0)}")
            
            print(f"{Fore.MAGENTA}{'='*60}\n")
            
        except Exception as e:
            print(f"{Fore.RED}[TEST] Error printing status: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources before shutdown."""
        try:
            print(f"{Fore.YELLOW}[TEST] Cleaning up...")
            
            if self.mongo_manager:
                await self.mongo_manager.close_connection()
            
            print(f"{Fore.GREEN}[TEST] Cleanup completed")
            
        except Exception as e:
            print(f"{Fore.RED}[TEST] Error during cleanup: {str(e)}")
    
    async def run(self) -> int:
        """
        Main entry point for the test bot.
        
        Returns:
            Exit code (0 for success, 1 for error)
        """
        try:
            print(f"{Fore.GREEN}{'='*60}")
            print(f"{Fore.GREEN}Discord AI Chat Bot - TEST MODE Starting...")
            print(f"{Fore.GREEN}Phase 5: RAG Integration - Testing")
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
              # Populate knowledge base
            print(f"{Fore.CYAN}[TEST] Populating technical knowledge base...")
            stored_count = await self.knowledge_retriever.populate_knowledge_base(self.mongo_manager)
            print(f"{Fore.GREEN}[TEST] Knowledge base populated with {stored_count} chunks")
            
            # Get knowledge base stats
            kb_stats = await self.mongo_manager.get_technical_knowledge_stats()
            print(f"{Fore.GREEN}[TEST] Knowledge base stats: {kb_stats.get('chunk_count', 0)} chunks in database")
            
            # Run initial data retrieval
            print(f"{Fore.CYAN}[TEST] Running initial data retrieval from source channel...")
            await self.scheduler.run_data_retrieval()
            
            # Start main loop
            await self.run_main_loop()
            
            return 0
            
        except Exception as e:
            print(f"{Fore.RED}[TEST] Fatal error: {str(e)}")
            return 1
        finally:
            await self.cleanup()

async def main_async():
    """Async main entry point for test bot."""
    # Create and run test bot
    bot = DiscordAIBotTest()
    exit_code = await bot.run()
    return exit_code

def main():
    """Main entry point for test bot."""
    try:
        # Run the async event loop
        exit_code = asyncio.run(main_async())
        print(f"{Fore.YELLOW}[TEST] Test bot shutdown complete. Exit code: {exit_code}")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"{Fore.YELLOW}[TEST] Keyboard interrupt received. Shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()
