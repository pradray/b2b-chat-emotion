import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
// PipelineDebugger removed - managed by parent


// Use environment variable for URL or default to local backend
const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000/chat';

// Storage keys
const STORAGE_KEY = 'b2b_chat_history';
const SETTINGS_KEY = 'b2b_app_settings';
const SESSION_KEY = 'b2b_session_id';
const MAX_MESSAGES = 50;

// Generate unique session ID
const generateSessionId = () => {
  return 'sess_' + Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
};

// Get or create session ID
const getSessionId = () => {
  let sessionId = localStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = generateSessionId();
    localStorage.setItem(SESSION_KEY, sessionId);
  }
  return sessionId;
};

// Helper to get initial settings
const getSettings = () => {
  const saved = localStorage.getItem(SETTINGS_KEY);
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch (e) {
      console.error("Failed to parse settings:", e);
    }
  }
  return { developerMode: false };
};

const ChatWidget = forwardRef(({ onNavigate, developerMode, onToggleDeveloperMode }, ref) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { text: "Hello! I can help with MOQ, Pricing, or Navigation. How are you feeling today?", sender: "bot", timestamp: Date.now() }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [lastEmotion, setLastEmotion] = useState(null);
  const [sessionId] = useState(getSessionId);
  const messagesEndRef = useRef(null);

  // Settings for Chat-specific things (removed developerMode from here)
  const [showSettings, setShowSettings] = useState(false);


  // Load messages from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
        }
      } catch (e) {
        console.error('Failed to parse saved messages:', e);
      }
    }
  }, []);

  // Save messages to localStorage when they change
  useEffect(() => {
    if (messages.length > 1) { // Don't save just the welcome message
      const toSave = messages.slice(-MAX_MESSAGES); // Keep only last 50 messages
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
    }
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Clear chat history
  const clearHistory = () => {
    const welcomeMsg = {
      text: "Hello! I can help with MOQ, Pricing, or Navigation. How are you feeling today?",
      sender: "bot",
      timestamp: Date.now()
    };
    setMessages([welcomeMsg]);
    localStorage.removeItem(STORAGE_KEY);
    setLastEmotion(null);
  };

  // Update and save settings
  const updateSettings = (newSettings) => {
    const updated = { ...settings, ...newSettings };
    setSettings(updated);
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(updated));
  };

  // Wrap the prop handler
  const handleToggleDevMode = () => {
    if (onToggleDeveloperMode) {
      onToggleDeveloperMode(!developerMode);
    }
  };

  const handleSend = async (textOverride = null) => {
    const textToSend = textOverride || input;
    if (!textToSend.trim()) return;

    // 1. Add User Message immediately
    const userMessage = { text: textToSend, sender: "user", timestamp: Date.now() };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: textToSend, sessionId })
      });

      const data = await response.json();

      // Extract emotion data from response
      const emotionData = data.emotion || null;
      setLastEmotion(emotionData);

      // 2. Add typing delay for natural feel (800-1500ms random)
      const typingDelay = 800 + Math.random() * 700;

      await new Promise(resolve => setTimeout(resolve, typingDelay));

      // 3. Add Bot Response with emotion info
      setMessages(prev => [...prev, {
        text: data.message,
        sender: "bot",
        emotion: emotionData,
        timestamp: Date.now()
      }]);

      if (data.action) {
        onNavigate(data.action);
      }

    } catch (error) {
      // Add delay even for errors
      await new Promise(resolve => setTimeout(resolve, 500));
      setMessages(prev => [...prev, {
        text: "Network error. Please try again.",
        sender: "bot",
        timestamp: Date.now()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Accessibility: Handle 'Enter' key
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSend();
  };

  // Get emotion color class
  const getEmotionClass = (emotion) => {
    if (!emotion) return '';
    const emotionMap = {
      'happy': 'emotion-happy',
      'positive': 'emotion-positive',
      'neutral': 'emotion-neutral',
      'negative': 'emotion-negative',
      'sad': 'emotion-sad',
      'angry': 'emotion-angry',
      'frustrated': 'emotion-frustrated',
      'anxious': 'emotion-anxious'
    };
    return emotionMap[emotion] || '';
  };

  // Expose methods to parent via ref
  useImperativeHandle(ref, () => ({
    sendMessage: (text) => handleSend(text),
    openChat: () => setIsOpen(true)
  }));

  return (
    <div className="chat-widget">
      {/* ... (component JSX remains same) ... */}
      <button
        className="chat-toggle"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle Chat Support"
      >
        {isOpen ? "✖" : "💬 Support"}
      </button>

      {isOpen && (
        <div
          className="chat-window"
          role="dialog"
          aria-label="B2B Support Assistant"
        >
          {/* ... */}
          <div className="chat-header">
            <span>B2B Assistant</span>
            {lastEmotion && (
              <span className="emotion-indicator" title={`Detected: ${lastEmotion.detected}`}>
                {lastEmotion.emoji}
              </span>
            )}
            <button
              className="clear-history-btn"
              onClick={clearHistory}
              title="Clear chat history"
            >
              Clear
            </button>
            <button
              className="settings-btn"
              onClick={() => setShowSettings(true)}
              title="Settings"
            >
              ⚙️
            </button>
            <button onClick={() => setIsOpen(false)} aria-label="Close Chat" style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}>✖</button>
          </div>

          <div className="chat-body">
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.sender} ${msg.emotion ? getEmotionClass(msg.emotion.detected) : ''}`}>
                {msg.sender === 'bot' && msg.emotion && (
                  <span className="message-emotion-badge" title={`Emotion: ${msg.emotion.detected} (${Math.round(msg.emotion.confidence * 100)}%)`}>
                    {msg.emotion.emoji}
                  </span>
                )}
                <span className="message-text">{msg.text}</span>
              </div>
            ))}

            {isLoading && (
              <div className="message bot">
                <div className="typing-indicator">
                  <span className="dot"></span>
                  <span className="dot"></span>
                  <span className="dot"></span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />

            <div className="chips">
              <button onClick={() => handleSend("Check MOQ")} tabIndex="0">MOQ</button>
              <button onClick={() => handleSend("Go to Marketplace")} tabIndex="0">Marketplace</button>
              <button onClick={() => handleSend("Suppliers")} tabIndex="0">Suppliers</button>
            </div>
          </div>

          <div className="chat-input-area">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type here... (try expressing emotions!)"
              aria-label="Type your message"
            />
            <button onClick={() => handleSend()}>Send</button>
          </div>
        </div>
      )}

      {/* Settings Modal - kept simplified for brevity in replacement, original code logic applies */}
      {showSettings && (
        <div className="settings-modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
            <div className="settings-header">
              <h3>⚙️ Settings</h3>
              <button className="settings-close" onClick={() => setShowSettings(false)}>✕</button>
            </div>
            <div className="settings-body">
              {/* Settings content */}
              <div className="settings-item">
                <div>
                  <div className="settings-label">🔧 Developer Mode</div>
                </div>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={developerMode}
                    onChange={handleToggleDevMode}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* PipelineDebugger removed from here, rendered by App.jsx */}

    </div>
  );
});

ChatWidget.displayName = 'ChatWidget';

export default ChatWidget;