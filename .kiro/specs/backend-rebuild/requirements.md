# Requirements Document

## Introduction

This document defines requirements for rebuilding the R.E.M.I backend from scratch as a communication aggregator system. The previous backend implementation has proven difficult to run and maintain. This rebuild focuses on four distinct, independently testablugh four distinct, testable stages: user connection flow, data collection and cleaning, contact matching, and AI ingestion/summarization.

## Glossary

- **Platform**: A communication service (Gmail, Slack, Discord, WhatsApp, Twitter, Telegram)
- **Connection Flow**: The process of authenticating and linking a user's account to a Platform
- **Message Thread**: A conversation or sequence of messages between participants
- **Contact**: A person or entity that the user communicates with across Platforms
- **Contact Matching**: The process of identifying which Contact corresponds to each Message Thread
- **Data Cleaning**: The process of normalizing and standardizing messages from different Platforms
- **AI Ingestion**: The process of analyzing messages using AI models for insights
- **Backend System**: The server application that orchestrates all four stages
- **User**: A person using the Backend System to aggregate their communications
- **OAuth Flow**: The authentication process for connecting to Platforms
- **Bridge**: A service that connects to a Platform (e.g., Mautrix, Baileys, or WhatsApp Business API for WhatsApp)

## Requirements

### Requirement 1: User Platform Connection

**User Story:** As a User, I want to connect my accounts from multiple Platforms, so that the Backend System can access my messages.

#### Acceptance Criteria

1. WHEN a User initiates a connection to a Platform, THE Backend System SHALL present the appropriate OAuth Flow for that Platform
2. WHEN a User completes the OAuth Flow successfully, THE Backend System SHALL store the authentication credentials securely
3. WHEN a User's authentication credentials expire, THE Backend System SHALL refresh the credentials automatically
4. THE Backend System SHALL support connection to Gmail, Slack, Discord, WhatsApp, Twitter, and Telegram
5. WHEN a User disconnects from a Platform, THE Backend System SHALL revoke the stored credentials and stop data collection from that Platform

### Requirement 2: Platform Data Collection

**User Story:** As a User, I want the Backend System to collect my messages from connected Platforms, so that I have a unified view of my communications.

#### Acceptance Criteria

1. WHEN a Platform connection is active, THE Backend System SHALL fetch historical messages from that Platform
2. WHEN new messages arrive on a Platform, THE Backend System SHALL collect them in real-time
3. THE Backend System SHALL handle rate limits imposed by each Platform without data loss
4. WHEN a Platform API returns an error, THE Backend System SHALL retry the request with exponential backoff
5. WHERE WhatsApp is the Platform, THE Backend System SHALL use an appropriate connection method (WhatsApp Business API, Mautrix bridge, or Baileys library) based on reliability and feature requirements

### Requirement 3: Message Data Cleaning

**User Story:** As a User, I want messages from different Platforms to be normalized into a consistent format, so that I can search and analyze them uniformly.

#### Acceptance Criteria

1. WHEN a message is collected from any Platform, THE Backend System SHALL transform it into a unified message schema
2. THE Backend System SHALL extract sender information, timestamp, content, and attachments from each message
3. THE Backend System SHALL preserve Platform-specific metadata in a structured format
4. WHEN a message contains attachments, THE Backend System SHALL store references to those attachments
5. THE Backend System SHALL validate that all cleaned messages conform to the unified schema

### Requirement 4: Contact Matching

**User Story:** As a User, I want Message Threads to be matched with Contacts, so that I can query conversations by person (e.g., "what did Iren and I talk about").

#### Acceptance Criteria

1. WHEN messages are cleaned, THE Backend System SHALL identify unique Contacts across all Platforms
2. THE Backend System SHALL match Message Threads to the corresponding Contact
3. WHEN the same Contact appears on multiple Platforms, THE Backend System SHALL merge them into a single Contact entity
4. THE Backend System SHALL allow Users to manually merge or split Contacts
5. WHEN a User queries by Contact name, THE Backend System SHALL return all Message Threads associated with that Contact

### Requirement 5: AI Ingestion and Summarization

**User Story:** As a User, I want the Backend System to analyze my messages using AI, so that I can get insights and summaries of my conversations.

#### Acceptance Criteria

1. WHEN messages are matched to Contacts, THE Backend System SHALL process them through an AI pipeline
2. THE Backend System SHALL generate embeddings for semantic search capabilities
3. THE Backend System SHALL extract entities (people, places, dates, topics) from messages
4. WHEN a User requests a summary of a Message Thread, THE Backend System SHALL generate a concise summary using AI
5. THE Backend System SHALL use local-first AI models with optional cloud fallbacks

### Requirement 6: Stage Independence and Testing

**User Story:** As a developer, I want each of the four stages to be independently testable, so that I can verify functionality at each step.

#### Acceptance Criteria

1. THE Backend System SHALL implement each stage (connection, collection, cleaning, matching, AI) as a separate module
2. WHEN testing a stage, THE Backend System SHALL allow mock data to be injected from the previous stage
3. THE Backend System SHALL provide health check endpoints for each stage
4. THE Backend System SHALL log stage transitions and errors for debugging
5. WHEN a stage fails, THE Backend System SHALL not block subsequent stages from processing other data

### Requirement 7: System Architecture

**User Story:** As a developer, I want a clean, maintainable architecture, so that the Backend System is easy to understand and extend.

#### Acceptance Criteria

1. THE Backend System SHALL use FastAPI for the REST API layer
2. THE Backend System SHALL use PostgreSQL for persistent data storage
3. THE Backend System SHALL use Redis for event streaming between stages
4. THE Backend System SHALL implement each Platform connector as a separate module
5. THE Backend System SHALL provide comprehensive API documentation via OpenAPI

### Requirement 8: Search and Query Interface

**User Story:** As a User, I want to search across all my messages and conversations, so that I can find information quickly.

#### Acceptance Criteria

1. WHEN a User submits a search query, THE Backend System SHALL return relevant messages across all Platforms
2. THE Backend System SHALL support full-text search on message content
3. THE Backend System SHALL support semantic search using AI embeddings
4. THE Backend System SHALL allow filtering by Contact, Platform, date range, and Message Thread
5. WHEN a User asks a natural language question, THE Backend System SHALL return contextually relevant results

### Requirement 9: Real-time Updates

**User Story:** As a User, I want to receive new messages in real-time, so that my aggregated view stays current.

#### Acceptance Criteria

1. WHEN a new message arrives on any connected Platform, THE Backend System SHALL process it within 30 seconds
2. THE Backend System SHALL support webhook notifications from Platforms that provide them
3. WHERE webhooks are not available, THE Backend System SHALL poll the Platform at configurable intervals
4. THE Backend System SHALL notify connected clients of new messages via WebSocket
5. WHEN the Backend System is offline, THE Backend System SHALL catch up on missed messages upon restart

### Requirement 10: Privacy and Security

**User Story:** As a User, I want my messages and credentials to be secure, so that my private communications remain protected.

#### Acceptance Criteria

1. THE Backend System SHALL encrypt all authentication credentials at rest
2. THE Backend System SHALL use HTTPS for all external API communications
3. THE Backend System SHALL implement PII detection and optional redaction
4. THE Backend System SHALL support multi-tenant isolation if multiple Users are configured
5. WHEN a User deletes data, THE Backend System SHALL permanently remove it from all storage

### Requirement 11: Analytics and Insights

**User Story:** As a User, I want insights about my communication patterns, so that I can understand my relationships better.

#### Acceptance Criteria

1. THE Backend System SHALL track message frequency per Contact over time
2. THE Backend System SHALL identify trending topics in conversations
3. THE Backend System SHALL detect sentiment in messages
4. WHEN a User requests relationship insights, THE Backend System SHALL provide a summary of communication patterns with a Contact
5. THE Backend System SHALL generate periodic summaries of communication activity

### Requirement 12: Deployment and Operations

**User Story:** As a developer, I want the Backend System to be easy to run and deploy, so that I can test and iterate quickly.

#### Acceptance Criteria

1. THE Backend System SHALL provide a Docker Compose configuration for local development
2. THE Backend System SHALL include environment variable configuration for all settings
3. THE Backend System SHALL provide database migration scripts
4. THE Backend System SHALL start successfully with minimal configuration
5. THE Backend System SHALL provide clear error messages when configuration is missing or invalid

### Requirement 13: Monitoring and Observability

**User Story:** As a developer, I want to monitor the Backend System's health and performance, so that I can identify and fix issues quickly.

#### Acceptance Criteria

1. THE Backend System SHALL expose health check endpoints for each stage
2. THE Backend System SHALL log all errors with sufficient context for debugging
3. THE Backend System SHALL track metrics for message processing throughput
4. THE Backend System SHALL alert when Platform connections fail
5. THE Backend System SHALL provide a status dashboard showing the state of all connected Platforms
