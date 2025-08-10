from integrations.gmail_client.fetch import fetch_emails

if __name__ == "__main__":
    print("📬 Fetching recent emails from your inbox...\n")
    emails = fetch_emails(query="is:inbox", max_results=5)
    
    if not emails:
        print("No emails found.")
    else:
        for i, email in enumerate(emails, 1):
            print(f"{i}. ID: {email['id']}\n   Snippet: {email['snippet'][:100]}...\n")