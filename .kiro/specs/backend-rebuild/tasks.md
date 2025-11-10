# Implementation Plan

## Stage 1: Project Foundation and Core Infrastructure

- [x] 1. Set up project structure and configuration
  - Create directory structure following the architecture (api/, db/, services/, integrations/)
  - Set up virtual environment and requirements.txt with core dependencies
  - Create .env.example with all required configuration variables
  - Set up Docker Compose with PostgreSQL, Redis, Ollama, and ChromaDB services
  - _Requirements: 7.1, 7.2, 7.3, 12.1, 12.2_

- [x] 2. Implement database foundation
- [x] 2.1 Set up SQLAlchemy base and session management
  - Create db/base.py with UUID primary key base model
  - Implement async session management in db/session.py
  - Configure Alembic for migrations
  - _Requirements: 7.2_

- [x] 2.2 Create core database models
  - Implement User model (db/models/user.py)
  - Implement PlatformConnection model with encrypted credentials
  - Implement RawMessage model for collection stage
  - Implement Message model with unified schema
  - _Requirements: 1.2, 2.1, 3.1_

- [x] 2.3 Create relationship models
  - Implement Contact model with platform identities
  - Implement Thread model with participant tracking
  - Implement Participant model for platform-specific identities
  - Implement Attachment model
  - _Requirements: 4.1, 4.2, 3.4_

- [x] 2.4 Create AI-related models
  - Implement Entity model for extracted entities
  - Implement Summary model for AI-generated summaries
  - Implement Embedding model with vector support
  - _Requirements: 5.2, 5.3, 5.4_

- [ ]* 2.5 Create initial database migration
  - Generate Alembic migration for all models
  - Test migration up and down
  - _Requirements: 12.3_

- [ ] 3. Set up event bus infrastructure
- [ ] 3.1 Implement Redis client and event bus
  - Create db/redis_client.py with connection management
  - Implement services/event_bus.py with Redis Streams
  - Create event type definitions in services/events/types.py
  - Implement producer and consumer patterns
  - _Requirements: 7.3, 6.1_

- [ ] 3.2 Create event handlers framework
  - Implement base event handler class
  - Create event routing and dispatch logic
  - Add consumer group management
  - Implement dead letter queue for failed events
  - _Requirements: 6.5_

- [ ] 4. Create FastAPI application foundation
  - Set up main.py with FastAPI app and lifespan management
  - Create api/dependencies.py for dependency injection
  - Implement health check endpoints (api/routes/health.py)
  - Set up CORS and middleware
  - Configure OpenAPI documentation
  - _Requirements: 7.1, 7.5, 6.3, 13.1_

## Stage 2: Connection Stage Implementation

- [ ] 5. Implement base connector framework
- [ ] 5.1 Create abstract base connector
  - Implement integrations/base_connector.py with health checks
  - Define connector interface (connect, disconnect, refresh_token)
  - Add rate limiting support
  - Implement circuit breaker pattern
  - _Requirements: 1.1, 2.3, 6.1_

- [ ] 5.2 Implement credential management
  - Create integrations/token_manager.py for OAuth token storage
  - Implement encryption for credentials at rest
  - Add automatic token refresh logic
  - _Requirements: 1.2, 1.3, 10.1_

- [ ] 6. Implement platform connectors
- [ ] 6.1 Gmail connector
  - Implement integrations/gmail_connector.py with OAuth 2.0
  - Create Gmail API client wrapper
  - Add webhook registration for push notifications
  - Implement token refresh
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 6.2 Slack connector
  - Implement integrations/slack_connector.py with OAuth 2.0
  - Create Slack API client wrapper
  - Add webhook support for real-time events
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 6.3 Discord connector
  - Implement integrations/discord_connector.py with OAuth 2.0
  - Create Discord API client wrapper
  - Add gateway connection for real-time events
  - _Requirements: 1.1, 1.2, 1.3, 1.4_


- [ ] 6.4 WhatsApp connector
  - Implement integrations/whatsapp_connector.py with Mautrix bridge
  - Set up Matrix protocol client
  - Configure bridge connection and authentication
  - _Requirements: 1.1, 1.2, 1.4, 2.5_

- [ ] 6.5 Twitter connector
  - Implement integrations/twitter_connector.py with OAuth
  - Create Twitter API client wrapper
  - Add polling mechanism for new tweets
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 6.6 Telegram connector
  - Implement integrations/telegram_connector.py with Bot API or MTProto
  - Create Telegram client wrapper
  - Add real-time update handling
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 7. Create connection management API
  - Implement POST /api/v1/connections/initiate/{platform} endpoint
  - Implement GET /api/v1/connections/callback/{platform} for OAuth callbacks
  - Implement GET /api/v1/connections to list active connections
  - Implement DELETE /api/v1/connections/{connection_id} for disconnection
  - Implement GET /api/v1/connections/{connection_id}/health for status checks
  - Emit CONNECTION_ESTABLISHED, CONNECTION_FAILED, CONNECTION_REVOKED events
  - _Requirements: 1.1, 1.5, 6.3, 13.4_

## Stage 3: Collection Stage Implementation

- [ ] 8. Implement collection orchestration
- [ ] 8.1 Create collection manager
  - Implement services/collection_orchestrator.py
  - Create job scheduling and prioritization logic
  - Add collection job tracking in database
  - Implement progress monitoring
  - _Requirements: 2.1, 2.2, 6.1_

- [ ] 8.2 Implement rate limiting
  - Create integrations/rate_limiter.py with platform-specific limits
  - Add exponential backoff for retries
  - Implement request queuing
  - _Requirements: 2.3, 2.4_

- [ ] 9. Implement historical message fetching
- [ ] 9.1 Create historical fetcher
  - Implement services/historical_fetcher.py
  - Add pagination support for each platform
  - Implement checkpoint/resume functionality
  - Store raw messages in database
  - _Requirements: 2.1_

- [ ] 9.2 Platform-specific historical fetchers
  - Implement Gmail historical fetch with pagination
  - Implement Slack historical fetch with cursor-based pagination
  - Implement Discord historical fetch
  - Implement WhatsApp historical fetch via Mautrix
  - Implement Twitter historical fetch
  - Implement Telegram historical fetch
  - _Requirements: 2.1, 2.3_

- [ ] 10. Implement real-time message collection
- [ ] 10.1 Create webhook receiver
  - Implement POST /api/v1/collection/webhook/{platform} endpoint
  - Add webhook signature validation
  - Route webhook events to appropriate handlers
  - _Requirements: 2.2, 9.2_

- [ ] 10.2 Create polling mechanism
  - Implement services/realtime_listener.py for polling-based platforms
  - Add configurable polling intervals
  - Implement efficient change detection
  - _Requirements: 2.2, 9.3_

- [ ] 11. Create collection API endpoints
  - Implement POST /api/v1/collection/start/{connection_id}
  - Implement POST /api/v1/collection/stop/{connection_id}
  - Implement GET /api/v1/collection/status/{connection_id}
  - Implement GET /api/v1/collection/history/{connection_id}
  - Emit MESSAGE_COLLECTED, COLLECTION_COMPLETED, COLLECTION_ERROR events
  - _Requirements: 2.1, 2.2, 6.3_

## Stage 4: Cleaning Stage Implementation

- [ ] 12. Implement message normalization
- [ ] 12.1 Create unified message schema
  - Define Pydantic models in services/message/schema.py
  - Implement schema validation
  - Create serialization/deserialization utilities
  - _Requirements: 3.1, 3.5_

- [ ] 12.2 Create platform parsers
  - Implement services/message/normalizer.py base class
  - Create Gmail message parser
  - Create Slack message parser
  - Create Discord message parser
  - Create WhatsApp message parser
  - Create Twitter message parser
  - Create Telegram message parser
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 12.3 Implement content processor
  - Create services/message/content_processor.py
  - Add HTML to plain text conversion
  - Implement markdown parsing
  - Add content sanitization
  - _Requirements: 3.2_

- [ ] 13. Implement attachment handling
  - Create services/storage/blob_storage.py interface
  - Implement local file storage backend
  - Add attachment download logic
  - Store attachment metadata in database
  - _Requirements: 3.4_

- [ ] 14. Create cleaning API endpoints
  - Implement GET /api/v1/messages to list normalized messages
  - Implement GET /api/v1/messages/{message_id} for details
  - Implement GET /api/v1/messages/stats for statistics
  - Implement POST /api/v1/messages/reprocess/{message_id}
  - Emit MESSAGE_NORMALIZED, NORMALIZATION_FAILED events
  - _Requirements: 3.1, 6.3, 8.1_

## Stage 5: Matching Stage Implementation

- [ ] 15. Implement contact matching
- [ ] 15.1 Create contact matcher
  - Implement services/contact_matcher.py
  - Add email-based matching logic
  - Add phone-based matching logic
  - Implement name similarity matching with fuzzy logic
  - _Requirements: 4.1, 4.3_

- [ ] 15.2 Create identity resolver
  - Implement services/identity_resolver.py
  - Add cross-platform identity linking
  - Create confidence scoring for matches
  - _Requirements: 4.1, 4.3_

- [ ] 16. Implement thread grouping
  - Create services/thread_grouper.py
  - Group messages by platform thread ID
  - Associate threads with contacts
  - Track thread participants
  - _Requirements: 4.2_

- [ ] 17. Create matching API endpoints
  - Implement GET /api/v1/contacts to list all contacts
  - Implement GET /api/v1/contacts/{contact_id} for details
  - Implement GET /api/v1/contacts/{contact_id}/threads
  - Implement POST /api/v1/contacts/merge for manual merging
  - Implement POST /api/v1/contacts/split for splitting
  - Implement GET /api/v1/threads to list threads
  - Implement GET /api/v1/threads/{thread_id} for details
  - Implement GET /api/v1/threads/{thread_id}/messages
  - Emit CONTACT_MATCHED, CONTACT_CREATED, CONTACT_MERGED, THREAD_CREATED events
  - _Requirements: 4.4, 4.5, 8.4_

## Stage 6: AI Stage Implementation

- [ ] 18. Set up AI infrastructure
- [ ] 18.1 Configure Ollama integration
  - Create services/ai/providers.py for LLM provider abstraction
  - Implement Ollama client wrapper
  - Add model management (download, list, select)
  - Configure tinyllama as default model
  - _Requirements: 5.5_

- [ ] 18.2 Set up ChromaDB
  - Create services/vector_db/chroma_client.py
  - Implement collection management
  - Add persistence configuration
  - Create vector database initialization script
  - _Requirements: 5.2_

- [ ] 19. Implement embedding service
- [ ] 19.1 Create embedding generator
  - Implement services/ai/embeddings.py
  - Add nomic-embed-text model integration
  - Implement batch processing for efficiency
  - Store embeddings in ChromaDB and PostgreSQL
  - _Requirements: 5.2_

- [ ] 19.2 Create semantic search engine
  - Implement services/ai/semantic_search.py
  - Add vector similarity search
  - Implement result ranking and filtering
  - _Requirements: 8.3_

- [ ] 20. Implement entity extraction
  - Create services/ai/entity_extraction.py
  - Integrate spaCy for NER
  - Define custom entity types (PERSON, ORG, DATE, LOCATION, TOPIC)
  - Store extracted entities in database
  - _Requirements: 5.3_

- [ ] 21. Implement PII detection and redaction
  - Create services/ai/pii_redaction.py
  - Integrate Presidio analyzer
  - Configure confidence thresholds
  - Add optional redaction functionality
  - _Requirements: 10.3_

- [ ] 22. Implement summarization
- [ ] 22.1 Create summary generator
  - Implement services/ai/summary/agent.py
  - Create prompt templates for different summary types
  - Add thread context building
  - Generate summaries using Ollama
  - _Requirements: 5.4_

- [ ] 22.2 Create insight generator
  - Implement services/ai/insight_generator.py
  - Analyze communication patterns
  - Track message frequency per contact
  - Identify trending topics
  - Detect sentiment
  - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ] 23. Create AI API endpoints
  - Implement POST /api/v1/ai/search for semantic search
  - Implement POST /api/v1/ai/summarize/{thread_id}
  - Implement GET /api/v1/ai/entities/{message_id}
  - Implement POST /api/v1/ai/insights/{contact_id}
  - Implement GET /api/v1/ai/similar/{message_id}
  - Implement POST /api/v1/ai/ask for natural language queries
  - Emit EMBEDDING_GENERATED, ENTITIES_EXTRACTED, SUMMARY_GENERATED events
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 8.5, 8.8_

## Stage 7: Search and Query Interface

- [ ] 24. Implement search functionality
- [ ] 24.1 Create full-text search
  - Add PostgreSQL full-text search indexes
  - Implement search query parser
  - Create search API with filtering
  - _Requirements: 8.2_

- [ ] 24.2 Implement advanced filtering
  - Add filter by contact
  - Add filter by platform
  - Add filter by date range
  - Add filter by thread
  - _Requirements: 8.4_

- [ ] 24.3 Create natural language query handler
  - Implement query understanding with AI
  - Convert natural language to search parameters
  - Return contextually relevant results
  - _Requirements: 8.5_

## Stage 8: Real-time Updates and WebSocket

- [ ] 25. Implement real-time notification system
  - Add WebSocket support to FastAPI
  - Create connection manager for WebSocket clients
  - Implement event broadcasting to connected clients
  - Add subscription filtering by platform/contact
  - _Requirements: 9.1, 9.4_

- [ ] 26. Implement catch-up mechanism
  - Create startup sync service
  - Detect missed messages during downtime
  - Prioritize recent messages for processing
  - _Requirements: 9.5_

## Stage 9: Monitoring and Operations

- [ ] 27. Implement comprehensive logging
  - Set up structured JSON logging
  - Add correlation IDs for request tracing
  - Implement log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Log stage transitions
  - _Requirements: 6.4, 13.2_

- [ ] 28. Create monitoring endpoints
  - Implement GET /api/v1/health for overall system health
  - Implement GET /api/v1/health/{stage} for stage-specific health
  - Implement GET /api/v1/stats for system statistics
  - Add metrics for message processing throughput
  - Track platform connection status
  - _Requirements: 13.1, 13.3, 13.5_

- [ ] 29. Implement alerting
  - Create alert definitions for critical failures
  - Add platform connection failure alerts
  - Monitor high error rates
  - Track database and Redis availability
  - _Requirements: 13.4_

## Stage 10: Security and Privacy

- [ ] 30. Implement authentication and authorization
  - Add JWT-based API authentication
  - Implement role-based access control
  - Create user registration and login endpoints
  - Add multi-tenant isolation
  - _Requirements: 10.4_

- [ ] 31. Enhance data protection
  - Verify encryption at rest for credentials
  - Ensure TLS for all external communications
  - Implement audit logging for data access
  - Add data retention policy configuration
  - _Requirements: 10.1, 10.2, 10.5_

## Stage 11: Testing and Quality Assurance

- [ ]* 32. Create comprehensive test suite
- [ ]* 32.1 Unit tests for core components
  - Write tests for each connector
  - Test message normalizers with sample data
  - Test contact matching algorithms
  - Test AI processing components
  - _Requirements: 6.2_

- [ ]* 32.2 Integration tests
  - Test end-to-end pipeline with mock data
  - Test Redis Streams event flow
  - Test database transactions
  - Test API endpoints
  - _Requirements: 6.2_

- [ ]* 32.3 Platform-specific tests
  - Create test suite for Gmail integration
  - Create test suite for Slack integration
  - Create test suite for Discord integration
  - Create test suite for WhatsApp integration
  - Create test suite for Twitter integration
  - Create test suite for Telegram integration
  - _Requirements: 6.2_

## Stage 12: Documentation and Deployment

- [ ]* 33. Create comprehensive documentation
  - Write API documentation with examples
  - Create deployment guide
  - Document environment variables
  - Write platform setup guides
  - Create troubleshooting guide
  - _Requirements: 7.5, 12.2_

- [ ] 34. Finalize deployment configuration
  - Optimize Docker Compose for production
  - Create Kubernetes manifests (optional)
  - Set up CI/CD pipeline
  - Configure monitoring and logging infrastructure
  - _Requirements: 12.1, 12.4_

## Stage 13: Migration and Cleanup

- [ ] 35. Archive old backend
  - Create backup of old backend database
  - Move old code to archive directory
  - Document old system for reference
  - _Requirements: 12.5_

- [ ]* 36. Create data migration script (optional)
  - Write script to import data from old backend
  - Test migration with sample data
  - Document migration process
  - _Requirements: 12.5_

- [ ] 37. Final system validation
  - Run end-to-end tests with all platforms
  - Verify all stages are working independently
  - Test failure scenarios and recovery
  - Validate performance meets requirements
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
