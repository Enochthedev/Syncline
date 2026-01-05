/**
 * Dummy Data for MESH Documentation Screenshots
 * This file contains mock data to populate the UI for demonstration purposes
 */

// ============================================================================
// Platform Connection Data (Section 4.11.1)
// ============================================================================
export const DUMMY_CONNECTIONS = [
    {
        id: 'conn_gmail_001',
        platform: 'gmail' as const,
        status: 'active' as const,
        last_sync_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(), // 2 minutes ago
        message_count: 1247,
        email: 'alex.wave@gmail.com',
    },
    {
        id: 'conn_slack_001',
        platform: 'slack' as const,
        status: 'active' as const,
        last_sync_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 minutes ago
        message_count: 892,
        workspace: 'Acme Corp',
    },
    {
        id: 'conn_discord_001',
        platform: 'discord' as const,
        status: 'active' as const,
        last_sync_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(), // 10 minutes ago
        message_count: 456,
        servers: 3,
    },
    {
        id: 'conn_telegram_001',
        platform: 'telegram' as const,
        status: 'disconnected' as const,
        last_sync_at: null,
        message_count: 0,
    },
    {
        id: 'conn_twitter_001',
        platform: 'twitter' as const,
        status: 'disconnected' as const,
        last_sync_at: null,
        message_count: 0,
    },
    {
        id: 'conn_whatsapp_001',
        platform: 'whatsapp' as const,
        status: 'active' as const,
        last_sync_at: new Date(Date.now() - 1 * 60 * 1000).toISOString(), // 1 minute ago
        message_count: 2341,
    },
];

// ============================================================================
// Message Data (Section 4.11.2, 4.11.3)
// ============================================================================
export const DUMMY_MESSAGES = [
    {
        id: 'msg_001',
        platform: 'gmail',
        platformColor: '#EA4335',
        sender: 'Sarah Johnson',
        senderEmail: 'sarah.johnson@company.com',
        senderAvatar: null,
        subject: 'Q4 Budget Draft - Review Needed',
        content: 'Hi Alex, I\'ve attached the Q4 budget draft for your review. Could you please take a look and provide feedback by Friday? We need to finalize the numbers before the board meeting next week.',
        preview: 'Hi Alex, I\'ve attached the Q4 budget draft for your review. Could you please take a look...',
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
        isRead: false,
        hasAttachment: true,
        attachments: [{ name: 'Q4_Budget_Draft.xlsx', size: '245 KB' }],
        threadCount: 5,
        recipients: ['alex.wave@company.com'],
        entities: {
            people: ['Sarah Johnson'],
            topics: ['Q4 Budget', 'Board Meeting'],
            dates: ['Friday, January 19'],
        },
        aiSummary: 'Sarah shared Q4 budget draft and requested feedback by Friday',
        commitments: ['Review budget by Friday, January 19'],
    },
    {
        id: 'msg_002',
        platform: 'slack',
        platformColor: '#4A154B',
        sender: 'Mike Chen',
        senderEmail: null,
        senderAvatar: null,
        channelName: '#project-alpha',
        content: 'Hey team! Just pushed the latest design mockups to Figma. Let me know what you think! 🎨',
        preview: 'Hey team! Just pushed the latest design mockups to Figma. Let me know what you...',
        timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(), // 4 hours ago
        isRead: false,
        hasAttachment: false,
        threadCount: 8,
        entities: {
            people: ['Mike Chen'],
            topics: ['Design Mockups', 'Figma'],
            dates: [],
        },
        aiSummary: 'Mike shared new design mockups in Figma for team review',
        commitments: [],
    },
    {
        id: 'msg_003',
        platform: 'discord',
        platformColor: '#5865F2',
        sender: 'Emily Davis',
        senderEmail: null,
        senderAvatar: null,
        serverName: 'Dev Community',
        channelName: 'general',
        content: 'Anyone up for the hackathon this weekend? I\'m looking for teammates!',
        preview: 'Anyone up for the hackathon this weekend? I\'m looking for teammates!',
        timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(), // 6 hours ago
        isRead: true,
        hasAttachment: false,
        threadCount: 0,
        entities: {
            people: ['Emily Davis'],
            topics: ['Hackathon'],
            dates: ['This weekend'],
        },
        aiSummary: 'Emily is recruiting teammates for weekend hackathon',
        commitments: [],
    },
    {
        id: 'msg_004',
        platform: 'gmail',
        platformColor: '#EA4335',
        sender: 'John Martinez',
        senderEmail: 'john.martinez@vendor.com',
        senderAvatar: null,
        subject: 'Re: Contract Renewal Discussion',
        content: 'Thanks for the call yesterday. As discussed, I\'ll send over the revised terms by Monday. Looking forward to continuing our partnership.',
        preview: 'Thanks for the call yesterday. As discussed, I\'ll send over the revised terms by...',
        timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(), // 8 hours ago
        isRead: true,
        hasAttachment: false,
        threadCount: 12,
        recipients: ['alex.wave@company.com'],
        entities: {
            people: ['John Martinez'],
            topics: ['Contract Renewal', 'Partnership'],
            dates: ['Monday'],
        },
        aiSummary: 'John will send revised contract terms by Monday',
        commitments: [],
    },
    {
        id: 'msg_005',
        platform: 'slack',
        platformColor: '#4A154B',
        sender: 'Lisa Wang',
        senderEmail: null,
        senderAvatar: null,
        channelName: 'Direct Message',
        content: 'Quick question - do you have the login credentials for the staging server? Need to deploy the hotfix.',
        preview: 'Quick question - do you have the login credentials for the staging server?...',
        timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(), // 12 hours ago
        isRead: true,
        hasAttachment: false,
        threadCount: 3,
        entities: {
            people: ['Lisa Wang'],
            topics: ['Staging Server', 'Hotfix', 'Deployment'],
            dates: [],
        },
        aiSummary: 'Lisa needs staging server credentials for hotfix deployment',
        commitments: [],
    },
    {
        id: 'msg_006',
        platform: 'whatsapp',
        platformColor: '#25D366',
        sender: 'David Kim',
        senderEmail: null,
        senderAvatar: null,
        phoneNumber: '+1 (555) 123-4567',
        content: 'Hey! Are we still on for lunch tomorrow? That new Thai place looks great 🍜',
        preview: 'Hey! Are we still on for lunch tomorrow? That new Thai place looks great 🍜',
        timestamp: new Date(Date.now() - 18 * 60 * 60 * 1000).toISOString(), // 18 hours ago
        isRead: true,
        hasAttachment: false,
        threadCount: 0,
        entities: {
            people: ['David Kim'],
            topics: ['Lunch'],
            dates: ['Tomorrow'],
        },
        aiSummary: 'David confirming lunch plans for tomorrow',
        commitments: [],
    },
];

// ============================================================================
// Contact Data (Section 4.11.4)
// ============================================================================
export const DUMMY_CONTACTS = [
    {
        id: 'contact_001',
        name: 'Sarah Johnson',
        primaryEmail: 'sarah.johnson@company.com',
        avatarUrl: null,
        platformIdentities: {
            gmail: 'sarah.johnson@company.com',
            slack: '@sarahjohnson',
            telegram: '@saraj',
        },
        relationshipStrength: 87,
        totalMessages: 342,
        sentMessages: 180,
        receivedMessages: 162,
        firstInteraction: '2023-03-15',
        lastInteraction: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        avgResponseTime: 2.4, // hours
        communicationFrequency: 'High',
        topTopics: [
            { topic: 'Project deadlines', count: 48 },
            { topic: 'Budget planning', count: 31 },
            { topic: 'Team coordination', count: 27 },
        ],
        recentFiles: [
            { name: 'Q4_Budget_Draft.xlsx', date: '2024-01-10', platform: 'Gmail' },
            { name: 'Project_Timeline.pdf', date: '2024-01-08', platform: 'Slack' },
        ],
        activeCommitments: [
            { description: 'Send updated timeline by Friday', dueDate: '2024-01-19' },
        ],
        aiInsights: [
            'Regular collaborator on project planning and budget discussions',
            'Typically responds within 3 hours during business days',
            'Prefers Slack for quick questions, email for formal communications',
        ],
    },
    {
        id: 'contact_002',
        name: 'Mike Chen',
        primaryEmail: 'mike.chen@company.com',
        avatarUrl: null,
        platformIdentities: {
            gmail: 'mike.chen@company.com',
            slack: '@mikechen',
            discord: 'MikeDev#1234',
        },
        relationshipStrength: 72,
        totalMessages: 156,
        sentMessages: 85,
        receivedMessages: 71,
        firstInteraction: '2023-06-20',
        lastInteraction: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
        avgResponseTime: 4.1,
        communicationFrequency: 'Medium',
        topTopics: [
            { topic: 'Design reviews', count: 32 },
            { topic: 'Product features', count: 28 },
            { topic: 'UI/UX feedback', count: 19 },
        ],
        recentFiles: [
            { name: 'Design_Mockups_v3.fig', date: '2024-01-14', platform: 'Slack' },
        ],
        activeCommitments: [],
        aiInsights: [
            'Primary contact for design-related discussions',
            'Most active on Slack during afternoon hours',
        ],
    },
    {
        id: 'contact_003',
        name: 'Emily Davis',
        primaryEmail: 'emily.davis@external.org',
        avatarUrl: null,
        platformIdentities: {
            discord: 'EmilyD#5678',
        },
        relationshipStrength: 45,
        totalMessages: 67,
        sentMessages: 30,
        receivedMessages: 37,
        firstInteraction: '2023-09-10',
        lastInteraction: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
        avgResponseTime: 8.2,
        communicationFrequency: 'Low',
        topTopics: [
            { topic: 'Community events', count: 15 },
            { topic: 'Hackathons', count: 12 },
        ],
        recentFiles: [],
        activeCommitments: [],
        aiInsights: [
            'Connected through developer community Discord',
            'Occasional interaction for tech events',
        ],
    },
    {
        id: 'contact_004',
        name: 'John Martinez',
        primaryEmail: 'john.martinez@vendor.com',
        avatarUrl: null,
        platformIdentities: {
            gmail: 'john.martinez@vendor.com',
        },
        relationshipStrength: 58,
        totalMessages: 89,
        sentMessages: 42,
        receivedMessages: 47,
        firstInteraction: '2023-01-05',
        lastInteraction: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
        avgResponseTime: 12.5,
        communicationFrequency: 'Low',
        topTopics: [
            { topic: 'Contract negotiations', count: 24 },
            { topic: 'Vendor services', count: 18 },
        ],
        recentFiles: [
            { name: 'Service_Agreement_2024.pdf', date: '2024-01-05', platform: 'Gmail' },
        ],
        activeCommitments: [],
        aiInsights: [
            'External vendor contact for service agreements',
            'Formal communication style, prefers email',
        ],
    },
    {
        id: 'contact_005',
        name: 'Lisa Wang',
        primaryEmail: 'lisa.wang@company.com',
        avatarUrl: null,
        platformIdentities: {
            gmail: 'lisa.wang@company.com',
            slack: '@lisawang',
        },
        relationshipStrength: 81,
        totalMessages: 278,
        sentMessages: 145,
        receivedMessages: 133,
        firstInteraction: '2022-11-15',
        lastInteraction: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
        avgResponseTime: 1.8,
        communicationFrequency: 'High',
        topTopics: [
            { topic: 'Technical issues', count: 65 },
            { topic: 'Deployments', count: 48 },
            { topic: 'Code reviews', count: 35 },
        ],
        recentFiles: [],
        activeCommitments: [
            { description: 'Review PR #456', dueDate: '2024-01-18' },
        ],
        aiInsights: [
            'Go-to person for technical and deployment questions',
            'Quick responder, usually within 2 hours',
            'Prefers Slack for urgent matters',
        ],
    },
];

// ============================================================================
// Thread/Conversation Data (Section 4.11.5)
// ============================================================================
export const DUMMY_THREADS = [
    {
        id: 'thread_001',
        title: 'Q4 Budget Discussion',
        participants: [
            { name: 'Alice Thompson', avatar: null },
            { name: 'Bob Wilson', avatar: null },
            { name: 'Carol Martinez', avatar: null },
            { name: 'Alex Wave', avatar: null },
        ],
        platform: 'gmail',
        messageCount: 8,
        dateRange: {
            start: '2024-01-10',
            end: '2024-01-15',
        },
        aiSummary: {
            overview: 'Team discussion about Q4 budget allocation across departments with focus on marketing spend increase and engineering hiring pause',
            keyPoints: [
                'Marketing budget increased by 15%',
                'Engineering hiring on hold until Q2 2025',
                'Final approval required from CFO',
                'Timeline: Decision needed by January 20',
            ],
            decisions: [
                { text: 'Approved 15% marketing budget increase', status: 'completed' },
                { text: 'Postponed engineering hires to Q2', status: 'completed' },
                { text: 'Pending CFO approval for final plan', status: 'pending' },
            ],
            actionItems: [
                { assignee: 'Alice', task: 'Finalize budget numbers by Friday', completed: false },
                { assignee: 'Bob', task: 'Schedule CFO approval meeting', completed: false },
                { assignee: 'Carol', task: 'Research marketing agency costs', completed: true },
            ],
        },
        messages: [
            {
                id: 'tmsg_001',
                sender: 'Alice Thompson',
                timestamp: '2024-01-10T09:00:00Z',
                content: 'Hi everyone, let\'s discuss the Q4 budget allocation. I\'ve prepared a preliminary draft.',
                attachments: [{ name: 'Q4_Budget_Draft.xlsx', size: '245 KB' }],
            },
            {
                id: 'tmsg_002',
                sender: 'Bob Wilson',
                timestamp: '2024-01-10T10:30:00Z',
                content: 'Thanks Alice. I think we should consider increasing the marketing budget given our Q3 performance.',
            },
            {
                id: 'tmsg_003',
                sender: 'Carol Martinez',
                timestamp: '2024-01-11T14:00:00Z',
                content: 'I agree with Bob. I\'ve done some research on marketing agencies - costs range from $50K-$80K per quarter.',
            },
            {
                id: 'tmsg_004',
                sender: 'Alex Wave',
                timestamp: '2024-01-12T09:15:00Z',
                content: 'What about engineering hiring? We had planned to bring on 3 new developers.',
            },
            {
                id: 'tmsg_005',
                sender: 'Alice Thompson',
                timestamp: '2024-01-12T11:00:00Z',
                content: 'Given the current budget constraints, I recommend we postpone engineering hires to Q2.',
            },
            {
                id: 'tmsg_006',
                sender: 'Bob Wilson',
                timestamp: '2024-01-13T16:30:00Z',
                content: 'That makes sense. Let\'s allocate 15% more to marketing and hold on engineering for now.',
            },
            {
                id: 'tmsg_007',
                sender: 'Carol Martinez',
                timestamp: '2024-01-14T10:00:00Z',
                content: 'I\'ve completed the marketing agency research. Attached my findings.',
            },
            {
                id: 'tmsg_008',
                sender: 'Alice Thompson',
                timestamp: '2024-01-15T09:00:00Z',
                content: 'Great work team! I\'ll finalize the numbers by Friday. Bob, can you schedule the CFO meeting?',
            },
        ],
    },
];

// ============================================================================
// Commitment Tracking Data (Section 4.11.6)
// ============================================================================
export const DUMMY_COMMITMENTS = [
    {
        id: 'commit_001',
        description: 'Send final budget numbers to Sarah',
        fullDescription: 'Send final budget numbers to Sarah by end of day Friday',
        status: 'overdue' as const,
        dueDate: '2024-01-18T17:00:00Z',
        confidence: 89,
        committedBy: 'You',
        committedTo: 'Sarah Johnson',
        sourceMessage: {
            platform: 'Slack',
            timestamp: '2024-01-15T10:30:00Z',
            context: [
                { sender: 'Sarah', content: 'When can you get me those Q4 budget numbers?' },
                { sender: 'You', content: 'I\'ll have the final numbers to you by end of day Friday' },
            ],
        },
        patterns: {
            commitmentPhrase: "I'll have",
            recipient: 'to you',
            deadline: 'by end of day Friday',
            dateResolution: 'Friday = January 18, 2024 (based on message timestamp)',
        },
        createdAt: '2024-01-15T10:35:00Z',
    },
    {
        id: 'commit_002',
        description: 'Review project proposal draft',
        fullDescription: 'Review the project proposal draft and provide feedback',
        status: 'pending' as const,
        dueDate: '2024-01-21T23:59:00Z',
        confidence: 76,
        committedBy: 'You',
        committedTo: 'Project Team',
        sourceMessage: {
            platform: 'Gmail',
            timestamp: '2024-01-14T14:00:00Z',
            context: [
                { sender: 'Team Lead', content: 'Can everyone review the proposal by Sunday?' },
                { sender: 'You', content: 'Sure, I\'ll take a look this weekend' },
            ],
        },
        patterns: {
            commitmentPhrase: "I'll take a look",
            recipient: 'implied (team)',
            deadline: 'this weekend',
            dateResolution: 'Weekend = January 20-21, 2024',
        },
        createdAt: '2024-01-14T14:05:00Z',
    },
    {
        id: 'commit_003',
        description: 'Provide feedback on design mockups',
        fullDescription: 'Review and provide detailed feedback on the new design mockups',
        status: 'pending' as const,
        dueDate: '2024-01-28T17:00:00Z',
        confidence: 91,
        committedBy: 'You',
        committedTo: 'Design Team',
        sourceMessage: {
            platform: 'Discord',
            timestamp: '2024-01-16T11:00:00Z',
            context: [
                { sender: 'Designer', content: 'Could you review these mockups when you get a chance? No rush - next week is fine.' },
                { sender: 'You', content: 'Will do! I\'ll have feedback to you by next Friday.' },
            ],
        },
        patterns: {
            commitmentPhrase: 'Will do',
            recipient: 'to you',
            deadline: 'by next Friday',
            dateResolution: 'Next Friday = January 28, 2024',
        },
        createdAt: '2024-01-16T11:02:00Z',
    },
    {
        id: 'commit_004',
        description: 'Schedule team sync meeting',
        fullDescription: 'Schedule a team sync meeting for next week',
        status: 'completed' as const,
        dueDate: '2024-01-17T12:00:00Z',
        confidence: 85,
        committedBy: 'You',
        committedTo: 'Engineering Team',
        sourceMessage: {
            platform: 'Slack',
            timestamp: '2024-01-15T09:00:00Z',
            context: [
                { sender: 'Manager', content: 'Can you set up a team sync for next week?' },
                { sender: 'You', content: 'On it! Will send the invite by EOD tomorrow.' },
            ],
        },
        patterns: {
            commitmentPhrase: 'On it',
            recipient: 'implied',
            deadline: 'by EOD tomorrow',
            dateResolution: 'Tomorrow EOD = January 17, 2024 5PM',
        },
        createdAt: '2024-01-15T09:02:00Z',
        completedAt: '2024-01-16T16:30:00Z',
    },
    {
        id: 'commit_005',
        description: 'Share API documentation',
        fullDescription: 'Share the updated API documentation with the frontend team',
        status: 'pending' as const,
        dueDate: '2024-01-25T17:00:00Z',
        confidence: 78,
        committedBy: 'You',
        committedTo: 'Frontend Team',
        sourceMessage: {
            platform: 'Slack',
            timestamp: '2024-01-17T15:00:00Z',
            context: [
                { sender: 'Frontend Dev', content: 'Do you have the API docs ready?' },
                { sender: 'You', content: 'Not yet, but I\'ll have them ready by end of next week.' },
            ],
        },
        patterns: {
            commitmentPhrase: "I'll have them ready",
            recipient: 'implied (frontend)',
            deadline: 'end of next week',
            dateResolution: 'End of next week = January 25, 2024',
        },
        createdAt: '2024-01-17T15:03:00Z',
    },
];

// ============================================================================
// Nudge/Notification Data (Section 4.11.7)
// ============================================================================
export const DUMMY_NUDGES = [
    {
        id: 'nudge_001',
        type: 'commitment_reminder' as const,
        priority: 'high' as const,
        title: 'Commitment Due Tomorrow',
        message: 'Your commitment to send budget numbers to Sarah is due tomorrow (Friday, Jan 19)',
        suggestedActions: [
            { label: 'Mark as complete', action: 'complete' },
            { label: 'View commitment details', action: 'view' },
            { label: 'Send reminder to yourself', action: 'reminder' },
        ],
        createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
        relatedId: 'commit_001',
    },
    {
        id: 'nudge_002',
        type: 'follow_up' as const,
        priority: 'medium' as const,
        title: 'Consider Following Up',
        message: 'No response to your message sent 3 days ago: "Can we schedule that meeting?"',
        suggestedActions: [
            { label: 'Send follow-up', action: 'followup' },
            { label: 'View conversation', action: 'view' },
            { label: 'Dismiss', action: 'dismiss' },
        ],
        createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
        relatedId: 'msg_004',
    },
    {
        id: 'nudge_003',
        type: 'reconnection' as const,
        priority: 'low' as const,
        title: 'Time to Reconnect?',
        message: "It's been 32 days since you last spoke with John Martinez",
        suggestedActions: [
            { label: 'Send message', action: 'message' },
            { label: 'View history', action: 'history' },
            { label: 'Remind me later', action: 'snooze' },
        ],
        createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        relatedId: 'contact_004',
    },
    {
        id: 'nudge_004',
        type: 'commitment_reminder' as const,
        priority: 'medium' as const,
        title: 'Commitment Coming Up',
        message: 'Review project proposal draft is due in 2 days (Sunday, Jan 21)',
        suggestedActions: [
            { label: 'Start now', action: 'view' },
            { label: 'Reschedule', action: 'reschedule' },
            { label: 'Dismiss', action: 'dismiss' },
        ],
        createdAt: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
        relatedId: 'commit_002',
    },
];

// ============================================================================
// Daily Summary Data (Section 4.11.8)
// ============================================================================
export const DUMMY_DAILY_SUMMARY = {
    date: new Date().toISOString().split('T')[0],
    overview: {
        totalMessages: 18,
        platformsUsed: 3,
        uniqueConversations: 8,
        activeContacts: 6,
        newCommitments: 2,
        filesShared: 1,
    },
    byContact: [
        {
            contact: 'Sarah Johnson',
            messageCount: 4,
            topics: ['Budget planning', 'Project deadlines'],
            summary: 'Continued Q4 budget discussion. Sarah requested final numbers by Friday. Shared updated spreadsheet with preliminary allocations.',
            keyPoints: [
                'Q4 budget draft attached (Q4_Budget_Draft.xlsx)',
                'Deadline set for Friday delivery',
                'Marketing budget increase to 15% approved',
            ],
            actionItems: ['Send final budget by Friday'],
        },
        {
            contact: 'Team Channel',
            messageCount: 3,
            topics: ['Sprint planning', 'Technical updates'],
            summary: 'Team discussed upcoming sprint priorities and technical debt items.',
            keyPoints: [
                'Sprint 24 starts Monday',
                'Focus on performance optimization',
            ],
            actionItems: [],
        },
        {
            contact: 'Mike Chen',
            messageCount: 2,
            topics: ['Design reviews'],
            summary: 'Quick sync on design mockups for the new dashboard feature.',
            keyPoints: ['Mockups approved with minor changes'],
            actionItems: ['Review updated mockups'],
        },
    ],
    actionItems: [
        { task: 'Send budget to Sarah by Friday', priority: 'High', contact: 'Sarah Johnson' },
        { task: 'Schedule team meeting next week', priority: 'Medium', contact: 'Team' },
        { task: 'Review design mockups', priority: 'Low', contact: 'Mike Chen' },
    ],
    newCommitments: [
        { description: 'Send budget numbers by Friday', to: 'Sarah Johnson' },
        { description: 'Schedule team meeting next week', to: 'Team' },
    ],
    filesShared: [
        { name: 'Q4_Budget_Draft.xlsx', from: 'Sarah Johnson', platform: 'Gmail' },
    ],
    communicationPatterns: {
        peakActivity: '10-11 AM',
        peakMessages: 6,
        mostActivePlatform: 'Slack',
        platformPercentage: 58,
        avgResponseTime: 2.1,
    },
};

// ============================================================================
// Search Results Data (Section 4.11.3)
// ============================================================================
export const DUMMY_SEARCH_RESULTS = [
    {
        id: 'result_001',
        relevanceScore: 0.94,
        relevanceStars: 5,
        matchType: 'semantic' as const,
        platform: 'slack',
        platformColor: '#4A154B',
        date: '2024-01-15',
        sender: 'You',
        highlightedSnippet: "I'll have the <mark>budget</mark> numbers ready by Friday for <mark>Sarah</mark>",
        fullContent: "I'll have the budget numbers ready by Friday for Sarah. Let me finalize the Q4 projections first.",
        entities: ['Sarah Johnson', 'budget', 'Friday'],
    },
    {
        id: 'result_002',
        relevanceScore: 0.87,
        relevanceStars: 4,
        matchType: 'keyword' as const,
        platform: 'gmail',
        platformColor: '#EA4335',
        date: '2024-01-14',
        sender: 'Sarah Johnson',
        highlightedSnippet: "Could you review the Q4 <mark>budget</mark> draft? I need your feedback...",
        fullContent: "Could you review the Q4 budget draft? I need your feedback before the board meeting.",
        entities: ['Sarah Johnson', 'budget', 'Q4'],
        threadId: 'thread_001',
    },
    {
        id: 'result_003',
        relevanceScore: 0.72,
        relevanceStars: 3,
        matchType: 'semantic' as const,
        platform: 'gmail',
        platformColor: '#EA4335',
        date: '2024-01-10',
        sender: 'Alice Thompson',
        highlightedSnippet: "Let's discuss the <mark>budget</mark> allocation for next quarter...",
        fullContent: "Let's discuss the budget allocation for next quarter. I've prepared some initial numbers.",
        entities: ['Alice Thompson', 'budget', 'allocation'],
        threadId: 'thread_001',
    },
];

// ============================================================================
// Settings Data (Section 4.11.9)
// ============================================================================
export const DUMMY_SETTINGS = {
    platformSync: {
        gmail: {
            syncFrequency: 'realtime',
            folders: ['Inbox', 'Sent'],
            excludedFolders: ['Spam', 'Trash'],
            lastSync: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
        },
        slack: {
            syncFrequency: 'realtime',
            channels: 'all',
            lastSync: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
        },
        discord: {
            syncFrequency: 'realtime',
            servers: 3,
            lastSync: new Date(Date.now() - 1 * 60 * 1000).toISOString(),
        },
    },
    notifications: {
        commitmentReminders: true,
        reminderTiming: 24, // hours before
        followUpSuggestions: true,
        followUpAfter: 3, // days
        reconnectionPrompts: true,
        reconnectionAfter: 30, // days
        deliveryChannels: {
            inApp: true,
            email: false,
            push: false,
        },
    },
    privacy: {
        dataRetention: 'indefinitely',
        autoDelete: 'never',
        aiProcessing: {
            entityExtraction: true,
            summaryGeneration: true,
            commitmentTracking: true,
            dataSharing: false,
        },
    },
    aiPreferences: {
        microSummaries: true,
        threadSummaries: true,
        threadSummaryThreshold: 3,
        dailySummaries: true,
        dailySummaryTime: '18:00',
        defaultSearchMode: 'hybrid',
        resultsPerPage: 20,
    },
};

// ============================================================================
// API Documentation Data (Section 4.11.10)
// ============================================================================
export const API_ENDPOINTS = [
    {
        category: 'Authentication',
        endpoints: [
            { method: 'POST', path: '/api/v1/auth/login', description: 'Authenticate user' },
            { method: 'POST', path: '/api/v1/auth/refresh', description: 'Refresh access token' },
        ],
    },
    {
        category: 'Messages',
        endpoints: [
            { method: 'GET', path: '/api/v1/messages', description: 'List all messages' },
            { method: 'GET', path: '/api/v1/messages/{id}', description: 'Get message by ID' },
        ],
    },
    {
        category: 'Search',
        endpoints: [
            {
                method: 'POST',
                path: '/api/v1/search',
                description: 'Execute hybrid search combining lexical and semantic approaches',
                requestBody: {
                    query: 'string (required, 1-500 chars)',
                    filters: {
                        platforms: '["string"]',
                        after: 'datetime (ISO 8601)',
                        before: 'datetime (ISO 8601)',
                        sender: 'string',
                    },
                    limit: 'integer (1-100, default: 20)',
                },
                responseBody: {
                    results: [
                        {
                            message_id: 'string',
                            platform: 'string',
                            sender: 'string',
                            content_preview: 'string',
                            highlighted: 'string',
                            relevance_score: 'number (0-1)',
                            timestamp: 'datetime',
                        },
                    ],
                    total_count: 'integer',
                },
            },
        ],
    },
    {
        category: 'Contacts',
        endpoints: [
            { method: 'GET', path: '/api/v1/contacts', description: 'List all contacts' },
            { method: 'GET', path: '/api/v1/contacts/{id}', description: 'Get contact by ID' },
        ],
    },
    {
        category: 'Commitments',
        endpoints: [
            { method: 'GET', path: '/api/v1/commitments', description: 'List all commitments' },
            { method: 'PATCH', path: '/api/v1/commitments/{id}', description: 'Update commitment status' },
        ],
    },
];
