from integrations.gmail_client.fetch import fetch_emails

def test_gmail_fetch_basic():
    print("\n📨 Running Gmail fetch test...")

    try:
        emails = fetch_emails(query="is:inbox", max_results=5)

        if not emails:
            print("⚠️  No emails returned.")
        else:
            for i, email in enumerate(emails, 1):
                print(f"\n📧 Email {i}")
                print(f"ID      : {email['id']}")
                print(f"Snippet : {email['snippet'][:100]}...")
                print(f"Thread  : {email.get('threadId')}\n")

        print("✅ Gmail fetch test completed.\n")

    except Exception as e:
        print("❌ Error while fetching Gmail:", e)

if __name__ == "__main__":
    test_gmail_fetch_basic()