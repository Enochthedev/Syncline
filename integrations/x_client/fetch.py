def fetch_dms(tweepy_api):
    dms = []
    for dm_event in tweepy_api.get_direct_messages():
        sender = dm_event.message_create['sender_id']
        text = dm_event.message_create['message_data']['text']
        dms.append({
            'sender': sender,
            'text': text
        })
    return dms