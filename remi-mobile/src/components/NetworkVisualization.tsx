/**
 * NetworkVisualization Component
 * 
 * Displays contact relationship mapping with mutual connections and network analysis
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
  PanGestureHandler,
  PinchGestureHandler,
  State,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import Svg, { Circle, Line, Text as SvgText, G } from 'react-native-svg';
import { useTheme } from '../hooks/useTheme';
import { UnifiedContact, NetworkData, MutualContact } from '../types';

interface NetworkVisualizationProps {
  contact: UnifiedContact;
  networkData: NetworkData;
  onContactPress?: (contactId: string) => void;
  onRefresh?: () => void;
}

interface NetworkNode {
  id: string;
  label: string;
  type: 'user' | 'main_contact' | 'mutual_contact';
  x: number;
  y: number;
  radius: number;
  color: string;
}

interface NetworkEdge {
  from: string;
  to: string;
  weight: number;
  color: string;
  strokeWidth: number;
}

export const NetworkVisualization: React.FC<NetworkVisualizationProps> = ({
  contact,
  networkData,
  onContactPress,
  onRefresh,
}) => {
  const { theme } = useTheme();
  const [scale, setScale] = useState(1);
  const [translateX, setTranslateX] = useState(0);
  const [translateY, setTranslateY] = useState(0);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  
  const screenWidth = Dimensions.get('window').width;
  const screenHeight = 300;
  const svgWidth = screenWidth - 32;
  const svgHeight = screenHeight;

  // Calculate node positions using a simple force-directed layout
  const calculateNodePositions = (): { nodes: NetworkNode[]; edges: NetworkEdge[] } => {
    if (!networkData.network_graph) {
      return { nodes: [], edges: [] };
    }

    const { nodes: rawNodes, edges: rawEdges } = networkData.network_graph;
    const centerX = svgWidth / 2;
    const centerY = svgHeight / 2;
    
    const nodes: NetworkNode[] = rawNodes.map((node, index) => {
      let x, y, radius, color;
      
      if (node.type === 'user') {
        x = centerX;
        y = centerY;
        radius = 25;
        color = theme.colors.primary;
      } else if (node.type === 'main_contact') {
        x = centerX + 80;
        y = centerY;
        radius = 22;
        color = theme.colors.secondary;
      } else {
        // Arrange mutual contacts in a circle around the center
        const angle = (index - 2) * (2 * Math.PI) / (rawNodes.length - 2);
        const distance = 120;
        x = centerX + Math.cos(angle) * distance;
        y = centerY + Math.sin(angle) * distance;
        radius = 18;
        color = theme.colors.warning;
      }
      
      return {
        id: node.id,
        label: node.label,
        type: node.type,
        x,
        y,
        radius,
        color,
      };
    });

    const edges: NetworkEdge[] = rawEdges.map((edge) => {
      const fromNode = nodes.find(n => n.id === edge.from);
      const toNode = nodes.find(n => n.id === edge.to);
      
      if (!fromNode || !toNode) {
        return null;
      }

      return {
        from: edge.from,
        to: edge.to,
        weight: edge.weight,
        color: theme.colors.border,
        strokeWidth: Math.max(1, edge.weight * 3),
      };
    }).filter(Boolean) as NetworkEdge[];

    return { nodes, edges };
  };

  const { nodes, edges } = calculateNodePositions();

  const handleNodePress = (nodeId: string) => {
    setSelectedNode(nodeId === selectedNode ? null : nodeId);
    
    if (nodeId !== 'user' && nodeId !== contact.id && onContactPress) {
      onContactPress(nodeId);
    }
  };

  const getNodeTypeIcon = (type: string) => {
    switch (type) {
      case 'user': return 'person';
      case 'main_contact': return 'person-circle';
      case 'mutual_contact': return 'people';
      default: return 'person';
    }
  };

  const renderNetworkGraph = () => {
    if (nodes.length === 0) {
      return (
        <View style={[styles.emptyGraph, { backgroundColor: theme.colors.surface }]}>
          <Icon name="people-outline" size={48} color={theme.colors.textSecondary} />
          <Text style={[styles.emptyGraphText, { color: theme.colors.textSecondary }]}>
            No network connections found
          </Text>
        </View>
      );
    }

    return (
      <View style={[styles.graphContainer, { backgroundColor: theme.colors.surface }]}>
        <Svg width={svgWidth} height={svgHeight}>
          <G scale={scale} translateX={translateX} translateY={translateY}>
            {/* Render edges first (behind nodes) */}
            {edges.map((edge, index) => {
              const fromNode = nodes.find(n => n.id === edge.from);
              const toNode = nodes.find(n => n.id === edge.to);
              
              if (!fromNode || !toNode) return null;
              
              return (
                <Line
                  key={`edge-${index}`}
                  x1={fromNode.x}
                  y1={fromNode.y}
                  x2={toNode.x}
                  y2={toNode.y}
                  stroke={edge.color}
                  strokeWidth={edge.strokeWidth}
                  opacity={0.6}
                />
              );
            })}
            
            {/* Render nodes */}
            {nodes.map((node) => (
              <G key={node.id}>
                <Circle
                  cx={node.x}
                  cy={node.y}
                  r={node.radius}
                  fill={node.color}
                  stroke={selectedNode === node.id ? theme.colors.text : 'transparent'}
                  strokeWidth={selectedNode === node.id ? 2 : 0}
                  opacity={0.8}
                  onPress={() => handleNodePress(node.id)}
                />
                
                {/* Node label */}
                <SvgText
                  x={node.x}
                  y={node.y + node.radius + 15}
                  fontSize="12"
                  fill={theme.colors.text}
                  textAnchor="middle"
                  onPress={() => handleNodePress(node.id)}
                >
                  {node.label.length > 10 ? node.label.substring(0, 10) + '...' : node.label}
                </SvgText>
              </G>
            ))}
          </G>
        </Svg>
        
        {/* Legend */}
        <View style={styles.legend}>
          <View style={styles.legendItem}>
            <View style={[styles.legendColor, { backgroundColor: theme.colors.primary }]} />
            <Text style={[styles.legendText, { color: theme.colors.textSecondary }]}>You</Text>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.legendColor, { backgroundColor: theme.colors.secondary }]} />
            <Text style={[styles.legendText, { color: theme.colors.textSecondary }]}>
              {contact.primaryName}
            </Text>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.legendColor, { backgroundColor: theme.colors.warning }]} />
            <Text style={[styles.legendText, { color: theme.colors.textSecondary }]}>
              Mutual Contacts
            </Text>
          </View>
        </View>
      </View>
    );
  };

  const renderNetworkStats = () => {
    if (!networkData.network_stats) return null;

    const stats = networkData.network_stats;

    return (
      <View style={[styles.statsContainer, { backgroundColor: theme.colors.surface }]}>
        <Text style={[styles.statsTitle, { color: theme.colors.text }]}>
          Network Statistics
        </Text>
        
        <View style={styles.statsGrid}>
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: theme.colors.primary }]}>
              {stats.network_size}
            </Text>
            <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
              Mutual Contacts
            </Text>
          </View>
          
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: theme.colors.primary }]}>
              {stats.avg_shared_threads}
            </Text>
            <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
              Avg Shared Threads
            </Text>
          </View>
          
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: theme.colors.primary }]}>
              {Math.round(stats.network_strength_score * 100)}%
            </Text>
            <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
              Network Strength
            </Text>
          </View>
        </View>
      </View>
    );
  };

  const renderMutualContactsList = () => {
    if (!networkData.mutual_contacts_list || networkData.mutual_contacts_list.length === 0) {
      return null;
    }

    return (
      <View style={[styles.contactsContainer, { backgroundColor: theme.colors.surface }]}>
        <Text style={[styles.contactsTitle, { color: theme.colors.text }]}>
          Mutual Connections
        </Text>
        
        <ScrollView style={styles.contactsList} showsVerticalScrollIndicator={false}>
          {networkData.mutual_contacts_list.slice(0, 10).map((mutualContact, index) => (
            <TouchableOpacity
              key={index}
              style={[styles.contactItem, { borderColor: theme.colors.border }]}
              onPress={() => {
                if (mutualContact.unified_contact && onContactPress) {
                  onContactPress(mutualContact.unified_contact.id);
                }
              }}
            >
              <View style={styles.contactInfo}>
                <View style={[styles.contactAvatar, { backgroundColor: theme.colors.primary + '20' }]}>
                  <Icon name="person" size={16} color={theme.colors.primary} />
                </View>
                
                <View style={styles.contactDetails}>
                  <Text style={[styles.contactName, { color: theme.colors.text }]}>
                    {mutualContact.unified_contact?.primary_name || mutualContact.display_name}
                  </Text>
                  <Text style={[styles.contactPlatform, { color: theme.colors.textSecondary }]}>
                    {mutualContact.platform} • {mutualContact.shared_threads} shared threads
                  </Text>
                </View>
              </View>
              
              <View style={styles.contactMeta}>
                <Text style={[styles.contactMessages, { color: theme.colors.textSecondary }]}>
                  {mutualContact.shared_messages} messages
                </Text>
                {mutualContact.unified_contact && (
                  <View style={styles.strengthIndicator}>
                    <View
                      style={[
                        styles.strengthBar,
                        {
                          backgroundColor: theme.colors.primary,
                          width: `${(mutualContact.unified_contact.relationship_strength || 0) * 100}%`,
                        },
                      ]}
                    />
                  </View>
                )}
              </View>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>
    );
  };

  return (
    <ScrollView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <View style={[styles.header, { backgroundColor: theme.colors.surface }]}>
        <View style={styles.headerContent}>
          <Text style={[styles.title, { color: theme.colors.text }]}>
            Network Connections
          </Text>
          <Text style={[styles.subtitle, { color: theme.colors.textSecondary }]}>
            Mutual connections with {contact.primaryName}
          </Text>
        </View>
        
        {onRefresh && (
          <TouchableOpacity
            style={[styles.refreshButton, { borderColor: theme.colors.border }]}
            onPress={onRefresh}
          >
            <Icon name="refresh" size={20} color={theme.colors.primary} />
          </TouchableOpacity>
        )}
      </View>

      {renderNetworkGraph()}
      {renderNetworkStats()}
      {renderMutualContactsList()}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    marginBottom: 8,
  },
  headerContent: {
    flex: 1,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
  },
  refreshButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  graphContainer: {
    margin: 16,
    borderRadius: 12,
    padding: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  emptyGraph: {
    height: 200,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
    margin: 16,
    padding: 32,
  },
  emptyGraphText: {
    marginTop: 8,
    fontSize: 16,
    textAlign: 'center',
  },
  legend: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  legendColor: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  legendText: {
    fontSize: 12,
  },
  statsContainer: {
    margin: 16,
    borderRadius: 12,
    padding: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  statsTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 16,
  },
  statsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    textAlign: 'center',
  },
  contactsContainer: {
    margin: 16,
    borderRadius: 12,
    padding: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  contactsTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 16,
  },
  contactsList: {
    maxHeight: 300,
  },
  contactItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  contactInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  contactAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  contactDetails: {
    flex: 1,
  },
  contactName: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 2,
  },
  contactPlatform: {
    fontSize: 12,
  },
  contactMeta: {
    alignItems: 'flex-end',
  },
  contactMessages: {
    fontSize: 12,
    marginBottom: 4,
  },
  strengthIndicator: {
    width: 40,
    height: 4,
    backgroundColor: '#f0f0f0',
    borderRadius: 2,
    overflow: 'hidden',
  },
  strengthBar: {
    height: '100%',
    borderRadius: 2,
  },
});