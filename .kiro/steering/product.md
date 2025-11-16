# Product Overview

R.E.M.I (Real-time External Memory Interface) is a comprehensive mesh ingestion system that unifies messages from multiple communication platforms into a single, searchable, and AI-enhanced interface.

## Core Purpose
- **Multi-Platform Integration**: Connect Gmail, Slack, Discord, WhatsApp, Twitter/X, and other platforms
- **Real-time Processing**: Event-driven architecture with minimal latency using Redis Streams
- **Unified Data Model**: Normalize messages from different platforms into consistent schema
- **AI Enhancement**: Local-first AI processing with entity extraction, summarization, and intelligent analysis
- **Enterprise Ready**: OAuth 2.0, webhook validation, encryption, and scalable architecture

## Key Features
- Real-time message ingestion with push notifications and webhooks
- Historical message fetching and processing with pagination
- Advanced search with full-text search and entity extraction
- RESTful API with comprehensive OpenAPI documentation
- Local-first AI processing optimized for M1 Air development
- Docker support and comprehensive deployment guides
- Structured logging and health monitoring with circuit breakers

## Current Status
- Gmail connector: ✅ Fully implemented and active
- Core infrastructure: ✅ Complete (FastAPI, PostgreSQL, Redis)
- Event bus system: ✅ Redis Streams with consumer groups
- AI processing pipeline: ✅ Local models with Ollama integration
- Vector database: ✅ ChromaDB for embeddings
- Slack/Discord/WhatsApp connectors: 🚧 Planned

## Target Users
- Development teams needing unified communication data
- Organizations requiring message analytics and insights
- Systems integrators building communication workflows
- Enterprises with multi-platform communication needs
- Developers building AI-enhanced communication tools