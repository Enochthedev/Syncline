# 🤖 AI Features Guide: Summaries, Insights & Intelligence

**How Syncline's AI features work and how to use them in your mobile app**

---

## 📊 Overview: AI Feature Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          AI Processing Pipeline                       │
└─────────────────────────────────────────────────────────────────────┘
         │
         ├─── 1. EMBEDDINGS ──────────────────────────────────────┐
         │    • Convert messages to vector embeddings              │
         │    • Store in ChromaDB for semantic search              │
         │    • Model: nomic-embed-text (local, no API key)        │
         │    • Endpoint: Automatic during ingestion               │
         │                                                          │
         ├─── 2. ENTITY EXTRACTION ───────────────────────────────┤
         │    • Extract people, dates, locations, organizations    │
         │    • Uses spaCy NER (Named Entity Recognition)          │
         │    • Endpoint: GET /api/v1/ai/entities/{message_id}     │
         │                                                          │
         ├─── 3. THREAD SUMMARIZATION ────────────────────────────┤
         │    • Generate conversation summaries                    │
         │    • Multiple summary types (brief, detailed, bullet)   │
         │    • Uses local LLM (Ollama) - no API cost              │
         │    • Endpoint: POST /api/v1/ai/summarize/{thread_id}    │
         │                                                          │
         ├─── 4. SEMANTIC SEARCH ─────────────────────────────────┤
         │    • Find messages by meaning, not just keywords        │
         │    • Vector similarity search                           │
         │    • Endpoint: POST /api/v1/ai/search                   │
         │                                                          │
         ├─── 5. CONTACT INSIGHTS ────────────────────────────────┤
         │    • Analyze communication patterns                     │
         │    • Trending topics, sentiment, frequency              │
         │    • Endpoint: POST /api/v1/ai/insights/{contact_id}    │
         │                                                          │
         └─── 6. NATURAL LANGUAGE QUERIES ────────────────────────┘
              • Ask questions in plain English
              • AI-powered answers with sources
              • Endpoint: POST /api/v1/ai/ask
```

---

## 🎯 Feature 1: Thread Summarization

### **What it does:**
Analyzes an entire conversation thread (across all platforms) and generates a concise summary using AI.

### **How it works:**

```
Thread Messages → LLM Context Builder → Ollama (llama3.2) → Summary
   (50 msgs)         (format messages)      (process)         (3-5 sentences)
```

### **API Endpoint:**

```typescript
POST /api/v1/ai/summarize/{thread_id}

// Request Body
{
  "summary_type": "brief" | "detailed" | "bullet_points",
  "force_regenerate": false  // Use cached summary if exists
}

// Response
{
  "thread_id": "uuid",
  "summary_type": "brief",
  "content": "Alice and Bob discussed the Q4 budget proposal. Bob raised concerns about increased marketing spend. They agreed to review the proposal again next week with updated numbers. Follow-up meeting scheduled for Friday at 2pm.",
  "metadata": {
    "message_count": 47,
    "participants": ["Alice", "Bob"],
    "date_range": "2025-11-20 to 2025-11-28",
    "key_topics": ["budget", "marketing", "Q4", "meeting"]
  },
  "generated_at": "2025-11-28T15:30:00Z"
}
```

### **Mobile App Usage:**

```typescript
// src/api/endpoints/ai.ts
export const aiAPI = {
  summarizeThread: async (
    threadId: string,
    type: 'brief' | 'detailed' | 'bullet_points' = 'brief'
  ) => {
    const { data } = await apiClient.post(
      `/ai/summarize/${threadId}`,
      { 
        summary_type: type,
        force_regenerate: false 
      }
    );
    return data;
  },
};

// src/screens/ThreadScreen.tsx
const ThreadScreen = ({ threadId }) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadSummary = async () => {
    setLoading(true);
    try {
      const data = await aiAPI.summarizeThread(threadId, 'brief');
      setSummary(data.content);
    } catch (error) {
      console.error('Failed to load summary:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View>
      <TouchableOpacity onPress={loadSummary}>
        <Text>📝 Generate Summary</Text>
      </TouchableOpacity>
      
      {loading && <ActivityIndicator />}
      
      {summary && (
        <View style={styles.summaryCard}>
          <Text style={styles.summaryTitle}>AI Summary</Text>
          <Text style={styles.summaryText}>{summary}</Text>
        </View>
      )}
    </View>
  );
};
```

### **Summary Types:**

| Type | Description | Use Case |
|------|-------------|----------|
| `brief` | 3-5 sentence overview | Quick glance at long threads |
| `detailed` | Paragraph with key points | Full context understanding |
| `bullet_points` | List of main topics | Action items, decisions |

### **When summaries are generated:**
- ✅ On-demand via API call
- ✅ Automatically for threads with >20 messages (background job)
- ✅ Cached for performance (regenerate with `force_regenerate: true`)

---

## 🔍 Feature 2: Semantic Search

### **What it does:**
Find messages by meaning, not just exact keywords. "Find discussions about budget" will match "Q4 financial planning" even without the word "budget".

### **How it works:**

```
User Query → Generate Embedding → Search ChromaDB → Rank Results → Return Messages
"budget"      [0.23, 0.45, ...]    (vector search)   (by similarity)   (top 10)
```

### **API Endpoint:**

```typescript
POST /api/v1/ai/search

// Request
{
  "query": "discussions about product launch delays",
  "platforms": ["slack", "gmail"],  // Optional filter
  "thread_ids": null,               // Optional filter
  "start_date": "2025-11-01",       // Optional filter
  "end_date": "2025-11-30",         // Optional filter
  "min_score": 0.7,                 // Similarity threshold (0-1)
  "limit": 10
}

// Response
{
  "query": "discussions about product launch delays",
  "results": [
    {
      "message_id": "uuid",
      "platform": "slack",
      "content": "We need to push the product launch to Q1...",
      "similarity_score": 0.89,
      "sender": "Alice",
      "timestamp": "2025-11-25T14:30:00Z",
      "thread_id": "uuid"
    },
    // ... more results
  ],
  "total": 15
}
```

### **Mobile App Usage:**

```typescript
// src/screens/SearchScreen.tsx
const SearchScreen = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searchType, setSearchType] = useState<'keyword' | 'semantic'>('semantic');

  const handleSearch = async () => {
    if (searchType === 'semantic') {
      // Semantic search - finds meaning
      const data = await apiClient.post('/ai/search', {
        query,
        limit: 20,
        min_score: 0.6
      });
      setResults(data.results);
    } else {
      // Keyword search - exact matches
      const data = await apiClient.get('/messages/search', {
        params: { query }
      });
      setResults(data.results);
    }
  };

  return (
    <View>
      <TextInput
        placeholder="Search your messages..."
        value={query}
        onChangeText={setQuery}
      />
      
      <View style={styles.toggles}>
        <TouchableOpacity onPress={() => setSearchType('keyword')}>
          <Text>🔤 Keyword</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => setSearchType('semantic')}>
          <Text>🤖 AI Semantic</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={results}
        renderItem={({ item }) => (
          <MessageCard
            message={item}
            highlightScore={item.similarity_score} // Show relevance
          />
        )}
      />
    </View>
  );
};
```

### **Example Semantic Queries:**

| Query | Matches (even without keywords) |
|-------|--------------------------------|
| "urgent issues" | "critical bug", "emergency", "ASAP", "blocker" |
| "meeting schedule" | "calendar invite", "let's sync", "availability" |
| "positive feedback" | "great job", "excellent work", "well done" |
| "budget concerns" | "cost overrun", "financial issues", "spending" |

---

## 👥 Feature 3: Contact Insights

### **What it does:**
Analyzes your communication patterns with a specific person across all platforms and generates insights.

### **Insights Generated:**

1. **Communication Frequency**
   - Messages per day/week
   - Active hours
   - Response time analysis

2. **Trending Topics**
   - Most discussed subjects
   - Topic evolution over time

3. **Sentiment Analysis**
   - Positive/negative/neutral breakdown
   - Relationship health score

4. **Platform Usage**
   - Where you communicate most
   - Preferred channels

### **API Endpoint:**

```typescript
POST /api/v1/ai/insights/{contact_id}
?days=30  // Analyze last 30 days

// Response
{
  "contact_id": "uuid",
  "insights": [
    {
      "type": "frequency",
      "title": "High Communication Volume",
      "description": "You exchange ~25 messages/day with Alice, 40% above your average",
      "data": {
        "messages_per_day": 25,
        "avg_response_time_minutes": 15,
        "most_active_hours": [9, 14, 16]
      },
      "confidence": 0.95,
      "generated_at": "2025-11-28T15:30:00Z"
    },
    {
      "type": "topics",
      "title": "Trending Topics",
      "description": "Recent discussions focus on: Product Launch (45%), Budget (30%), Hiring (25%)",
      "data": {
        "topics": [
          { "name": "Product Launch", "percentage": 45, "trend": "up" },
          { "name": "Budget", "percentage": 30, "trend": "stable" },
          { "name": "Hiring", "percentage": 25, "trend": "down" }
        ]
      },
      "confidence": 0.87
    },
    {
      "type": "sentiment",
      "title": "Positive Communication",
      "description": "85% of messages have positive sentiment",
      "data": {
        "positive": 0.85,
        "neutral": 0.12,
        "negative": 0.03,
        "relationship_score": 8.5
      },
      "confidence": 0.78
    },
    {
      "type": "platforms",
      "title": "Platform Preferences",
      "description": "Primary communication via Slack (60%), followed by Email (40%)",
      "data": {
        "slack": 150,
        "gmail": 100
      },
      "confidence": 1.0
    }
  ],
  "total": 4
}
```

### **Mobile App Usage:**

```typescript
// src/screens/ContactInsightsScreen.tsx
const ContactInsightsScreen = ({ contactId, contactName }) => {
  const [insights, setInsights] = useState([]);

  useEffect(() => {
    loadInsights();
  }, [contactId]);

  const loadInsights = async () => {
    const { data } = await apiClient.post(
      `/ai/insights/${contactId}`,
      null,
      { params: { days: 30 } }
    );
    setInsights(data.insights);
  };

  return (
    <ScrollView>
      <Text style={styles.title}>
        Insights: {contactName}
      </Text>

      {insights.map((insight, idx) => (
        <InsightCard key={idx} insight={insight} />
      ))}
    </ScrollView>
  );
};

const InsightCard = ({ insight }) => (
  <View style={styles.card}>
    <View style={styles.header}>
      <Text style={styles.icon}>{getIconForType(insight.type)}</Text>
      <Text style={styles.title}>{insight.title}</Text>
      <Text style={styles.confidence}>
        {(insight.confidence * 100).toFixed(0)}% confidence
      </Text>
    </View>
    
    <Text style={styles.description}>{insight.description}</Text>

    {/* Render type-specific visualizations */}
    {insight.type === 'topics' && (
      <TopicChart data={insight.data.topics} />
    )}
    
    {insight.type === 'sentiment' && (
      <SentimentGauge score={insight.data.relationship_score} />
    )}
    
    {insight.type === 'frequency' && (
      <FrequencyGraph data={insight.data} />
    )}
  </View>
);

const getIconForType = (type: string) => {
  const icons = {
    frequency: '📊',
    topics: '🏷️',
    sentiment: '❤️',
    platforms: '💬'
  };
  return icons[type] || '📌';
};
```

---

## 🔎 Feature 4: Entity Extraction

### **What it does:**
Automatically extracts important information from messages: people, dates, locations, organizations, money, etc.

### **Entities Extracted:**

| Type | Examples | Use Case |
|------|----------|---------|
| `PERSON` | "Alice", "Bob Johnson" | Contact tracking |
| `ORG` | "Google", "Acme Corp" | Company mentions |
| `DATE` | "next Friday", "Dec 25" | Calendar events |
| `TIME` | "3pm", "tomorrow at 4" | Meeting times |
| `MONEY` | "$1000", "€500" | Budget discussions |
| `GPE` | "New York", "London" | Location tracking |
| `PRODUCT` | "iPhone 15", "ChatGPT" | Product discussions |

### **API Endpoint:**

```typescript
GET /api/v1/ai/entities/{message_id}
?entity_type=PERSON  // Optional filter

// Response
{
  "message_id": "uuid",
  "entities": [
    {
      "id": "uuid",
      "entity_type": "PERSON",
      "entity_text": "Alice Johnson",
      "confidence": 0.95,
      "metadata": {
        "start_char": 15,
        "end_char": 28,
        "context": "Meeting with Alice Johnson tomorrow"
      }
    },
    {
      "entity_type": "DATE",
      "entity_text": "tomorrow",
      "confidence": 0.92,
      "metadata": {
        "normalized_date": "2025-11-29",
        "relative": true
      }
    }
  ],
  "total": 2
}
```

### **Auto-extraction:**
- ✅ Runs automatically when messages are ingested
- ✅ Stored in database for fast retrieval
- ✅ Re-extract on demand if needed

---

## 💬 Feature 5: Natural Language Queries

### **What it does:**
Ask questions in plain English and get AI-powered answers based on your messages.

### **Example Queries:**

| Question | AI Response |
|----------|-------------|
| "What did Alice say about the budget?" | "Alice mentioned budget concerns in 3 messages. She's worried about Q4 marketing spend exceeding $50K and requested a review meeting..." |
| "When is my next meeting?" | "Based on your messages, you have a meeting scheduled for Friday at 2pm with Bob to discuss the Q4 budget proposal." |
| "What are the main blockers right now?" | "Current blockers mentioned: 1) API integration delayed by 2 weeks, 2) Design mockups pending review, 3) Budget approval needed..." |

### **API Endpoint:**

```typescript
POST /api/v1/ai/ask

// Request
{
  "question": "What did we decide about the product launch date?",
  "context": {
    "platforms": ["slack", "gmail"],
    "date_range": "last_7_days"
  },
  "limit": 5  // Max sources to consider
}

// Response
{
  "question": "What did we decide about the product launch date?",
  "answer": "Based on the conversation thread, the team decided to push the product launch from December 15th to January 10th. This decision was made due to integration delays and stakeholder feedback. Alice will send calendar invites for the new launch timeline.",
  "sources": [
    {
      "message_id": "uuid",
      "content": "Let's move launch to Jan 10...",
      "platform": "slack",
      "sender": "Bob",
      "timestamp": "2025-11-25T14:00:00Z",
      "similarity_score": 0.92
    },
    // ... more source messages
  ],
  "confidence": 0.88
}
```

### **Mobile App Usage:**

```typescript
// src/screens/AskAIScreen.tsx
const AskAIScreen = () => {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);

  const askQuestion = async () => {
    setLoading(true);
    try {
      const { data } = await apiClient.post('/ai/ask', {
        question,
        limit: 10
      });
      setAnswer(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View>
      <Text style={styles.title}>🤖 Ask AI About Your Messages</Text>
      
      <TextInput
        style={styles.input}
        placeholder="Ask a question..."
        value={question}
        onChangeText={setQuestion}
        multiline
      />

      <TouchableOpacity 
        style={styles.button}
        onPress={askQuestion}
        disabled={loading || !question}
      >
        <Text>Ask</Text>
      </TouchableOpacity>

      {loading && (
        <View style={styles.loading}>
          <ActivityIndicator />
          <Text>AI is thinking...</Text>
        </View>
      )}

      {answer && (
        <View style={styles.answerCard}>
          <Text style={styles.answerTitle}>Answer</Text>
          <Text style={styles.answerText}>{answer.answer}</Text>
          
          <Text style={styles.confidence}>
            Confidence: {(answer.confidence * 100).toFixed(0)}%
          </Text>

          <Text style={styles.sourcesTitle}>Sources ({answer.sources.length}):</Text>
          {answer.sources.map((source, idx) => (
            <TouchableOpacity
              key={idx}
              onPress={() => goToMessage(source.message_id)}
            >
              <View style={styles.sourceCard}>
                <Text style={styles.sourceText} numberOfLines={2}>
                  {source.content}
                </Text>
                <Text style={styles.sourceMeta}>
                  {source.sender} • {source.platform} • {formatDate(source.timestamp)}
                </Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>
      )}
    </View>
  );
};
```

---

## 🎨 Suggested Queries for Your App:

```typescript
const SUGGESTED_QUESTIONS = [
  "What are my urgent tasks?",
  "Summarize today's discussions",
  "What did [contact] say about [topic]?",
  "When is my next meeting?",
  "What are the current blockers?",
  "Who do I communicate with most?",
  "What topics am I discussing most lately?",
  "Find discussions about [project name]",
];

// Show as quick action buttons
<View style={styles.suggestions}>
  {SUGGESTED_QUESTIONS.map((q) => (
    <TouchableOpacity
      key={q}
      style={styles.suggestionChip}
      onPress={() => setQuestion(q)}
    >
      <Text>{q}</Text>
    </TouchableOpacity>
  ))}
</View>
```

---

## ⚡ Performance & Caching

All AI features implement smart caching:

| Feature | Cache Duration | Force Refresh |
|---------|---------------|---------------|
| Summaries | 24 hours | `force_regenerate: true` |
| Entities | Permanent | Re-extract endpoint |
| Insights | 1 hour | New request |
| Embeddings | Permanent | Auto on content change |

### **Cost Optimization:**

```typescript
// Check if summary exists before generating
const getSummaryOptimized = async (threadId: string) => {
  try {
    // Try cached version first
    const cached = await apiClient.post(`/ai/summarize/${threadId}`, {
      force_regenerate: false  // Use cache
    });
    return cached.data;
  } catch (error) {
    // Generate if doesn't exist
    const fresh = await apiClient.post(`/ai/summarize/${threadId}`, {
      force_regenerate: true  // Force new
    });
    return fresh.data;
  }
};
```

---

## 🚀 Getting Started Checklist

- [ ] Backend running with Ollama models downloaded
- [ ] Test AI endpoints with curl/Postman
- [ ] Implement AI API client in mobile app
- [ ] Create summary UI component
- [ ] Add semantic search to search screen
- [ ] Build insights screen for contacts
- [ ] Implement "Ask AI" feature
- [ ] Test with real data

---

## 🧪 Testing AI Features

```bash
# 1. Test summarization
curl -X POST http://localhost:8000/api/v1/ai/summarize/your-thread-id \
  -H "Content-Type: application/json" \
  -d '{"summary_type": "brief"}'

# 2. Test semantic search
curl -X POST http://localhost:8000/api/v1/ai/search \
  -H "Content-Type: application/json" \
  -d '{"query": "budget discussions", "limit": 5}'

# 3. Test entity extraction
curl http://localhost:8000/api/v1/ai/entities/your-message-id

# 4. Test insights
curl -X POST http://localhost:8000/api/v1/ai/insights/your-contact-id?days=30

# 5. Test natural language query
curl -X POST http://localhost:8000/api/v1/ai/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main topics discussed this week?"}'
```

---

## 💡 UI/UX Recommendations

### **1. Show AI Status:**
```typescript
<View style={styles.aiIndicator}>
  {isProcessing && <Text>🤖 AI is analyzing...</Text>}
  {hasSummary && <Text>✨ Summary available</Text>}
</View>
```

### **2. Confidence Badges:**
```typescript
const ConfidenceBadge = ({ score }) => {
  const color = score > 0.8 ? 'green' : score > 0.6 ? 'orange' : 'red';
  return (
    <View style={[styles.badge, { backgroundColor: color }]}>
      <Text>{(score * 100).toFixed(0)}%</Text>
    </View>
  );
};
```

### **3. Progressive Enhancement:**
Start with basic features, add AI gradually:
- Week 1: Basic message listing
- Week 2: Add keyword search
- Week 3: Add semantic search
- Week 4: Add summaries
- Week 5: Add insights & NL queries

---

**Ready to implement AI features?** Start with summaries (easiest) then move to semantic search!
