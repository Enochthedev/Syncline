import React, { useState, useEffect, useRef } from 'react';
import { 
    View, 
    Text, 
    StyleSheet, 
    FlatList, 
    TextInput, 
    TouchableOpacity,
    KeyboardAvoidingView,
    Platform,
    Alert
} from 'react-native';
import { ChatMessage, messagesAPI } from '../../src/api/endpoints/messages';
import { theme } from '../../src/theme';

interface ChatMessagesViewProps {
    threadId: string;
    platform: string;
    contactName?: string;
    onBack: () => void;
}

interface MessageBubbleProps {
    message: ChatMessage;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
    const isFromMe = message.is_from_me;
    
    const formatTime = (timestamp: string) => {
        return new Date(timestamp).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    };

    return (
        <View style={[
            styles.messageContainer,
            isFromMe ? styles.messageFromMe : styles.messageFromOther
        ]}>
            <View style={[
                styles.messageBubble,
                isFromMe ? styles.bubbleFromMe : styles.bubbleFromOther
            ]}>
                {!isFromMe && (
                    <Text style={styles.senderName}>{message.sender_name}</Text>
                )}
                <Text style={[
                    styles.messageText,
                    isFromMe ? styles.textFromMe : styles.textFromOther
                ]}>
                    {message.content}
                </Text>
                <Text style={[
                    styles.messageTime,
                    isFromMe ? styles.timeFromMe : styles.timeFromOther
                ]}>
                    {formatTime(message.timestamp)}
                    {message.has_attachments && ' 📎'}
                </Text>
            </View>
        </View>
    );
};

export const ChatMessagesView: React.FC<ChatMessagesViewProps> = ({
    threadId,
    platform,
    contactName,
    onBack
}) => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [loading, setLoading] = useState(true);
    const [newMessage, setNewMessage] = useState('');
    const [sending, setSending] = useState(false);
    const flatListRef = useRef<FlatList>(null);

    useEffect(() => {
        loadMessages();
    }, [threadId, platform]);

    const loadMessages = async () => {
        try {
            setLoading(true);
            const response = await messagesAPI.getChatMessages(threadId, platform, {
                limit: 50
            });
            setMessages(response.messages);
        } catch (error) {
            console.error('Failed to load messages:', error);
            Alert.alert('Error', 'Failed to load messages');
        } finally {
            setLoading(false);
        }
    };

    const sendMessage = async () => {
        if (!newMessage.trim() || sending) return;

        try {
            setSending(true);
            const response = await messagesAPI.sendMessage(
                threadId,
                platform,
                newMessage.trim()
            );

            if (response.success) {
                setNewMessage('');
                // Reload messages to show the sent message
                await loadMessages();
                // Scroll to bottom
                setTimeout(() => {
                    flatListRef.current?.scrollToEnd({ animated: true });
                }, 100);
            } else {
                Alert.alert('Error', response.message || 'Failed to send message');
            }
        } catch (error) {
            console.error('Failed to send message:', error);
            Alert.alert('Error', 'Failed to send message');
        } finally {
            setSending(false);
        }
    };

    const renderMessage = ({ item }: { item: ChatMessage }) => (
        <MessageBubble message={item} />
    );

    return (
        <KeyboardAvoidingView 
            style={styles.container}
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity onPress={onBack} style={styles.backButton}>
                    <Text style={styles.backText}>← Back</Text>
                </TouchableOpacity>
                <View style={styles.headerInfo}>
                    <Text style={styles.contactName} numberOfLines={1}>
                        {contactName || `${platform} chat`}
                    </Text>
                    <Text style={styles.platformName}>{platform}</Text>
                </View>
            </View>

            {/* Messages */}
            <FlatList
                ref={flatListRef}
                data={messages}
                renderItem={renderMessage}
                keyExtractor={(item) => item.id}
                style={styles.messagesList}
                contentContainerStyle={styles.messagesContent}
                showsVerticalScrollIndicator={false}
                onContentSizeChange={() => {
                    flatListRef.current?.scrollToEnd({ animated: false });
                }}
            />

            {/* Input */}
            <View style={styles.inputContainer}>
                <TextInput
                    style={styles.textInput}
                    value={newMessage}
                    onChangeText={setNewMessage}
                    placeholder="Type a message..."
                    placeholderTextColor={theme.colors.textSecondary}
                    multiline
                    maxLength={1000}
                />
                <TouchableOpacity
                    onPress={sendMessage}
                    disabled={!newMessage.trim() || sending}
                    style={[
                        styles.sendButton,
                        (!newMessage.trim() || sending) && styles.sendButtonDisabled
                    ]}
                >
                    <Text style={[
                        styles.sendButtonText,
                        (!newMessage.trim() || sending) && styles.sendButtonTextDisabled
                    ]}>
                        {sending ? '...' : 'Send'}
                    </Text>
                </TouchableOpacity>
            </View>
        </KeyboardAvoidingView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: theme.spacing.m,
        backgroundColor: theme.colors.surface,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    backButton: {
        marginRight: theme.spacing.m,
    },
    backText: {
        ...theme.typography.body,
        color: theme.colors.primary,
    },
    headerInfo: {
        flex: 1,
    },
    contactName: {
        ...theme.typography.h3,
    },
    platformName: {
        ...theme.typography.caption,
        color: theme.colors.textSecondary,
        textTransform: 'capitalize',
    },
    messagesList: {
        flex: 1,
    },
    messagesContent: {
        padding: theme.spacing.m,
        paddingBottom: theme.spacing.l,
    },
    messageContainer: {
        marginBottom: theme.spacing.m,
    },
    messageFromMe: {
        alignItems: 'flex-end',
    },
    messageFromOther: {
        alignItems: 'flex-start',
    },
    messageBubble: {
        maxWidth: '80%',
        padding: theme.spacing.m,
        borderRadius: theme.borderRadius.lg,
    },
    bubbleFromMe: {
        backgroundColor: theme.colors.primary,
    },
    bubbleFromOther: {
        backgroundColor: theme.colors.surface,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    senderName: {
        ...theme.typography.caption,
        color: theme.colors.textSecondary,
        marginBottom: theme.spacing.xs,
        fontWeight: '600',
    },
    messageText: {
        ...theme.typography.body,
        lineHeight: 20,
    },
    textFromMe: {
        color: 'white',
    },
    textFromOther: {
        color: theme.colors.text,
    },
    messageTime: {
        ...theme.typography.caption,
        marginTop: theme.spacing.xs,
        fontSize: 11,
    },
    timeFromMe: {
        color: 'rgba(255, 255, 255, 0.7)',
    },
    timeFromOther: {
        color: theme.colors.textSecondary,
    },
    inputContainer: {
        flexDirection: 'row',
        alignItems: 'flex-end',
        padding: theme.spacing.m,
        backgroundColor: theme.colors.surface,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
        gap: theme.spacing.m,
    },
    textInput: {
        flex: 1,
        ...theme.typography.body,
        borderWidth: 1,
        borderColor: theme.colors.border,
        borderRadius: theme.borderRadius.lg,
        paddingHorizontal: theme.spacing.m,
        paddingVertical: theme.spacing.s,
        maxHeight: 100,
        backgroundColor: theme.colors.background,
    },
    sendButton: {
        backgroundColor: theme.colors.primary,
        paddingHorizontal: theme.spacing.l,
        paddingVertical: theme.spacing.s,
        borderRadius: theme.borderRadius.lg,
        justifyContent: 'center',
        alignItems: 'center',
    },
    sendButtonDisabled: {
        backgroundColor: theme.colors.textSecondary,
    },
    sendButtonText: {
        ...theme.typography.body,
        color: 'white',
        fontWeight: '600',
    },
    sendButtonTextDisabled: {
        color: 'rgba(255, 255, 255, 0.5)',
    },
});