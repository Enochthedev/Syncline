# Mobile App Fixes Needed

## ✅ Completed
- Fixed API connectivity issue (hardcoded local IP for iOS: 192.168.1.137)
- Removed Screenshots button from home page
- App successfully loads and connects to backend

## 🔧 Issues to Fix

### 1. Phone Login Error (500)
**Error**: `Phone login error: [AxiosError: Request failed with status code 500]`
**Location**: WhatsApp phone authentication endpoint
**Impact**: Cannot authenticate WhatsApp via phone number
**Next Steps**: 
- Check backend logs for the actual error
- Verify WhatsApp connector phone login endpoint
- Test endpoint directly with curl

### 2. Daily Summary Error (500)
**Error**: `Failed to fetch daily summary: [AxiosError: Request failed with status code 500]`
**Location**: AI summary generation endpoint
**Impact**: Daily briefing on home page doesn't work
**Next Steps**:
- Check if AI service (Ollama) is running
- Verify summary endpoint exists and works
- Consider enabling MOCK_MODE for testing without AI

### 3. Nudges & Buttons Not Working
**Issue**: Nudges section and related buttons not functional
**Location**: Home page Quick Access section
**Next Steps**:
- Check if nudges endpoints exist
- Verify nudges page implementation
- Test nudges API calls

### 4. Commitments Not Working
**Issue**: Commitments section not functional
**Location**: Home page Quick Access section
**Next Steps**:
- Check if commitments endpoints exist
- Verify commitments page implementation
- Test commitments API calls

### 5. WhatsApp Chat Pulling
**Issue**: Unable to pull chats using WhatsApp Matrix integration
**Location**: WhatsApp connector / Matrix bridge
**Next Steps**:
- Verify Matrix bridge is running
- Check WhatsApp session status
- Test message sync manually
- Review WhatsApp connector logs

## 🎯 Priority Order
1. **High**: Daily Summary (affects home page UX)
2. **High**: WhatsApp Chat Pulling (core functionality)
3. **Medium**: Phone Login (alternative auth method)
4. **Low**: Nudges & Commitments (nice-to-have features)

## 📝 Notes
- Backend is running successfully on http://192.168.1.137:8000
- Frontend connects properly via Expo tunnel
- WhatsApp background sync is working (messages being processed)
- 929 contacts loaded successfully
