# Syncline - Complete Contacts & Messaging Implementation Plan

## 🎯 Vision Summary

**Core Concept:** Syncline is a unified communication aggregator that unifies contacts across platforms and enables sending messages to all connected platforms from one interface.

### Key Features:
1. **Unified Contact Profiles** - One profile per person, aggregating all their platform identities
2. **Cross-Platform Messaging** - Send one message that goes to all allowed platforms
3. **Contact-Based Search** - Search by contact, not by conversation
4. **Platform Profile Pictures** - Pull from first connected platform
5. **Rich Contact Profiles** - Show phone, email, social handles, etc.
6. **Onboarding Integration** - Collect contacts, notifications permissions upfront

---

## 📋 Implementation Phases

### **Phase 1: Contact Management Foundation** ✅ PARTIALLY DONE

#### Files Already Created (from previous session):
- `apps/backend/api/routes/contact_sync.py` - Contact sync backend
- `apps/Syncline/src/services/contacts.ts` - Device contacts service
- `apps/Syncline/src/api/endpoints/contactSync.ts` - Contact sync API client

#### What's Missing:
- Integration into onboarding flow
- UI for contact matching/merging
- Profile picture fetching from platforms

---

### **Phase 2: Messages Tab Rework** 🔄 IN PROGRESS

#### Current State:
- `apps/Syncline/app/(tabs)/messages.tsx` - Basic message list

#### Needs Complete Rework:

**1. Contact-Based Conversations**
```
Current: List of individual messages
New: List of contacts with aggregated conversations
```

**2. UI Changes:**
- Show contact name (from device contacts)
- Show colored platform icons (Slack, Gmail, etc.)
- Pull profile picture from first connected platform
- Group all messages from same contact
- Show last message preview
- Unread count badge

**3. Search:**
- Search by contact name
- Filter by platform
- Quick access to pinned contacts

---

### **Phase 3: Contact Profile Screen** 📱 NEW

#### Location: `apps/Syncline/app/contact/[id].tsx`

**Purpose:** Detailed view of a single contact showing:

**Profile Header:**
- Profile picture (from Platform API)
- Contact name
- Job title / Company (from device contacts)

**Connected Platforms Section:**
```
Slack      @sarah.connor     [Message]
Gmail      sarah@company.com [Email]
WhatsApp   +1-555-0123       [Call]
```

**Contact Details (from device):**
- Phone number
- Email address
- Company
- Job title
- Birthday
- Notes

**Quick Actions:**
- Message (unified - goes to all platforms)
- Call
- Email
- View conversation history

**Platform-Specific Actions:**
- Message on Slack
- Email on Gmail
- Chat on WhatsApp

---

### **Phase 4: Unified Messaging ("General Chat")** ✉️ NEW

#### Concept:
Send ONE message that goes to ALL allowed  platforms for that contact.

**Implementation:**

**1. Backend Endpoint:** `POST /api/messages/send-unified`
```python
{
  "contact_id": "uuid",
  "message": "Hey, checking in on the Q4 designs",
  "platforms": ["slack", "gmail"],  # or "all"
  "attachments": []
}
```

**2. Platform Dispatch Logic:**
- Check which platforms are connected for this contact
- Format message appropriately for each platform:
  - Slack → Direct message
  - Gmail → Email (with subject line)
  - WhatsApp → Chat message
  - Twitter → DM
- Send to each platform's API
- Track delivery status
- Return unified status

**3. UI Components:**
- Chat composer with platform selector
- "Send to All" toggle
- Individual platform toggles
- Attachment support
- Read receipts (aggregated across platforms)

---

### **Phase 5: Profile Picture Integration** 🖼️

#### Sources (Priority Order):
1. **Platform APIs** (Preferred)
   - Slack: `users.profile.get`
   - Gmail: Google Contacts API
   - WhatsApp: Profile photo API
   - LinkedIn: Profile API

2. **Device Contacts** (Fallback)
   - iOS/Android contact photos

3. **Initials Avatar** (Last resort)
   - Generated from name

#### Implementation:

**Backend:** `GET /api/contacts/{id}/profile-picture`
```python
def get_contact_profile_picture(contact_id):
    # 1. Check cache
    # 2. Try first connected platform
    # 3. Try other platforms
    # 4. Try device contacts
    # 5. Return initials avatar
    pass
```

**Frontend:** Cache in AsyncStorage, refresh periodically

---

### **Phase 6: Onboarding Flow** 🚀

#### Screen Flow:

**1. Welcome Screen**
- App intro
- Value proposition

**2. Permissions Screen** (`app/(auth)/onboarding-permissions.tsx`)
- ✅ Already exists!
- Requests:
  - Contacts access
  - Notifications
  - Camera (for profile picture)

**3. Contact Sync Screen** (NEW)
- "Syncing your contacts..."
- Progress bar
- Shows count: "Found 247 contacts"

**4. Platform Connection Screen**
- "Connect your accounts"
- List of platforms with Connect buttons
- Skip option (must connect at least 1)

**5. Contact Matching Screen** (NEW)
- AI-powered matching
- Show suggested matches:
```
John Doe
  📧 john.doe@gmail.com → Gmail
  💬 @johndoe → Slack
  📱 +1-555-0123 → WhatsApp
  [Confirm] [Edit]
```

**6. Review & Start**
- Summary of connected accounts
- Number of unified contacts
- "Start using Syncline"

---

### **Phase 7: Text-to-Speech Integration** 🔊

#### Already Partially Implemented:
- Frontend TTS removed (user reverted changes)

#### Backend Implementation Needed:

**1. Backend Route:** `apps/backend/api/routes/tts.py`
```python
@router.post("/generate")
async def generate_speech(request: TTSRequest):
    # Use OpenAI TTS API
    # Cache audio files
    # Return audio URL
    pass
```

**2. Frontend Integration:**
```typescript
// In BriefingModal
const handlePlayAudio = async () => {
    const audio = await ttsAPI.generateSpeech({
        text: summary,
        voice: 'nova'
    });
    // Play audio
};
```

**3. Features:**
- Play/pause button
- Speed control
- Voice selection
- Download option

---

## 🗂️ File Structure

```
apps/
├── backend/
│   └── api/
│       └── routes/
│           ├── contact_sync.py        ✅ EXISTS
│           ├── messages.py            🆕 CREATE - Unified messaging
│           ├── tts.py                 🆕 CREATE - Text-to-speech
│           └── profile_pictures.py    🆕 CREATE - Profile pic fetching
│
├── Syncline/
    ├── app/
    │   ├── (auth)/
    │   │   ├── onboarding-permissions.tsx    ✅ EXISTS
    │   │   ├── onboarding-contacts.tsx       🆕 CREATE
    │   │   └── onboarding-matching.tsx        🆕 CREATE
    │   ├── (tabs)/
    │   │   └── messages.tsx                   🔄 REWORK
    │   └── contact/
    │       └── [id].tsx                       🆕 CREATE
    │
    ├── components/
    │   ├── Messages/
    │   │   ├── ContactCard.tsx               🆕 CREATE
    │   │   ├── ConversationView.tsx          🆕 CREATE
    │   │   └── UnifiedComposer.tsx           🆕 CREATE
    │   └── Contacts/
    │       ├── ProfilePicture.tsx            🆕 CREATE
    │       └── PlatformBadges.tsx            🆕 CREATE
    │
    └── src/
        ├── api/endpoints/
        │   ├── contactSync.ts                ✅ EXISTS
        │   ├── messages.ts                   🔄 UPDATE
        │   ├── tts.ts                        🆕 CREATE
        │   └── profilePictures.ts            🆕 CREATE
        │
        └── services/
            ├── contacts.ts                   ✅ EXISTS
            └── platformAPIs.ts               🆕 CREATE - Platform integrations
```

---

## 🎨 UI/UX Specifications

### Messages Tab Redesign:

```
┌─────────────────────────────────┐
│  Messages          [Search] [+]  │
├─────────────────────────────────┤
│                                  │
│  [👤] Sarah Connor           10m │
│      Product Manager             │
│      Hey, checking on designs... │
│      [💬][📧][💼]             •3  │
│                                  │
│  [👤] Mike Ross              1hr │
│      Finance                     │
│      Attached is the Q4 budget...│
│      [📧]                         │
│                                  │
│  [👤] Jessica Pearson     Yesterday│
│      Director                    │
│      Great work on the pres...   │
│      [💬][📧][💼]                 │
│                                  │
└─────────────────────────────────┘
```

**Legend:**
- 👤 = Profile picture (from platform)
- 💬 = Slack icon (colored)
- 📧 = Gmail icon (colored)
- 💼 = LinkedIn icon (colored)
- •3 = Unread count

### Contact Profile:

```
┌─────────────────────────────────┐
│         [< Back]     [...More]   │
│                                  │
│           [👤 Large PFP]         │
│           Sarah Connor           │
│          Product Manager         │
│                                  │
│  ┌─────────────────────────────┐│
│  │  Connected Platforms         ││
│  ├─────────────────────────────┤│
│  │ [💬] Slack                   ││
│  │     @sarah.connor   [Message]││
│  │                              ││
│  │ [📧] Gmail                   ││
│  │     sarah@company.com [Email]││
│  │                              ││
│  │ [💼] LinkedIn                ││
│  │     in/sarahconnor  [View]   ││
│  └─────────────────────────────┘│
│                                  │
│  ┌─────────────────────────────┐│
│  │  Contact Information         ││
│  ├─────────────────────────────┤│
│  │ Phone: +1-555-0123           ││
│  │ Email: sarah@company.com     ││
│  │ Company: Acme Corp           ││
│  └─────────────────────────────┘│
│                                  │
│  [📤 Send General Message]       │
│  [📞 Call] [📧 Email] [💬 Chat]  │
└─────────────────────────────────┘
```

---

## 🔧 Technical Implementation Details

### Contact Matching Algorithm:

```python
def match_contact_to_platforms(device_contact):
    """
    Match device contact to platform identities
    """
    matches = []
    
    # 1. Email matching
    if device_contact.email:
        gmail_match = find_gmail_contact(device_contact.email)
        if gmail_match:
            matches.append({
                'platform': 'gmail',
                'identity': gmail_match,
                'confidence': 1.0
            })
    
    # 2. Phone matching
    if device_contact.phone:
        whatsapp_match = find_whatsapp_contact(device_contact.phone)
        if whatsapp_match:
            matches.append({
                'platform': 'whatsapp',
                'identity': whatsapp_match,
                'confidence': 0.9
            })
    
    # 3. Name fuzzy matching
    slack_matches = find_slack_users_by_name(device_contact.name)
    for match in slack_matches:
        confidence = calculate_name_similarity(
            device_contact.name, 
            match.display_name
        )
        if confidence > 0.7:
            matches.append({
                'platform': 'slack',
                'identity': match,
                'confidence': confidence
            })
    
    return matches
```

### Unified Message Dispatch:

```python
async def send_unified_message(contact_id, message, platforms='all'):
    """
    Send message to multiple platforms
    """
    contact = get_contact(contact_id)
    results = []
    
    if platforms == 'all':
        platforms = contact.connected_platforms
    
    for platform in platforms:
        if platform == 'slack':
            result = await send_slack_message(
                contact.slack_id,
                message
            )
        elif platform == 'gmail':
            result = await send_gmail(
                contact.email,
                subject="Message from Syncline",
                body=message
            )
        elif platform == 'whatsapp':
            result = await send_whatsapp_message(
                contact.phone,
                message
            )
        
        results.append({
            'platform': platform,
            'status': result.status,
            'message_id': result.id
        })
    
    return results
```

---

## 📊 Implementation Priority

### **Immediate (Week 1-2):**
1. ✅ Complete Dark Mode (Part C)
2. 🔄 Rework Messages Tab UI
3. 🆕 Create Contact Profile Screen
4. 🆕 Implement colored platform icons

### **Short-term (Week 3-4):**
5. 🆕 Build unified messaging backend
6. 🆕 Create unified composer UI
7. 🆕 Implement profile picture fetching
8. 🔄 Update onboarding flow

### **Medium-term (Month 2):**
9. 🆕 Advanced contact matching
10. 🆕 Text-to-speech backend
11. 🆕 Platform-specific features
12. 🆕 Analytics & insights

---

## ✅ Next Steps

1. **Complete Dark Mode** ✓
2. **Create detailed spec for Messages rework**
3. **Build Contact Profile screen**
4. **Implement platform icon colors**
5. **Start on unified messaging**

Would you like me to proceed with any specific phase?
