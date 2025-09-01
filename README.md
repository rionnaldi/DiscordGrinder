
# Discord AI Agent Boilerplate

A customizable, modular Discord AI Agent that can be deployed across any Discord server. This boilerplate is designed for easy configuration, multi-server support, and rapid extension.

## Features

- **Multi-Server Ready**: Easily configure for any Discord server/channel
- **Intelligent AI Responses**: Uses Google Gemini AI for context-aware replies
- **Reply & Context Detection**: Responds to replies and maintains conversation history
- **MongoDB Persistence**: Stores messages and knowledge base for context
- **Non-blocking Async Architecture**: Fast, scalable, and efficient
- **Customizable Behavior**: Tune agent personality, timing, and knowledge sources

## Architecture Overview

- `discord_comm.py`: Discord API communication (fetch/send messages)
- `data_handler.py`: MongoDB operations for message/context storage
- `ai_core.py`: AI logic, Gemini API integration, intent classification
- `knowledge_retriever.py`: Knowledge base population and retrieval
- `scheduler.py`: Controls agent behavior, timing, and message cooldowns
- `main.py`: Entry point, loads config, starts agent

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/rionnaldi/DiscordGrinder
cd DiscordGrinder
python -m venv venv
venv\Scripts\activate  or source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration

Copy `.env.example` to `.env` and fill in your credentials for each server/channel you want to support:

```bash
cp .env.example .env
```

#### Required Environment Variables

- `DISCORD_USER_TOKEN`: Discord user token (NOT bot token)
- `DISCORD_CHANNEL_ID`: Target channel ID (can be a comma-separated list for multi-server)
- `MY_USER_ID`: Your Discord user ID
- `GEMINI_API_KEY`: Google Gemini API key
- `MONGODB_CONNECTION_STRING`: MongoDB connection string

#### Optional Variables

- `AGENT_NAME`: Custom name for your agent
- `AGENT_PERSONALITY`: Short description/personality prompt
- `MIN_DELAY_SECONDS`, `MAX_DELAY_SECONDS`: Timing controls
- `CONTEXT_LIMIT`: Number of messages for context

### 3. Multi-Server/Channel Setup

To run the agent on multiple servers/channels, set `DISCORD_CHANNEL_ID` to a comma-separated list:

```
DISCORD_CHANNEL_ID=123456789012345678,987654321098765432
```

You can also duplicate `.env` files or use config files per server for advanced setups.

### 4. Credentials

See below for how to obtain Discord tokens, channel IDs, and Gemini API keys.

## Running the Agent

```bash
python main.py
```

The agent will connect to all configured channels, monitor for replies, and generate AI-powered responses in real time.

## Customization

- **Personality**: Edit `AGENT_PERSONALITY` in `.env` or pass a custom prompt to the AI core
- **Knowledge Base**: Add documents to MongoDB or use `knowledge_retriever.py` to ingest new sources
- **Behavior**: Tune timing, context, and reply logic in `scheduler.py`
- **Server/Channel Targeting**: Change `DISCORD_CHANNEL_ID` or use config files for each deployment

## Advanced Usage

- **Multiple Agents**: Run multiple instances with different `.env` files or config objects
- **Custom RAG Logic**: Extend `ai_core.py` and `knowledge_retriever.py` for new knowledge sources
- **Integrate with Other APIs**: Add plugins to `ai_core.py` for more capabilities

## How to Get Credentials

### Discord User Token
1. Open Discord in your browser
2. Open Developer Tools (F12)
3. Go to Network tab
4. Send a message in any channel
5. Look for requests to `discord.com/api`
6. Find the `Authorization` header value - this is your token

### Discord Channel ID
1. Enable Developer Mode in Discord settings
2. Right-click on the target channel
3. Select "Copy ID"

### Your User ID
1. Enable Developer Mode in Discord settings
2. Right-click on your username
3. Select "Copy ID"

### Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create a new API key
3. Copy the generated key

### MongoDB Setup

- Local: `mongodb://localhost:27017/`
- Atlas: Create cluster at [MongoDB Atlas](https://www.mongodb.com/atlas) and get connection string

## Configuration Reference

```bash
# Required
DISCORD_USER_TOKEN=your_token
DISCORD_CHANNEL_ID=channel_id_1,channel_id_2
MY_USER_ID=your_user_id
GEMINI_API_KEY=your_gemini_key
MONGODB_CONNECTION_STRING=mongodb://localhost:27017/

# Optional
AGENT_NAME=DiscordGrind
AGENT_PERSONALITY="Friendly, helpful, and witty." # More detailed, better
MIN_DELAY_SECONDS=60
MAX_DELAY_SECONDS=300
CONTEXT_LIMIT=20
```

## Troubleshooting & Logs

- Colored console output for status, errors, and debug info
- All errors are handled gracefully; see logs for details
- If you encounter issues, check your credentials and network connectivity

## Safety & Best Practices

- Use responsibly and respect Discord's Terms of Service
- Avoid spamming or violating automation policies
- Consider running with bot tokens for production (requires Discord bot setup)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License & Disclaimer

This boilerplate is for educational purposes. Use at your own risk. I'm not responsible for any account suspensions or violations.
