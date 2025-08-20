#!/usr/bin/env python3
"""
WhatsApp Connection Test Script

This script tests the WhatsApp integration by:
1. Connecting to the API
2. Requesting a WhatsApp connection
3. Displaying the QR code
4. Monitoring connection status
"""

import requests
import json
import base64
import time
import sys
from PIL import Image
import io

# Configuration
REMI_BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test_user_123"


def print_status(message):
    print(f"[INFO] {message}")


def print_success(message):
    print(f"[SUCCESS] {message}")


def print_error(message):
    print(f"[ERROR] {message}")


def test_api_health():
    """Test if R.E.M.I API is responding"""
    try:
        response = requests.get(f"{REMI_BASE_URL}/")
        if response.status_code == 200:
            print_success("R.E.M.I API is responding")
            return True
        else:
            print_error(f"R.E.M.I API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to R.E.M.I API. Is it running?")
        return False


def test_whatsapp_endpoints():
    """Test WhatsApp-specific endpoints"""
    try:
        # Test bridge status
        response = requests.get(f"{REMI_BASE_URL}/api/whatsapp/bridges/status")
        if response.status_code == 200:
            print_success("WhatsApp bridge status endpoint is working")
            bridge_data = response.json()
            print(f"Bridge pool status: {json.dumps(bridge_data, indent=2)}")
        else:
            print_error(
                f"Bridge status endpoint returned {response.status_code}")

        # Test metrics endpoint
        response = requests.get(f"{REMI_BASE_URL}/api/whatsapp/metrics")
        if response.status_code == 200:
            print_success("WhatsApp metrics endpoint is working")
            metrics = response.json()
            print(f"Current metrics: {json.dumps(metrics, indent=2)}")
        else:
            print_error(f"Metrics endpoint returned {response.status_code}")

        return True
    except Exception as e:
        print_error(f"Error testing WhatsApp endpoints: {e}")
        return False


def connect_whatsapp():
    """Attempt to connect WhatsApp"""
    try:
        print_status("Requesting WhatsApp connection...")

        payload = {
            "user_id": TEST_USER_ID,
            "sync_tier": "real_time",
            "include_groups": False,
            "include_dms": True,
            "sync_history_days": 30,
            "auto_sync": True
        }

        response = requests.post(
            f"{REMI_BASE_URL}/api/whatsapp/connect",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            result = response.json()
            print_success(f"Connection request successful: {result['status']}")

            if result['status'] == 'ready':
                print_success("Bridge is available! QR code generated.")

                # Save QR code
                if 'qr_code' in result and result['qr_code']:
                    save_qr_code(result['qr_code'])
                    print_success("QR code saved as 'whatsapp_qr.png'")
                    print("📱 Open WhatsApp on your phone:")
                    print("   1. Go to Settings → Linked Devices")
                    print("   2. Tap 'Link a Device'")
                    print("   3. Scan the QR code in whatsapp_qr.png")

                return result['session_id']

            elif result['status'] == 'queued':
                print_status(
                    f"Added to queue at position {result['queue_position']}")
                print_status(
                    f"Estimated wait time: {result['estimated_wait_minutes']} minutes")
                return result['session_id']

        else:
            print_error(f"Connection request failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None

    except Exception as e:
        print_error(f"Error connecting WhatsApp: {e}")
        return None


def save_qr_code(qr_code_data):
    """Save QR code to file"""
    try:
        # Remove data URL prefix if present
        if qr_code_data.startswith('data:image/png;base64,'):
            qr_code_data = qr_code_data.split(',')[1]

        # Decode base64
        qr_bytes = base64.b64decode(qr_code_data)

        # Save to file
        with open('whatsapp_qr.png', 'wb') as f:
            f.write(qr_bytes)

        # Also try to display in terminal if possible
        try:
            img = Image.open(io.BytesIO(qr_bytes))
            print(f"QR Code size: {img.size}")
        except Exception:
            pass

    except Exception as e:
        print_error(f"Error saving QR code: {e}")


def monitor_connection_status(session_id):
    """Monitor connection status"""
    print_status("Monitoring connection status...")
    print("(Press Ctrl+C to stop monitoring)")

    try:
        while True:
            response = requests.get(
                f"{REMI_BASE_URL}/api/whatsapp/status/{TEST_USER_ID}")

            if response.status_code == 200:
                status = response.json()
                current_status = status.get('status', 'unknown')

                if current_status == 'connected':
                    print_success("🎉 WhatsApp is now connected!")
                    print(
                        f"Connected at: {status.get('connected_at', 'unknown')}")
                    print(
                        "You can now send WhatsApp messages and they will appear in R.E.M.I!")
                    break
                elif current_status == 'connecting':
                    print_status("📱 WhatsApp is connecting...")
                elif current_status == 'queued':
                    pos = status.get('queue_position', 'unknown')
                    wait = status.get('estimated_wait_minutes', 'unknown')
                    print_status(
                        f"⏳ In queue at position {pos}, ~{wait} minutes remaining")
                else:
                    print_status(f"Status: {current_status}")

            else:
                print_error(f"Status check failed: {response.status_code}")

            time.sleep(5)  # Check every 5 seconds

    except KeyboardInterrupt:
        print_status("Monitoring stopped by user")
    except Exception as e:
        print_error(f"Error monitoring status: {e}")


def test_message_retrieval():
    """Test retrieving WhatsApp messages"""
    try:
        print_status("Testing message retrieval...")

        response = requests.get(
            f"{REMI_BASE_URL}/api/v1/messages?platform=whatsapp&limit=5")

        if response.status_code == 200:
            messages = response.json()
            print_success(f"Retrieved {len(messages)} WhatsApp messages")

            for msg in messages:
                print(f"  From: {msg.get('sender', 'unknown')}")
                print(f"  Content: {msg.get('content', 'no content')[:50]}...")
                print(f"  Time: {msg.get('timestamp', 'unknown')}")
                print("  ---")
        else:
            print_error(f"Message retrieval failed: {response.status_code}")

    except Exception as e:
        print_error(f"Error retrieving messages: {e}")


def main():
    print("🧪 WhatsApp Integration Test Script")
    print("===================================")
    print()

    # Test API health
    if not test_api_health():
        print_error(
            "API health check failed. Please ensure R.E.M.I is running.")
        sys.exit(1)

    # Test WhatsApp endpoints
    if not test_whatsapp_endpoints():
        print_error("WhatsApp endpoints test failed.")
        sys.exit(1)

    # Connect WhatsApp
    session_id = connect_whatsapp()
    if not session_id:
        print_error("WhatsApp connection failed.")
        sys.exit(1)

    # Monitor connection status
    monitor_connection_status(session_id)

    # Test message retrieval
    test_message_retrieval()

    print()
    print_success("WhatsApp integration test complete!")
    print()
    print("Next steps:")
    print("1. Send a WhatsApp message to yourself or a contact")
    print("2. Check http://localhost:8000/api/v1/messages?platform=whatsapp")
    print("3. Explore the API docs at http://localhost:8000/docs")


if __name__ == "__main__":
    main()
