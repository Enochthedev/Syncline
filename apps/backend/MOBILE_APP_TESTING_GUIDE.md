# Mobile App Testing Guide

## Authentication Fix Summary

✅ **Fixed Issues:**
1. **Logout Bug**: Profile screen now properly calls AuthContext logout
2. **Navigation Guard**: Added AuthGuard component for proper auth routing
3. **WhatsApp Auth Check**: WhatsApp modal now checks authentication before connecting

## Test Credentials

Use these credentials to test the mobile app:

```
Username: testuser
Password: testpass123
Connection ID: 0f0460b8-9fc1-44be-beb1-7a0acce134df
```

## Testing Steps

### 1. Start Backend Server
```bash
cd apps/backend
python main.py
```

### 2. Start Mobile App
```bash
cd apps/Syncline
npm start
# or
yarn start
```

### 3. Test Authentication Flow

#### Login Test:
1. Open mobile app
2. Should automatically show login screen
3. Enter credentials:
   - Username: `testuser`
   - Password: `testpass123`
4. Tap "Sign In"
5. Should redirect to main app (tabs)

#### Logout Test:
1. Go to Profile tab
2. Scroll down to "Log Out" button
3. Tap "Log Out"
4. Confirm in alert dialog
5. Should redirect to login screen
6. Try accessing other tabs - should stay on login

### 4. Test WhatsApp Connection

#### Before Login (Should Fail):
1. Try to access connections without logging in
2. Should be redirected to login screen

#### After Login (Should Work):
1. Login with test credentials
2. Go to Connections tab
3. Tap WhatsApp card
4. Should show WhatsApp connection modal
5. Should NOT get 401 error
6. Should show QR code or connection options

## Expected Behavior

### ✅ Working:
- Login redirects to main app
- Logout redirects to login screen
- Authentication persists across app restarts
- WhatsApp modal shows without 401 errors
- API calls include proper Bearer tokens

### ❌ If Still Broken:
- Check backend server is running on port 8000
- Check mobile app can reach `http://localhost:8000` (or your IP)
- Check browser network tab for API calls
- Check mobile app console for errors

## API Endpoints Test

You can test the backend directly:

```bash
# Test login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'

# Test WhatsApp endpoint (use token from login response)
curl -X GET http://localhost:8000/api/v1/whatsapp/0f0460b8-9fc1-44be-beb1-7a0acce134df/status \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Troubleshooting

### Mobile App Won't Login
- Check backend server is running
- Check network connectivity
- Check credentials are correct
- Check mobile app console for errors

### Still Getting 401 Errors
- Check token is being stored in AsyncStorage
- Check API client is adding Authorization header
- Check token hasn't expired (30 minutes)
- Try logging out and back in

### WhatsApp Connection Issues
- Login first before trying to connect
- Check WhatsApp bridge is running (Matrix server)
- Check connection ID exists in database

## Next Steps

Once authentication is working:
1. Test WhatsApp QR code scanning
2. Test message sync after login
3. Test auto-sync functionality
4. Test chat list population

The mobile app should now properly handle authentication and be ready for WhatsApp testing! 🚀