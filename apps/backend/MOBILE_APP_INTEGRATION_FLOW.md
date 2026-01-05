# Mobile App Integration Flow

## Overview

The WhatsApp integration now has auto-sync functionality and proper session management. Here's the complete flow for your mobile app.

## 🚀 Complete Integration Flow

### 1. Initial Setup
```http
POST /api/whatsapp/{connection_id}/session/create
Authorization: Bearer {token}
```

**Response:**
```json
{
  "connection_id": "uuid",
  "is_logged_in": false,
  "phone_number": null,
  "session_age_seconds": null
}
```

### 2. Get QR Code for Login
```http
GET /api/whatsapp/{connection_id}/login
Authorization: Bearer {token}
```

**Response (if not logged in):**
```json
{
  "connection_id": "uuid",
  "qr_code": "2@ABC123...",
  "already_logged_in": false,
  "message": "Scan QR code with WhatsApp mobile app"
}
```

**Response (if already logged in):**
```json
{
  "connection_id": "uuid",
  "qr_code": null,
  "already_logged_in": true,
  "phone": "+1234567890",
  "message": "Already logged in to WhatsApp",
  "auto_sync": {
    "success": true,
    "rooms_found": 15,
    "message": "Auto-synced 15 WhatsApp chats"
  }
}
```

### 3. Poll for Login Completion (NEW!)
```http
GET /api/whatsapp/{connection_id}/login/status
Authorization: Bearer {token}
```

**Response (waiting for scan):**
```json
{
  "success": true,
  "login_completed": false,
  "phone": null,
  "message": "Waiting for QR scan..."
}
```

**Response (login successful with auto-sync):**
```json
{
  "success": true,
  "login_completed": true,
  "phone": "+1234567890",
  "auto_sync": {
    "success": true,
    "rooms_found": 15,
    "sync_details": {...},
    "message": "Auto-synced 15 WhatsApp chats"
  },
  "message": "Login successful! Chats are being synced."
}
```

### 4. Manual Sync (if needed)
```http
POST /api/whatsapp/{connection_id}/sync-after-login
Authorization: Bearer {token}
```

**Response:**
```json
{
  "success": true,
  "sync_result": {
    "success": true,
    "rooms_found": 15,
    "message": "Auto-synced 15 WhatsApp chats"
  },
  "messages_available": 50,
  "message": "Sync completed. 50 messages available."
}
```

### 5. Collect Messages
```http
POST /api/whatsapp/{connection_id}/collect?limit=100
Authorization: Bearer {token}
```

**Response:**
```json
{
  "messages_collected": 50,
  "contacts_created": 5,
  "errors": 0,
  "message": "Successfully collected 50 messages"
}
```

### 6. Get Chat Threads
```http
GET /api/chats?platform=whatsapp
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "id": "whatsapp_room_id",
    "platform": "whatsapp",
    "contact_name": "John Doe",
    "phone_number": "+1234567890",
    "last_message": "Hey, how are you?",
    "last_message_time": "2025-12-21T00:30:00Z",
    "unread_count": 2
  }
]
```

## 📱 Mobile App Implementation

### Login Flow
```typescript
class WhatsAppService {
  async loginWithQR(connectionId: string): Promise<LoginResult> {
    // 1. Create session
    await this.createSession(connectionId);
    
    // 2. Get QR code
    const qrResult = await this.getQRCode(connectionId);
    
    if (qrResult.already_logged_in) {
      // Already logged in, chats auto-synced
      return { success: true, autoSynced: true };
    }
    
    // 3. Show QR code to user
    this.showQRCode(qrResult.qr_code);
    
    // 4. Poll for completion
    return this.pollForLogin(connectionId);
  }
  
  async pollForLogin(connectionId: string): Promise<LoginResult> {
    const maxAttempts = 60; // 5 minutes
    
    for (let i = 0; i < maxAttempts; i++) {
      const status = await this.checkLoginStatus(connectionId);
      
      if (status.login_completed) {
        // Login successful! Auto-sync triggered
        return {
          success: true,
          phone: status.phone,
          autoSynced: status.auto_sync?.success || false,
          roomsFound: status.auto_sync?.rooms_found || 0
        };
      }
      
      // Wait 5 seconds before next check
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
    
    throw new Error('Login timeout');
  }
  
  async syncChatsAfterLogin(connectionId: string) {
    // Manual sync if auto-sync didn't work
    const result = await this.syncChatsManually(connectionId);
    
    if (result.success) {
      // Collect messages
      await this.collectMessages(connectionId);
      
      // Refresh chat list
      await this.refreshChats();
    }
  }
}
```

### Auto-Sync Benefits
1. **Immediate Chat Availability**: Chats are synced as soon as login completes
2. **No Manual Steps**: User doesn't need to trigger sync manually
3. **Real-time Feedback**: Mobile app knows exactly when sync completes
4. **Error Handling**: Fallback to manual sync if auto-sync fails

## 🔄 Auto-Sync Features

### When Auto-Sync Triggers
- ✅ When QR login detects existing login
- ✅ When QR scan completes successfully  
- ✅ When phone login completes
- ✅ When polling detects login completion

### What Auto-Sync Does
1. **Comprehensive Sync**: Runs `sync_all_chats()` with multiple strategies
2. **Contact Sync**: Syncs contacts with avatars
3. **Group Sync**: Syncs group chats
4. **App State Sync**: Syncs WhatsApp app state
5. **Room Discovery**: Finds all available chat rooms
6. **Message Backfill**: Triggers message history sync

### Auto-Sync Response
```json
{
  "success": true,
  "rooms_found": 15,
  "sync_details": {
    "contacts": "Synced 10 contacts",
    "groups": "Synced 3 groups", 
    "appstate": "App state synced",
    "rooms_found": 15
  },
  "message": "Auto-synced 15 WhatsApp chats"
}
```

## 🎯 Recommended Mobile Flow

1. **App Launch**: Check if session exists and is logged in
2. **Login Screen**: Show QR code and start polling
3. **Login Success**: Show "Syncing chats..." with progress
4. **Chat List**: Display synced chats immediately
5. **Background Sync**: Continue collecting messages in background

## 🔧 Error Handling

### Login Failures
- **QR Timeout**: Show "Please try again" and generate new QR
- **Bridge Offline**: Show "Service unavailable, please try later"
- **Session Expired**: Automatically cleanup and restart

### Sync Failures  
- **Auto-sync Failed**: Fallback to manual sync
- **No Chats Found**: Show "No chats available" with refresh option
- **Partial Sync**: Show available chats, continue syncing in background

The system is now ready for your mobile app! The auto-sync ensures chats are immediately available after login, providing a smooth user experience. 🚀