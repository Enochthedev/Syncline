from .auth import get_gmail_service

def fetch_emails(query="is:inbox", max_results=10):
    service = get_gmail_service()
    response = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
    messages = response.get('messages', [])

    emails = []
    for msg in messages:
        full_msg = service.users().messages().get(userId='me', id=msg['id']).execute()
        snippet = full_msg.get('snippet', '')
        emails.append({
            'id': msg['id'],
            'snippet': snippet,
            'threadId': full_msg.get('threadId')
        })

    return emails