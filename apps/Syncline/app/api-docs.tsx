/**
 * Interactive API Documentation (Section 4.11.10, Figure 4.15)
 * 
 * Swagger/OpenAPI style interactive documentation for MESH API.
 * Shows navigation, endpoint details, request/response schemas, and "Try It Out".
 */

import React, { useState } from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../src/theme';
import { Card } from '../components/Card/Card';
import { API_ENDPOINTS } from '../src/data/dummyData';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

const METHOD_COLORS: Record<HttpMethod, string> = {
    GET: '#10B981',
    POST: '#3B82F6',
    PUT: '#F59E0B',
    PATCH: '#8B5CF6',
    DELETE: '#EF4444',
};

export default function APIDocsScreen() {
    const [expandedEndpoint, setExpandedEndpoint] = useState<string | null>('/api/v1/search');
    const [expandedCategory, setExpandedCategory] = useState<string>('Search');

    const renderMethodBadge = (method: HttpMethod) => (
        <View style={[styles.methodBadge, { backgroundColor: METHOD_COLORS[method] }]}>
            <Text style={styles.methodText}>{method}</Text>
        </View>
    );

    return (
        <View style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <View style={styles.headerTop}>
                    <View style={styles.logoContainer}>
                        <Ionicons name="code-working" size={24} color="white" />
                    </View>
                    <View style={styles.headerInfo}>
                        <Text style={styles.headerTitle}>MESH API</Text>
                        <Text style={styles.headerVersion}>v1.0.0 | OpenAPI 3.0</Text>
                    </View>
                </View>
                <Text style={styles.headerDescription}>
                    RESTful API for accessing your unified communication data
                </Text>
            </View>

            <View style={styles.mainContent}>
                {/* Navigation Sidebar */}
                <View style={styles.sidebar}>
                    <Text style={styles.sidebarTitle}>Endpoints</Text>
                    <ScrollView showsVerticalScrollIndicator={false}>
                        {API_ENDPOINTS.map((category) => (
                            <View key={category.category}>
                                <TouchableOpacity
                                    style={styles.categoryHeader}
                                    onPress={() => setExpandedCategory(
                                        expandedCategory === category.category ? '' : category.category
                                    )}
                                >
                                    <Text style={[
                                        styles.categoryName,
                                        expandedCategory === category.category && styles.categoryNameActive
                                    ]}>
                                        {category.category}
                                    </Text>
                                    <Ionicons
                                        name={expandedCategory === category.category ? 'chevron-down' : 'chevron-forward'}
                                        size={14}
                                        color={theme.colors.textSecondary}
                                    />
                                </TouchableOpacity>

                                {expandedCategory === category.category && (
                                    <View style={styles.categoryEndpoints}>
                                        {category.endpoints.map((endpoint, idx) => (
                                            <TouchableOpacity
                                                key={idx}
                                                style={[
                                                    styles.endpointNavItem,
                                                    expandedEndpoint === endpoint.path && styles.endpointNavItemActive
                                                ]}
                                                onPress={() => setExpandedEndpoint(endpoint.path)}
                                            >
                                                <View style={[
                                                    styles.methodDot,
                                                    { backgroundColor: METHOD_COLORS[endpoint.method as HttpMethod] }
                                                ]} />
                                                <Text style={styles.endpointNavPath} numberOfLines={1}>
                                                    {endpoint.path.replace('/api/v1', '')}
                                                </Text>
                                            </TouchableOpacity>
                                        ))}
                                    </View>
                                )}
                            </View>
                        ))}
                    </ScrollView>
                </View>

                {/* Main Content Area */}
                <ScrollView style={styles.contentArea} showsVerticalScrollIndicator={false}>
                    {/* Find selected endpoint */}
                    {API_ENDPOINTS.map((category) => (
                        category.endpoints.map((endpoint, idx) => {
                            if (endpoint.path !== expandedEndpoint) return null;

                            return (
                                <View key={`${category.category}-${idx}`} style={styles.endpointDetail}>
                                    {/* Endpoint Header */}
                                    <View style={styles.endpointHeader}>
                                        {renderMethodBadge(endpoint.method as HttpMethod)}
                                        <Text style={styles.endpointPath}>{endpoint.path}</Text>
                                    </View>

                                    <Text style={styles.endpointDescription}>{endpoint.description}</Text>

                                    {/* Request Body (if POST) */}
                                    {endpoint.requestBody && (
                                        <Card style={styles.schemaCard}>
                                            <View style={styles.schemaHeader}>
                                                <Text style={styles.schemaTitle}>Request Body</Text>
                                                <Text style={styles.schemaType}>application/json</Text>
                                            </View>
                                            <View style={styles.codeBlock}>
                                                <Text style={styles.codeText}>
                                                    {`{`}
                                                </Text>
                                                {Object.entries(endpoint.requestBody).map(([key, value], i) => (
                                                    <View key={key} style={styles.codeLine}>
                                                        <Text style={styles.codeKey}>  "{key}"</Text>
                                                        <Text style={styles.codeColon}>: </Text>
                                                        {typeof value === 'object' ? (
                                                            <>
                                                                <Text style={styles.codeText}>{`{`}</Text>
                                                                {Object.entries(value as object).map(([subKey, subValue]) => (
                                                                    <View key={subKey} style={styles.codeLineSub}>
                                                                        <Text style={styles.codeKey}>    "{subKey}"</Text>
                                                                        <Text style={styles.codeColon}>: </Text>
                                                                        <Text style={styles.codeValue}>"{subValue}"</Text>
                                                                    </View>
                                                                ))}
                                                                <Text style={styles.codeText}>  {`}`}</Text>
                                                            </>
                                                        ) : (
                                                            <Text style={styles.codeValue}>"{value}"</Text>
                                                        )}
                                                    </View>
                                                ))}
                                                <Text style={styles.codeText}>{`}`}</Text>
                                            </View>
                                        </Card>
                                    )}

                                    {/* Response Body */}
                                    {endpoint.responseBody && (
                                        <Card style={styles.schemaCard}>
                                            <View style={styles.schemaHeader}>
                                                <Text style={styles.schemaTitle}>Response Body</Text>
                                                <View style={styles.successBadge}>
                                                    <Text style={styles.successText}>200 OK</Text>
                                                </View>
                                            </View>
                                            <View style={styles.codeBlock}>
                                                <Text style={styles.codeText}>{`{`}</Text>
                                                {Object.entries(endpoint.responseBody).map(([key, value]) => (
                                                    <View key={key} style={styles.codeLine}>
                                                        <Text style={styles.codeKey}>  "{key}"</Text>
                                                        <Text style={styles.codeColon}>: </Text>
                                                        {Array.isArray(value) ? (
                                                            <>
                                                                <Text style={styles.codeText}>[</Text>
                                                                {value.map((item, i) => (
                                                                    <View key={i}>
                                                                        <Text style={styles.codeText}>    {`{`}</Text>
                                                                        {Object.entries(item).map(([subKey, subValue]) => (
                                                                            <View key={subKey} style={styles.codeLineSub}>
                                                                                <Text style={styles.codeKey}>      "{subKey}"</Text>
                                                                                <Text style={styles.codeColon}>: </Text>
                                                                                <Text style={styles.codeValue}>"{subValue}"</Text>
                                                                            </View>
                                                                        ))}
                                                                        <Text style={styles.codeText}>    {`}`}</Text>
                                                                    </View>
                                                                ))}
                                                                <Text style={styles.codeText}>  ]</Text>
                                                            </>
                                                        ) : (
                                                            <Text style={styles.codeValue}>"{value}"</Text>
                                                        )}
                                                    </View>
                                                ))}
                                                <Text style={styles.codeText}>{`}`}</Text>
                                            </View>
                                        </Card>
                                    )}

                                    {/* Try It Out Section */}
                                    <Card style={styles.tryItCard}>
                                        <View style={styles.tryItHeader}>
                                            <Ionicons name="play-circle" size={20} color={theme.colors.primary} />
                                            <Text style={styles.tryItTitle}>Try It Out</Text>
                                        </View>
                                        <TouchableOpacity style={styles.executeButton}>
                                            <Text style={styles.executeButtonText}>Execute</Text>
                                        </TouchableOpacity>

                                        {/* Sample Response */}
                                        <View style={styles.responseSection}>
                                            <Text style={styles.responseLabel}>Sample Response</Text>
                                            <View style={styles.responseMeta}>
                                                <View style={styles.responseStatus}>
                                                    <View style={styles.statusDot} />
                                                    <Text style={styles.statusCode}>200</Text>
                                                </View>
                                                <Text style={styles.responseTime}>142ms</Text>
                                            </View>
                                            <View style={styles.responseCodeBlock}>
                                                <Text style={styles.responseCode}>
                                                    {`{
  "results": [
    {
      "message_id": "msg_abc123",
      "platform": "slack",
      "sender": "You",
      "content_preview": "I'll have the budget...",
      "relevance_score": 0.94
    }
  ],
  "total_count": 3
}`}
                                                </Text>
                                            </View>
                                        </View>
                                    </Card>
                                </View>
                            );
                        })
                    ))}

                    <View style={{ height: 100 }} />
                </ScrollView>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    header: {
        backgroundColor: '#1F2937',
        padding: 20,
        paddingTop: 60,
    },
    headerTop: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
    },
    logoContainer: {
        width: 44,
        height: 44,
        borderRadius: 12,
        backgroundColor: theme.colors.primary,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 12,
    },
    headerInfo: {
        flex: 1,
    },
    headerTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: 'white',
    },
    headerVersion: {
        fontSize: 13,
        color: 'rgba(255,255,255,0.6)',
        marginTop: 2,
    },
    headerDescription: {
        fontSize: 14,
        color: 'rgba(255,255,255,0.8)',
    },
    mainContent: {
        flex: 1,
        flexDirection: 'row',
    },
    sidebar: {
        width: 200,
        backgroundColor: theme.colors.background,
        borderRightWidth: 1,
        borderRightColor: theme.colors.border,
        padding: 16,
    },
    sidebarTitle: {
        fontSize: 11,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        textTransform: 'uppercase',
        marginBottom: 16,
    },
    categoryHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 10,
    },
    categoryName: {
        fontSize: 14,
        fontWeight: '500',
        color: theme.colors.text,
    },
    categoryNameActive: {
        color: theme.colors.primary,
    },
    categoryEndpoints: {
        marginLeft: 8,
        marginBottom: 8,
    },
    endpointNavItem: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 8,
        paddingHorizontal: 8,
        borderRadius: 6,
        gap: 8,
    },
    endpointNavItemActive: {
        backgroundColor: theme.colors.primaryLighter,
    },
    methodDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
    },
    endpointNavPath: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        flex: 1,
    },
    contentArea: {
        flex: 1,
        padding: 20,
    },
    endpointDetail: {},
    endpointHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        marginBottom: 12,
    },
    methodBadge: {
        paddingHorizontal: 10,
        paddingVertical: 5,
        borderRadius: 6,
    },
    methodText: {
        fontSize: 12,
        fontWeight: 'bold',
        color: 'white',
    },
    endpointPath: {
        fontSize: 18,
        fontWeight: '600',
        color: theme.colors.text,
        fontFamily: 'monospace',
    },
    endpointDescription: {
        fontSize: 15,
        color: theme.colors.textSecondary,
        marginBottom: 20,
    },
    schemaCard: {
        marginBottom: 16,
        padding: 0,
        backgroundColor: theme.colors.background,
        overflow: 'hidden',
    },
    schemaHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 14,
        backgroundColor: theme.colors.surface,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    schemaTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.text,
    },
    schemaType: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    successBadge: {
        backgroundColor: '#D1FAE5',
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 4,
    },
    successText: {
        fontSize: 11,
        color: '#10B981',
        fontWeight: '600',
    },
    codeBlock: {
        padding: 14,
        backgroundColor: '#1F2937',
    },
    codeText: {
        fontFamily: 'monospace',
        fontSize: 12,
        color: '#E5E7EB',
    },
    codeLine: {
        marginVertical: 1,
    },
    codeLineSub: {
        marginLeft: 8,
    },
    codeKey: {
        fontFamily: 'monospace',
        fontSize: 12,
        color: '#93C5FD',
    },
    codeColon: {
        fontFamily: 'monospace',
        fontSize: 12,
        color: '#E5E7EB',
    },
    codeValue: {
        fontFamily: 'monospace',
        fontSize: 12,
        color: '#86EFAC',
    },
    tryItCard: {
        padding: 16,
        backgroundColor: theme.colors.background,
    },
    tryItHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        marginBottom: 16,
    },
    tryItTitle: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.text,
    },
    executeButton: {
        backgroundColor: theme.colors.primary,
        paddingVertical: 12,
        borderRadius: 8,
        alignItems: 'center',
        marginBottom: 16,
    },
    executeButtonText: {
        fontSize: 14,
        fontWeight: '600',
        color: 'white',
    },
    responseSection: {
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
        paddingTop: 16,
    },
    responseLabel: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        textTransform: 'uppercase',
        marginBottom: 8,
    },
    responseMeta: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 16,
        marginBottom: 12,
    },
    responseStatus: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
    },
    statusDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: '#10B981',
    },
    statusCode: {
        fontSize: 13,
        fontWeight: '600',
        color: '#10B981',
    },
    responseTime: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    responseCodeBlock: {
        backgroundColor: '#1F2937',
        borderRadius: 8,
        padding: 12,
    },
    responseCode: {
        fontFamily: 'monospace',
        fontSize: 11,
        color: '#E5E7EB',
        lineHeight: 16,
    },
});
