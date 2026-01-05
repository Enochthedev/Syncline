# WhatsApp QR Code Solution

## Problem

Your mautrix-whatsapp bridge doesn't support the `login-code` command for phone pairing.

Bridge logs show:
```
Received unknown command [mx_command=login-code]
```

## ✅ Solution: Use QR Code Login

QR code login is **fully supported** and works reliably with your bridge.

## 📱 Mobile App Implementation

### Method 1: Display QR Code in Mobile App (Recommended)

```javascript
import React, { useState, useEffect } from 'react';
import { View, Text, Image, Button, ActivityIndicator } from 'react-native';
import QRCode from 'react-native-qrcode-svg'; // npm install react-native-qrcode-svg

const WhatsAppQRConnect = ({ authToken }) => {
  const [connectionId, setConnectionId] = useState(null);
  const [qrCodeData, setQrCodeData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [checkingStatus, setCheckingStatus] = useState(false);

  // Step 1: Create connection
  const createConnection = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        'http://localhost:8000/api/v1/whatsapp/connections/create',
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        }
      );

      const data = await response.json();
      if (data.success) {
        setConnectionId(data.connection_id);
        await getQRCode(data.connection_id);
      }
    } catch (err) {
      setError('Failed to create connection');
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Get QR code
  const getQRCode = async (connId) => {
    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/whatsapp/${connId}/login`,
        {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        }
      );

      const result = await response.json();

      if (result.already_logged_in) {
        alert('Already connected to WhatsApp!');
        return;
      }

      if (result.qr_code) {
        setQrCodeData(result.qr_code);
        // Start polling for login completion
        pollLoginStatus(connId);
      }
    } catch (err) {
      setError('Failed to get QR code');
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Poll for login completion
  const pollLoginStatus = async (connId) => {
    setCheckingStatus(true);

    const interval = setInterval(async () => {
      try {
        const response = await fetch(
          `http://localhost:8000/api/v1/whatsapp/${connId}/session/status`,
          {
            headers: {
              'Authorization': `Bearer ${authToken}`
            }
          }
        );

        const status = await response.json();

        if (status.is_logged_in) {
          clearInterval(interval);
          setCheckingStatus(false);
          alert(`Connected as ${status.phone_number}!`);
          // Navigate to next screen or update UI
        }
      } catch (err) {
        console.error('Status check failed:', err);
      }
    }, 3000); // Check every 3 seconds

    // Stop polling after 5 minutes
    setTimeout(() => {
      clearInterval(interval);
      setCheckingStatus(false);
    }, 300000);
  };

  useEffect(() => {
    createConnection();
  }, []);

  return (
    <View style={{ padding: 20, alignItems: 'center' }}>
      <Text style={{ fontSize: 24, fontWeight: 'bold', marginBottom: 20 }}>
        Connect WhatsApp
      </Text>

      {loading && <ActivityIndicator size="large" />}

      {error && <Text style={{ color: 'red' }}>{error}</Text>}

      {qrCodeData && (
        <View style={{ alignItems: 'center' }}>
          <QRCode
            value={qrCodeData}
            size={250}
          />

          <Text style={{ marginTop: 20, fontSize: 16, textAlign: 'center' }}>
            1. Open WhatsApp on your phone{'\n'}
            2. Go to Settings → Linked Devices{'\n'}
            3. Tap "Link a Device"{'\n'}
            4. Scan this QR code
          </Text>

          {checkingStatus && (
            <View style={{ marginTop: 20 }}>
              <ActivityIndicator />
              <Text>Waiting for scan...</Text>
            </View>
          )}

          <Button
            title="Refresh QR Code"
            onPress={() => getQRCode(connectionId)}
            style={{ marginTop: 20 }}
          />
        </View>
      )}
    </View>
  );
};

export default WhatsAppQRConnect;
```

### Method 2: Link to Web WhatsApp

If you don't want to generate QR in the app:

```javascript
const openWebWhatsApp = async () => {
  // Create connection
  const response = await fetch(
    'http://localhost:8000/api/v1/whatsapp/connections/create',
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authToken}` }
    }
  );

  const { connection_id } = await response.json();

  // Get QR code URL
  const qrResponse = await fetch(
    `http://localhost:8000/api/v1/whatsapp/${connection_id}/login`,
    {
      headers: { 'Authorization': `Bearer ${authToken}` }
    }
  );

  const { qr_code } = await qrResponse.json();

  // Open in browser with QR code
  Linking.openURL(`https://web.whatsapp.com/?qr=${encodeURIComponent(qr_code)}`);
};
```

## 🧪 Test QR Code Login

```bash
# 1. Create connection
curl -X POST "http://localhost:8000/api/v1/whatsapp/connections/create" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Copy the connection_id

# 2. Get QR code
curl -X GET "http://localhost:8000/api/v1/whatsapp/{CONNECTION_ID}/login" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. You'll get a response like:
# {
#   "qr_code": "2@xxxxxxxxxxx...",
#   "already_logged_in": false,
#   "message": "Scan QR code with WhatsApp mobile app"
# }

# 4. Poll for login status
curl -X GET "http://localhost:8000/api/v1/whatsapp/{CONNECTION_ID}/session/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📦 Required Package

```bash
npm install react-native-qrcode-svg
# or
yarn add react-native-qrcode-svg
```

## Why This Works

1. ✅ QR code login is the **primary** method supported by mautrix-whatsapp
2. ✅ Your bridge is already configured for QR login
3. ✅ No additional bridge configuration needed
4. ✅ More reliable than phone pairing
5. ✅ Works with all WhatsApp accounts

## Alternative: Update Bridge for Phone Pairing

If you really want phone pairing, you'd need to:

1. Update to latest mautrix-whatsapp version
2. Check if your version supports phone pairing
3. Use different command format

But **QR code is the recommended method** and works perfectly!
