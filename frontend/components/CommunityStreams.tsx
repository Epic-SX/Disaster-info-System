"use client";

import { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { YouTubePlayerHybrid } from './YouTubePlayer';
import { apiClient, API_ENDPOINTS, createWebSocket, WS_ENDPOINTS } from '@/lib/api-config';
import Image from 'next/image';
import { 
  Users, 
  MessageSquare, 
  AlertTriangle,
  Clock,
  Volume2,
  VolumeX,
  RefreshCw,
  Info,
  Shield,
  Heart,
  Radio,
  ChevronDown,
  X,
  MoreVertical,
  Send,
  Smile,
  Flame,
  Check,
  CheckCheck,
  Menu,
  Search,
  Edit,
  Pin
} from 'lucide-react';

interface CommunityStream {
  id: string;
  videoId: string;
  title: string;
  channel: string;
  description: string;
  category: 'disaster_info' | 'community_support' | 'safety_guidance' | 'local_updates';
  isLive: boolean;
  viewerCount?: number;
  thumbnail?: string;
  link?: string;
  verified_channel?: boolean;
  priority?: 'high' | 'medium' | 'low';
}

interface BackendLiveStream {
  video_id: string;
  title: string;
  channel: string;
  description?: string;
  video_type?: string;
  duration?: string;
  thumbnail?: string;
  link?: string;
  verified_channel?: boolean;
}

interface ChatMessage {
  id: string;
  message_id: string;
  author: string;
  message: string;
  timestamp: string;
  sentiment_score?: number;
  category?: string;
  platform?: string;
  message_type?: 'text' | 'super_chat' | 'member';
  amount_value?: number;
  currency?: string;
  author_badge?: string;
  author_image?: string;
}

interface PinnedMessage {
  id: string;
  text: string;
  type: 'sponsor' | 'announcement' | 'important';
}

interface ChannelInfo {
  channel_id: string;
  name: string;
  url: string;
  thumbnail: string;
  subscriber_count: string;
  verified: boolean;
  description?: string;
}

// Default community-focused streams for disaster information
const DEFAULT_COMMUNITY_STREAMS: CommunityStream[] = [
  {
    id: 'nhk-disaster',
    videoId: 'jfKfPfyJRdk',
    title: 'NHK 災害・気象情報',
    channel: 'NHK',
    description: '災害時の最新情報と避難指示をお伝えします',
    category: 'disaster_info',
    isLive: true,
    priority: 'high'
  },
  {
    id: 'weather-community',
    videoId: 'Ch_ZqaUQhc8',
    title: 'ウェザーニュース コミュニティ情報',
    channel: 'Weather News',
    description: '地域の天気情報とコミュニティ向け災害情報',
    category: 'local_updates',
    isLive: true,
    priority: 'high'
  }
];

export function CommunityStreams() {
  const [selectedStream, setSelectedStream] = useState<string>(DEFAULT_COMMUNITY_STREAMS[0].videoId);
  const [communityStreams, setCommunityStreams] = useState<CommunityStream[]>(DEFAULT_COMMUNITY_STREAMS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [muted, setMuted] = useState(false);
  
  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState('');
  const [pinnedMessages, setPinnedMessages] = useState<PinnedMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [showChat, setShowChat] = useState(true);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [currentUser, setCurrentUser] = useState<string>('');
  // Track last message per channel for sidebar display
  const [lastMessagesByChannel, setLastMessagesByChannel] = useState<Record<string, string>>({});
  
  // Channel information state
  const [channelInfo, setChannelInfo] = useState<ChannelInfo | null>(null);
  const [channelLoading, setChannelLoading] = useState(false);
  
  // Telegram-style UI state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  
  // Keywords for highlighting (like おかゆ in the image)
  const highlightKeywords = ['おかゆ', '災害', '地震', '避難', '緊急', 'disaster', 'earthquake'];
  
  // Ref for chat messages container (for auto-scroll)
  const chatMessagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const emojiPickerRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatMessagesEndRef.current) {
      chatMessagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages]);

  // Close emoji picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        emojiPickerRef.current &&
        !emojiPickerRef.current.contains(event.target as Node) &&
        !(event.target as HTMLElement)?.closest('button[title="絵文字"]')
      ) {
        setShowEmojiPicker(false);
      }
    };

    if (showEmojiPicker) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showEmojiPicker]);

  // WebSocket connection for real-time community chat updates
  useEffect(() => {
    if (!showChat) {
      // Close WebSocket when chat is hidden
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    const connectWebSocket = () => {
      try {
        // Close existing connection if any
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }

        const ws = createWebSocket(WS_ENDPOINTS.main);
        if (!ws) {
          console.log('WebSocket not available for community chat, using polling');
          setChatError('');
          // Fallback to polling if WebSocket is not available
          return;
        }

        wsRef.current = ws;

        // Set connection timeout
        const connectionTimeout = setTimeout(() => {
          if (ws.readyState === WebSocket.CONNECTING) {
            console.log('Community chat WebSocket connection timeout');
            ws.close();
            setChatError('WebSocket接続タイムアウト。HTTPポーリングを使用します。');
          }
        }, 10000); // 10 second timeout

        ws.onopen = () => {
          clearTimeout(connectionTimeout);
          console.log('Community chat WebSocket connected');
          setChatError('');
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'community_message' && data.data) {
              const message = data.data;
              const messageChannelId = message.channel_id || message.platform;
              
              // Only add message if it's for the currently selected channel
              if (messageChannelId === selectedChatId) {
                setChatMessages(prev => {
                  // Avoid duplicates
                  const exists = prev.some(msg => msg.id === message.id);
                  if (exists) return prev;
                  return [...prev, message];
                });
              }
              
              // Update last message for this channel (for sidebar display)
              if (messageChannelId) {
                setLastMessagesByChannel(prev => ({
                  ...prev,
                  [messageChannelId]: message.message
                }));
              }
            }
          } catch (err) {
            console.error('Error parsing WebSocket message:', err);
          }
        };

        ws.onerror = (event) => {
          clearTimeout(connectionTimeout);
          // WebSocket error events don't provide detailed error info
          // This is a common, non-critical error that will auto-retry
          // Only log minimal information to avoid console spam
          try {
            const errorDetails: Record<string, string | number> = {};
            
            // Always include basic info
            errorDetails.eventType = event?.type || 'error';
            errorDetails.timestamp = new Date().toISOString();
            
            // Safely access WebSocket properties if available
            if (ws) {
              const state = ws.readyState;
              errorDetails.readyState = state;
              
              // Add human-readable state
              const stateMap: Record<number, string> = {
                [WebSocket.CONNECTING]: 'CONNECTING',
                [WebSocket.OPEN]: 'OPEN',
                [WebSocket.CLOSING]: 'CLOSING',
                [WebSocket.CLOSED]: 'CLOSED'
              };
              errorDetails.state = stateMap[state] || `UNKNOWN(${state})`;
              
              // Try to get URL
              try {
                if ('url' in ws && typeof ws.url === 'string' && ws.url) {
                  errorDetails.url = ws.url;
                }
              } catch {
                // URL not accessible
              }
            } else {
              errorDetails.note = 'WebSocket object unavailable';
            }
            
            // Log as warning (not error) since this is expected during connection attempts
            console.warn('Community chat WebSocket connection issue:', errorDetails);
          } catch (err) {
            // Minimal fallback logging
            console.warn('Community chat WebSocket connection issue. Will retry automatically.');
          }
          
          // Don't show error to user - WebSocket will auto-retry
        };

        ws.onclose = (event) => {
          clearTimeout(connectionTimeout);
          console.log('Community chat WebSocket disconnected', {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean
          });
          wsRef.current = null;
          
          // Only attempt to reconnect if it was an unexpected close
          // and chat is still visible and channel is still selected
          if (showChat && selectedChatId && event.code !== 1000) {
            // Attempt to reconnect after 3 seconds
            setTimeout(() => {
              if (showChat && selectedChatId) {
                connectWebSocket();
              }
            }, 3000);
          }
        };
      } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        setChatError('WebSocket接続に失敗しました。HTTPポーリングを使用します。');
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [showChat, selectedChatId]);

  const loadCommunityStreams = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      // Load community-focused disaster information streams from backend API
      // Using location=Japan and focusing on disaster/community keywords
      const response = await apiClient.get<{streams?: BackendLiveStream[], videos?: BackendLiveStream[]}>(
        `${API_ENDPOINTS.youtube.liveStreams}?location=Japan&query=災害情報,避難情報,コミュニティ`
      );
      
      // Convert backend format to frontend format
      const backendStreams = response.videos || response.streams || [];
      
      if (backendStreams.length > 0) {
        const convertedStreams: CommunityStream[] = backendStreams.map((stream, index) => ({
          id: stream.video_id || `community-stream-${index}`,
          videoId: stream.video_id,
          title: stream.title,
          channel: stream.channel,
          description: stream.description || '',
          category: determineCategoryFromContent(stream.title, stream.channel, stream.description || ''),
          isLive: stream.video_type === 'live',
          thumbnail: stream.thumbnail,
          link: stream.link,
          verified_channel: stream.verified_channel,
          priority: determinePriority(stream.title, stream.channel)
        }));
        
        // Sort by priority (high first) and merge with defaults
        const sortedStreams = [...DEFAULT_COMMUNITY_STREAMS, ...convertedStreams].sort((a, b) => {
          const priorityOrder = { high: 0, medium: 1, low: 2 };
          return priorityOrder[a.priority || 'low'] - priorityOrder[b.priority || 'low'];
        });
        
        setCommunityStreams(sortedStreams);
      } else {
        // Fallback to default streams if no results
        setCommunityStreams(DEFAULT_COMMUNITY_STREAMS);
      }
    } catch (err) {
      console.error('Error loading community streams:', err);
      setError('コミュニティ配信の読み込みに失敗しました');
      setCommunityStreams(DEFAULT_COMMUNITY_STREAMS);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load channel information from backend
  const loadChannelInfo = useCallback(async () => {
    setChannelLoading(true);
    try {
      // Search for the specific channel "ちいにいの隠家(アジト) ささき 齋藤隆文"
      // First try with query parameter to search for specific channel name
      const searchQueries = ['ちいにいの隠家', 'ささき', '齋藤隆文'];
      let targetChannel: ChannelInfo | null = null;
      
      // Try each search query
      for (const query of searchQueries) {
        try {
          const response = await apiClient.get<{channels?: ChannelInfo[], total_results?: number, query_filter?: string}>(
            `${API_ENDPOINTS.youtube.channels}?limit=20&query=${encodeURIComponent(query)}`
          );
          
          if (response.channels && response.channels.length > 0) {
            // Find the best match
            const match = response.channels.find(ch => 
              ch.name.includes('ちいにいの隠家') || 
              ch.name.includes('ささき') ||
              ch.name.includes('齋藤隆文')
            );
            
            if (match) {
              targetChannel = match;
              break;
            }
          }
        } catch (err) {
          console.warn(`Error searching for channel with query "${query}":`, err);
        }
      }
      
      // If not found with specific queries, try general search
      if (!targetChannel) {
        const response = await apiClient.get<{channels?: ChannelInfo[], total_results?: number}>(
          `${API_ENDPOINTS.youtube.channels}?limit=20`
        );
        
        if (response.channels && response.channels.length > 0) {
          // Try to find the specific channel by name
          targetChannel = response.channels.find(ch => 
            ch.name.includes('ちいにいの隠家') || 
            ch.name.includes('ささき') ||
            ch.name.includes('齋藤隆文')
          ) || response.channels[0];
        }
      }
      
      if (targetChannel) {
        setChannelInfo(targetChannel);
      } else {
        // Set default channel info if not found
        setChannelInfo({
          channel_id: 'default',
          name: 'ちいにいの隠家(アジト) ささき 齋藤隆文',
          url: '#',
          thumbnail: '',
          subscriber_count: '',
          verified: false,
          description: ''
        });
      }
    } catch (err) {
      console.error('Error loading channel info:', err);
      // Set default channel info if API fails
      setChannelInfo({
        channel_id: 'default',
        name: 'ちいにいの隠家(アジト) ささき 齋藤隆文',
        url: '#',
        thumbnail: '',
        subscriber_count: '',
        verified: false,
        description: ''
      });
    } finally {
      setChannelLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initialize with default streams on mount, then load community streams
    setCommunityStreams(DEFAULT_COMMUNITY_STREAMS);
    setSelectedStream(DEFAULT_COMMUNITY_STREAMS[0].videoId);
    setSelectedChatId(DEFAULT_COMMUNITY_STREAMS[0].videoId);
    
    // Load community streams from API after initial render
    loadCommunityStreams();
    
    // Load channel information
    loadChannelInfo();
    
    // Auto-refresh every 5 minutes to get latest community streams
    const refreshInterval = setInterval(() => {
      loadCommunityStreams();
    }, 5 * 60 * 1000); // 5 minutes

    return () => clearInterval(refreshInterval);
  }, [loadCommunityStreams, loadChannelInfo]);

  const determineCategoryFromContent = (
    title: string, 
    channel: string, 
    description: string
  ): CommunityStream['category'] => {
    const content = `${title} ${channel} ${description}`.toLowerCase();
    
    if (content.includes('避難') || content.includes('安全') || content.includes('ガイド') || content.includes('guidance')) {
      return 'safety_guidance';
    }
    if (content.includes('コミュニティ') || content.includes('支援') || content.includes('community') || content.includes('support')) {
      return 'community_support';
    }
    if (content.includes('地域') || content.includes('local') || content.includes('近隣')) {
      return 'local_updates';
    }
    return 'disaster_info';
  };

  const determinePriority = (title: string, channel: string): CommunityStream['priority'] => {
    const content = `${title} ${channel}`.toLowerCase();
    
    if (content.includes('緊急') || content.includes('emergency') || content.includes('nhk') || content.includes('気象庁')) {
      return 'high';
    }
    if (content.includes('重要') || content.includes('important')) {
      return 'medium';
    }
    return 'low';
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'disaster_info':
        return <AlertTriangle className="h-4 w-4" />;
      case 'community_support':
        return <Heart className="h-4 w-4" />;
      case 'safety_guidance':
        return <Shield className="h-4 w-4" />;
      case 'local_updates':
        return <Info className="h-4 w-4" />;
      default:
        return <Radio className="h-4 w-4" />;
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'disaster_info':
        return '災害情報';
      case 'community_support':
        return 'コミュニティ支援';
      case 'safety_guidance':
        return '安全ガイド';
      case 'local_updates':
        return '地域情報';
      default:
        return 'その他';
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'disaster_info':
        return 'bg-red-500';
      case 'community_support':
        return 'bg-pink-500';
      case 'safety_guidance':
        return 'bg-blue-500';
      case 'local_updates':
        return 'bg-green-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getPriorityColor = (priority?: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-600';
      case 'medium':
        return 'bg-yellow-600';
      case 'low':
        return 'bg-gray-600';
      default:
        return 'bg-gray-600';
    }
  };

  // Helper function to get YouTube thumbnail URL
  const getThumbnailUrl = (videoId: string, thumbnail?: string): string => {
    if (thumbnail) {
      return thumbnail;
    }
    return `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
  };

  // Load chat messages
  const loadChatMessages = useCallback(async () => {
    if (!selectedStream) return;
    
    setChatLoading(true);
    setChatError('');
    
    try {
      const messages = await apiClient.get<ChatMessage[]>(
        `${API_ENDPOINTS.chat.messages}?limit=50`
      );
      
      if (Array.isArray(messages)) {
        setChatMessages(messages);
        
        // Extract pinned messages (sponsors, announcements)
        const pinned: PinnedMessage[] = messages
          .filter(msg => msg.message_type === 'super_chat' || msg.category === 'announcement')
          .slice(0, 1)
          .map(msg => ({
            id: msg.id,
            text: msg.message_type === 'super_chat' ? `株式会社ティーファイブプロジェクト` : msg.message,
            type: msg.message_type === 'super_chat' ? 'sponsor' : 'announcement'
          }));
        setPinnedMessages(pinned);
      }
    } catch (err) {
      console.error('Error loading chat messages:', err);
      setChatError('チャットの読み込みに失敗しました');
      // Use mock data for development
      setChatMessages([
        {
          id: '1',
          message_id: '1',
          author: 'ちいにいの隠家(アジト)',
          message: 'おかゆない',
          timestamp: new Date().toISOString(),
          message_type: 'text',
          author_badge: 'Y'
        },
        {
          id: '2',
          message_id: '2',
          author: 'indigowalz',
          message: '久米島は昨日もこんなんだよ',
          timestamp: new Date().toISOString(),
          message_type: 'text'
        },
        {
          id: '3',
          message_id: '3',
          author: 'リーリエ',
          message: '久米島あばれてるw',
          timestamp: new Date().toISOString(),
          message_type: 'text'
        },
        {
          id: '4',
          message_id: '4',
          author: 'GREEN NIKI@みどりニキ',
          message: '沖縄の波形お祭りやん',
          timestamp: new Date().toISOString(),
          message_type: 'text'
        },
        {
          id: '5',
          message_id: '5',
          author: 'ファー',
          message: '地震が武者震いしてるな',
          timestamp: new Date().toISOString(),
          message_type: 'text'
        }
      ]);
    } finally {
      setChatLoading(false);
    }
  }, [selectedStream]);

  // Initialize current user from localStorage or generate one
  useEffect(() => {
    const storedUser = localStorage.getItem('community_chat_username');
    if (storedUser) {
      setCurrentUser(storedUser);
    } else {
      // Generate a random username
      const randomUser = `User${Math.floor(Math.random() * 10000)}`;
      setCurrentUser(randomUser);
      localStorage.setItem('community_chat_username', randomUser);
    }
  }, []);

  // Load community chat messages for the selected channel/server
  const loadCommunityChatMessages = useCallback(async () => {
    if (!showChat) return;
    
    setChatLoading(true);
    setChatError('');
    
    try {
      // Build URL with optional channel_id
      let url = `${API_ENDPOINTS.community.chat.messages}?limit=50`;
      if (selectedChatId) {
        url += `&channel_id=${encodeURIComponent(selectedChatId)}`;
      }
      
      const messages = await apiClient.get<ChatMessage[]>(url);
      
      if (Array.isArray(messages)) {
        setChatMessages(messages);
        
        // Update last message for this channel
        if (messages.length > 0 && selectedChatId) {
          const lastMsg = messages[messages.length - 1];
          setLastMessagesByChannel(prev => ({
            ...prev,
            [selectedChatId]: lastMsg.message
          }));
        }
      }
    } catch (err) {
      console.error('Error loading community chat messages:', err);
      setChatError('チャットの読み込みに失敗しました');
    } finally {
      setChatLoading(false);
    }
  }, [showChat, selectedChatId]);

  // Send community chat message to the selected channel/server
  const sendCommunityMessage = useCallback(async () => {
    if (!chatInput.trim() || sendingMessage || !currentUser || !selectedChatId) return;
    
    setSendingMessage(true);
    
    try {
      await apiClient.post(
        API_ENDPOINTS.community.chat.messages,
        {
          author: currentUser,
          message: chatInput.trim(),
          message_type: 'text',
          channel_id: selectedChatId
        }
      );
      
      // Clear input
      setChatInput('');
      
      // Reload messages after a short delay
      setTimeout(() => {
        loadCommunityChatMessages();
      }, 500);
    } catch (err) {
      console.error('Error sending message:', err);
      setChatError('メッセージの送信に失敗しました');
    } finally {
      setSendingMessage(false);
    }
  }, [chatInput, sendingMessage, currentUser, selectedChatId, loadCommunityChatMessages]);

  // Handle Enter key to send message
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendCommunityMessage();
    }
  };

  // Auto-refresh chat messages when channel changes or chat is shown
  useEffect(() => {
    if (showChat && selectedChatId) {
      loadCommunityChatMessages();
      const chatInterval = setInterval(() => {
        loadCommunityChatMessages();
      }, 3000); // Refresh every 3 seconds
      
      return () => clearInterval(chatInterval);
    }
  }, [showChat, selectedChatId, loadCommunityChatMessages]);

  // Highlight keywords in message text
  const highlightKeywordsInText = (text: string) => {
    let highlightedText = text;
    highlightKeywords.forEach(keyword => {
      const regex = new RegExp(`(${keyword})`, 'gi');
      highlightedText = highlightedText.replace(regex, '<mark class="bg-yellow-400/30 px-1 rounded">$1</mark>');
    });
    return highlightedText;
  };

  // Get user avatar color based on username (Discord-style colors)
  const getUserAvatarColor = (username: string): string => {
    const colors = [
      'bg-[#5865F2]', 'bg-[#57F287]', 'bg-[#FEE75C]', 'bg-[#EB459E]',
      'bg-[#ED4245]', 'bg-[#1ABC9C]', 'bg-[#3498DB]', 'bg-[#9B59B6]',
      'bg-[#E67E22]', 'bg-[#E74C3C]'
    ];
    const index = username.charCodeAt(0) % colors.length;
    return colors[index];
  };

  // Group consecutive messages from the same user (Discord-style)
  const groupMessages = (messages: ChatMessage[]): Array<ChatMessage & { showAvatar?: boolean; showTimestamp?: boolean }> => {
    if (messages.length === 0) return [];
    
    const grouped: Array<ChatMessage & { showAvatar?: boolean; showTimestamp?: boolean }> = [];
    const TIME_THRESHOLD = 5 * 60 * 1000; // 5 minutes
    
    for (let i = 0; i < messages.length; i++) {
      const msg = messages[i];
      const prevMsg = i > 0 ? messages[i - 1] : null;
      const nextMsg = i < messages.length - 1 ? messages[i + 1] : null;
      
      const msgTime = new Date(msg.timestamp).getTime();
      const prevTime = prevMsg ? new Date(prevMsg.timestamp).getTime() : 0;
      const nextTime = nextMsg ? new Date(nextMsg.timestamp).getTime() : 0;
      
      // Show avatar if:
      // - First message
      // - Different author than previous
      // - More than 5 minutes since previous message
      const showAvatar = !prevMsg || 
                        prevMsg.author !== msg.author || 
                        (msgTime - prevTime) > TIME_THRESHOLD;
      
      // Show timestamp if:
      // - Last message
      // - Different author than next
      // - More than 5 minutes before next message
      const showTimestamp = !nextMsg || 
                           nextMsg.author !== msg.author || 
                           (nextTime - msgTime) > TIME_THRESHOLD;
      
      grouped.push({ ...msg, showAvatar, showTimestamp });
    }
    
    return grouped;
  };

  // Get badge color based on badge type
  const getBadgeColor = (badge?: string): string => {
    switch (badge) {
      case 'Y': return 'bg-purple-500';
      case 'M': return 'bg-blue-500';
      case 'J': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  // Common emojis for the picker
  const commonEmojis = [
    '😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂', '🙂', '🙃',
    '😉', '😊', '😇', '🥰', '😍', '🤩', '😘', '😗', '😚', '😙',
    '😋', '😛', '😜', '🤪', '😝', '🤑', '🤗', '🤭', '🤫', '🤔',
    '🤐', '🤨', '😐', '😑', '😶', '😏', '😒', '🙄', '😬', '🤥',
    '😌', '😔', '😪', '🤤', '😴', '😷', '🤒', '🤕', '🤢', '🤮',
    '👍', '👎', '👌', '✌️', '🤞', '🤟', '🤘', '🤙', '👏', '🙌',
    '👐', '🤲', '🤝', '🙏', '✍️', '💪', '🦵', '🦶', '👂', '👃',
    '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔',
    '❣️', '💕', '💞', '💓', '💗', '💖', '💘', '💝', '💟', '☮️',
    '✅', '❌', '⭕', '❓', '❔', '❗', '❕', '💯', '🔅', '🔆',
    '🎉', '🎊', '🎈', '🎁', '🎀', '🏆', '🥇', '🥈', '🥉', '⚽',
    '🏀', '🏈', '⚾', '🎾', '🏐', '🏉', '🎱', '🏓', '🏸', '🥊',
    '🚀', '✈️', '🛫', '🛬', '🛩️', '💺', '🚁', '🚂', '🚃', '🚄',
    '🌍', '🌎', '🌏', '🌐', '🗺️', '🧭', '🏔️', '⛰️', '🌋', '🗻',
    '🏕️', '🏖️', '🏜️', '🏝️', '🏞️', '🏟️', '🏛️', '🏗️', '🧱', '🏘️',
    '🏚️', '🏠', '🏡', '🏢', '🏣', '🏤', '🏥', '🏦', '🏨', '🏩',
    '🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘', '🌙', '🌚',
    '🌛', '🌜', '🌝', '🌞', '⭐', '🌟', '💫', '✨', '☄️', '💥',
    '🔥', '💧', '🌊', '☀️', '🌤️', '⛅', '🌥️', '☁️', '🌦️', '🌧️',
    '⛈️', '🌩️', '⚡', '☔', '❄️', '☃️', '⛄', '🌨️', '💨', '🌪️',
    '🌈', '☂️', '☔', '☂️', '🌂', '⛱️', '🧊', '❄️', '☃️', '⛄'
  ];

  // Insert emoji into chat input
  const insertEmoji = (emoji: string) => {
    // Use a ref or find the input element
    const inputElement = document.querySelector('input[placeholder*="メッセージを送信"]') as HTMLInputElement;
    
    if (inputElement) {
      const start = inputElement.selectionStart || 0;
      const end = inputElement.selectionEnd || 0;
      const text = chatInput;
      const newText = text.substring(0, start) + emoji + text.substring(end);
      setChatInput(newText);
      
      // Focus back on input and set cursor position after state update
      setTimeout(() => {
        inputElement.focus();
        const newPosition = start + emoji.length;
        inputElement.setSelectionRange(newPosition, newPosition);
      }, 10);
    } else {
      // Fallback: just append emoji
      setChatInput(chatInput + emoji);
    }
    
    // Close picker after selecting emoji
    setShowEmojiPicker(false);
  };

  const selectedStreamData = communityStreams.find(stream => stream.videoId === selectedStream);

  // Filter chats based on search
  const filteredChats = communityStreams.filter(stream =>
    stream.channel.toLowerCase().includes(searchQuery.toLowerCase()) ||
    stream.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Get last message for each chat
  const getLastMessage = (streamId: string) => {
    return lastMessagesByChannel[streamId] || '';
  };

  // Format timestamp like Telegram
  const formatTelegramTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'now';
    if (diffMins < 60) return `${diffMins}m`;
    if (diffHours < 24) return `${diffHours}h`;
    if (diffDays < 7) return `${diffDays}d`;
    return date.toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' });
  };

  // Group messages by date
  const groupMessagesByDate = (messages: ChatMessage[]) => {
    const groups: { [key: string]: ChatMessage[] } = {};
    messages.forEach(msg => {
      const date = new Date(msg.timestamp).toLocaleDateString('ja-JP', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      });
      if (!groups[date]) groups[date] = [];
      groups[date].push(msg);
    });
    return groups;
  };

  return (
    <div className="h-[calc(100vh-200px)] flex bg-[#0E1621] rounded-lg overflow-hidden">
      {/* Left Sidebar - Telegram-style Chat List */}
      <div className="w-80 bg-[#212B36] border-r border-[#1E2329] flex flex-col">
        {/* Sidebar Header */}
        <div className="h-14 bg-[#1E2329] px-3 flex items-center gap-2 border-b border-[#1E2329]">
          <Button
            size="sm"
            variant="ghost"
            className="h-9 w-9 p-0 text-[#B1BBC3] hover:text-white hover:bg-[#2B2B2B] rounded transition-colors"
            title="メニュー"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#6B7B8C] pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search"
              className="w-full bg-[#2B2B2B] text-white text-sm px-9 py-2 rounded-lg border-0 focus:outline-none focus:ring-1 focus:ring-[#5288C1] placeholder-[#6B7B8C]"
            />
          </div>
        </div>

        {/* Chat List */}
        <div className="flex-1 overflow-y-auto">
          {filteredChats.map((stream) => {
            const lastMessage = getLastMessage(stream.videoId);
            const isSelected = selectedChatId === stream.videoId;
            
            return (
              <div
                key={stream.videoId}
                onClick={() => {
                  setSelectedChatId(stream.videoId);
                  setSelectedStream(stream.videoId);
                  setShowChat(true);
                }}
                className={`px-3 py-2.5 flex items-start gap-3 cursor-pointer hover:bg-[#2B2B2B] transition-colors ${
                  isSelected ? 'bg-[#2B2B2B] border-l-2 border-[#5288C1]' : ''
                }`}
              >
                {/* Avatar */}
                <div className="relative flex-shrink-0">
                  {stream.thumbnail ? (
                    <div className="w-12 h-12 rounded-full overflow-hidden">
                      <Image
                        src={stream.thumbnail}
                        alt={stream.channel}
                        width={48}
                        height={48}
                        className="object-cover"
                      />
                    </div>
                  ) : (
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#5288C1] to-[#6B46C1] flex items-center justify-center">
                      <span className="text-white text-lg font-semibold">
                        {stream.channel.charAt(0).toUpperCase()}
                      </span>
                    </div>
                  )}
                  {stream.isLive && (
                    <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 bg-red-500 rounded-full border-2 border-[#212B36]" />
                  )}
                </div>

                {/* Chat Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-0.5">
                    <h3 className={`text-sm font-medium truncate ${
                      isSelected ? 'text-white' : 'text-[#E4E6EB]'
                    }`}>
                      {stream.channel}
                    </h3>
                    <span className="text-[#6B7B8C] text-xs ml-2 flex-shrink-0">
                      {lastMessage ? formatTelegramTime(chatMessages[chatMessages.length - 1]?.timestamp || '') : ''}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {lastMessage ? (
                      <p className="text-[#6B7B8C] text-sm truncate flex-1">
                        {lastMessage}
                      </p>
                    ) : (
                      <p className="text-[#6B7B8C] text-sm italic">No messages</p>
                    )}
                    {stream.isLive && (
                      <Badge className="bg-red-500 text-white text-[10px] px-1.5 py-0 h-4 font-medium animate-pulse">
                        LIVE
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* New Message Button */}
        <div className="p-4 border-t border-[#1E2329]">
          <Button
            size="lg"
            className="w-full h-12 bg-[#5288C1] hover:bg-[#4775A8] text-white rounded-full shadow-lg"
            title="New Message"
          >
            <Edit className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {/* Right Pane - Telegram-style Chat */}
      <div className="flex-1 flex flex-col bg-[#0E1621] relative">
          {/* Telegram-style background pattern */}
          <div 
            className="absolute inset-0 opacity-5 pointer-events-none"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
            }}
          />

          {/* Chat Header - Only show when chat is selected */}
          {selectedChatId && (
            <>
          <div className="h-14 bg-[#1E2329] px-4 flex items-center justify-between border-b border-[#1E2329] z-10">
            <div className="flex items-center gap-3">
              {selectedStreamData?.thumbnail ? (
                <div className="relative w-10 h-10 rounded-full overflow-hidden">
                  <Image
                    src={selectedStreamData.thumbnail}
                    alt={selectedStreamData.channel}
                    width={40}
                    height={40}
                    className="object-cover"
                  />
                </div>
              ) : (
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#5288C1] to-[#6B46C1] flex items-center justify-center">
                  <span className="text-white text-sm font-semibold">
                    {selectedStreamData?.channel.charAt(0).toUpperCase() || 'C'}
                  </span>
                </div>
              )}
              <div>
                <h2 className="text-white text-base font-semibold">
                  {selectedStreamData?.channel || 'コミュニティチャット'}
                </h2>
                <p className="text-[#6B7B8C] text-xs">
                  {chatMessages.length} members, {Math.floor(Math.random() * 100)} online
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                className="h-9 w-9 p-0 text-[#B1BBC3] hover:text-white hover:bg-[#2B2B2B] rounded transition-colors"
                title="Pinned Messages"
              >
                <Pin className="h-5 w-5" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="h-9 w-9 p-0 text-[#B1BBC3] hover:text-white hover:bg-[#2B2B2B] rounded transition-colors"
                title="Search"
              >
                <Search className="h-5 w-5" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="h-9 w-9 p-0 text-[#B1BBC3] hover:text-white hover:bg-[#2B2B2B] rounded transition-colors"
                title="More"
              >
                <MoreVertical className="h-5 w-5" />
              </Button>
            </div>
          </div>

          {/* Pinned Message Banner - Telegram-style */}
          {pinnedMessages.length > 0 && (
            <div className="bg-[#1E2329] border-b border-[#1E2329] px-4 py-2.5 z-10">
              <div className="flex items-center gap-2 text-[#B1BBC3] text-sm">
                <Pin className="h-4 w-4" />
                <span className="truncate">We&apos;re going to be rolling out some gr...</span>
              </div>
            </div>
          )}

          {/* Chat Messages Feed - Telegram-style */}
          <div className="flex-1 overflow-y-auto px-4 py-4 min-h-0 relative z-0">
            {chatLoading && chatMessages.length === 0 ? (
              <div className="text-center py-12">
                <RefreshCw className="h-7 w-7 text-[#6B7B8C] mx-auto mb-3 animate-spin" />
                <p className="text-[#6B7B8C] text-sm font-medium">チャットを読み込み中...</p>
              </div>
            ) : chatMessages.length === 0 ? (
              <div className="text-center py-12">
                <MessageSquare className="h-8 w-8 text-[#6B7B8C] mx-auto mb-3" />
                <p className="text-[#6B7B8C] text-sm">チャットメッセージがありません</p>
              </div>
            ) : (
              <>
                {Object.entries(groupMessagesByDate(chatMessages)).map(([date, dateMessages]) => (
                  <div key={date}>
                    {/* Date Separator */}
                    <div className="flex items-center justify-center my-4">
                      <div className="bg-[#1E2329] px-3 py-1 rounded-full">
                        <span className="text-[#6B7B8C] text-xs font-medium">{date}</span>
                      </div>
                    </div>
                    
                    {/* Messages for this date */}
                    {dateMessages.map((msg) => {
                      const isCurrentUser = msg.author === currentUser;
                      const prevMsg = dateMessages[dateMessages.indexOf(msg) - 1];
                      const showAvatar = !prevMsg || prevMsg.author !== msg.author;
                      
                      return (
                        <div 
                          key={msg.id} 
                          className={`group flex items-start gap-2 mb-1 px-2 py-0.5 hover:bg-[#1E2329]/30 transition-colors rounded ${
                            isCurrentUser ? 'flex-row-reverse' : ''
                          }`}
                        >
                          {/* User Avatar */}
                          {showAvatar && (
                            <div className="flex-shrink-0">
                              {msg.author_image ? (
                                <div className="w-8 h-8 rounded-full overflow-hidden">
                                  <Image
                                    src={msg.author_image}
                                    alt={msg.author}
                                    width={32}
                                    height={32}
                                    className="object-cover"
                                  />
                                </div>
                              ) : (
                                <div className={`w-8 h-8 rounded-full ${getUserAvatarColor(msg.author)} flex items-center justify-center`}>
                                  <span className="text-white text-xs font-semibold">
                                    {msg.author.charAt(0).toUpperCase()}
                                  </span>
                                </div>
                              )}
                            </div>
                          )}
                          
                          {/* Message Content */}
                          <div className={`flex-1 min-w-0 ${isCurrentUser ? 'items-end' : 'items-start'} flex flex-col gap-0.5`}>
                            {/* Author name (only if avatar shown) */}
                            {showAvatar && !isCurrentUser && (
                              <span className="text-[#5288C1] text-xs font-semibold mb-0.5">
                                {msg.author}
                              </span>
                            )}
                            
                            {/* Message bubble - Telegram-style */}
                            <div className={`inline-flex items-end gap-1.5 max-w-[75%] ${isCurrentUser ? 'flex-row-reverse ml-auto' : 'flex-row'}`}>
                              <div className={`rounded-2xl px-3 py-1.5 break-words ${
                                isCurrentUser
                                  ? 'bg-[#5288C1] text-white rounded-tr-sm'
                                  : 'bg-[#1E2329] text-[#E4E6EB] rounded-tl-sm'
                              } shadow-sm`}>
                                <p 
                                  className={`text-sm break-words leading-relaxed ${
                                    isCurrentUser ? 'text-white' : 'text-[#E4E6EB]'
                                  }`}
                                  dangerouslySetInnerHTML={{ 
                                    __html: highlightKeywordsInText(msg.message) 
                                  }}
                                />
                              </div>
                              
                              {/* Timestamp */}
                              <span className={`text-[10px] ${
                                isCurrentUser ? 'text-[#6B7B8C]' : 'text-[#6B7B8C] opacity-0 group-hover:opacity-100'
                              } transition-opacity whitespace-nowrap`}>
                                {new Date(msg.timestamp).toLocaleTimeString('ja-JP', { 
                                  hour: '2-digit', 
                                  minute: '2-digit' 
                                })}
                              </span>
                              
                              {/* Read receipt for current user */}
                              {isCurrentUser && (
                                <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <CheckCheck className="h-3 w-3 text-[#6B7B8C]" />
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))}
                <div ref={chatMessagesEndRef} />
              </>
            )}
            {chatError && (
              <div className="text-red-400 text-xs p-3 bg-red-500/10 rounded-lg border border-red-500/20 mx-4 mt-2">
                {chatError}
              </div>
            )}
          </div>

          {/* Message Input Area - Telegram-style */}
          <div className="border-t border-[#1E2329] px-4 py-3 bg-[#1E2329] z-10 relative">
            {/* Emoji Picker Popover */}
            {showEmojiPicker && (
              <div 
                ref={emojiPickerRef}
                className="absolute bottom-full left-4 mb-2 w-80 h-64 bg-[#2B2B2B] border border-[#1E2329] rounded-lg shadow-xl z-50"
              >
                <div className="p-2 border-b border-[#1E2329] flex items-center justify-between">
                  <span className="text-[#E4E6EB] text-sm font-medium">絵文字</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setShowEmojiPicker(false)}
                    className="h-6 w-6 p-0 text-[#6B7B8C] hover:text-[#E4E6EB] hover:bg-[#1E2329] rounded"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
                <div className="h-[calc(100%-3rem)] overflow-y-auto p-2">
                  <div className="grid grid-cols-8 gap-1">
                    {commonEmojis.map((emoji, index) => (
                      <button
                        key={index}
                        onClick={() => insertEmoji(emoji)}
                        className="w-9 h-9 flex items-center justify-center text-xl hover:bg-[#1E2329] rounded transition-colors cursor-pointer"
                        title={emoji}
                      >
                        {emoji}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
            
            <div className="flex items-end gap-2">
              <div className="relative">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setShowEmojiPicker(!showEmojiPicker)}
                  className={`h-9 w-9 p-0 text-[#6B7B8C] hover:text-[#B1BBC3] hover:bg-[#2B2B2B] rounded-full transition-colors ${
                    showEmojiPicker ? 'bg-[#2B2B2B] text-[#B1BBC3]' : ''
                  }`}
                  title="絵文字"
                >
                  <Smile className="h-5 w-5" />
                </Button>
              </div>
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={`#${selectedStreamData?.channel || 'コミュニティ'} にメッセージを送信`}
                  className="w-full bg-[#2B2B2B] px-4 py-2.5 text-[#E4E6EB] text-sm placeholder-[#6B7B8C] focus:outline-none disabled:opacity-50 rounded-full border-0"
                  disabled={sendingMessage}
                  maxLength={500}
                />
              </div>
              <Button
                size="sm"
                onClick={sendCommunityMessage}
                disabled={!chatInput.trim() || sendingMessage}
                className="h-9 w-9 p-0 bg-[#5288C1] hover:bg-[#4775A8] text-white disabled:opacity-50 disabled:cursor-not-allowed transition-all rounded-full flex items-center justify-center"
                title="送信"
              >
                {sendingMessage ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
            <div className="flex items-center gap-2 text-xs text-[#6B7B8C] mt-2">
              <span>現在のユーザー: {currentUser}</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  const newUser = prompt('新しいユーザー名を入力:', currentUser);
                  if (newUser && newUser.trim()) {
                    setCurrentUser(newUser.trim());
                    localStorage.setItem('community_chat_username', newUser.trim());
                  }
                }}
                className="h-5 px-2 text-[10px] text-[#5288C1] hover:text-[#6B9BD1] hover:bg-[#2B2B2B] rounded transition-colors"
              >
                変更
              </Button>
            </div>
          </div>
            </>
          )}

        {/* Empty State when no chat selected */}
        {!selectedChatId && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <MessageSquare className="h-16 w-16 text-[#6B7B8C] mx-auto mb-4" />
              <p className="text-[#6B7B8C] text-lg">チャットを選択してください</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default CommunityStreams;


