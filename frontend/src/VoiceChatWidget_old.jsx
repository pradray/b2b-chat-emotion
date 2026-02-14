import { useState, useEffect, useRef } from 'react';

// Use environment variable for URL
const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000/chat';

// Storage keys
const STORAGE_KEY = 'b2b_voice_chat_history';
const SESSION_KEY = 'b2b_session_id';
const MAX_MESSAGES = 50;

// Check for browser support
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const speechSynthesis = window.speechSynthesis;

// Generate unique session ID
const generateSessionId = () => {
    return 'sess_' + Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
};

// Get or create session ID (shared with ChatWidget)
const getSessionId = () => {
    let sessionId = localStorage.getItem(SESSION_KEY);
    if (!sessionId) {
        sessionId = generateSessionId();
        localStorage.setItem(SESSION_KEY, sessionId);
    }
    return sessionId;
};

const VoiceChatWidget = ({ onNavigate, selectedVoice = 'default' }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([
        { text: "Hello! I'm your voice-enabled B2B Assistant. Click the microphone to speak, or type below.", sender: "bot", timestamp: Date.now() }
    ]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isListening, setIsListening] = useState(false);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [lastEmotion, setLastEmotion] = useState(null);
    const [voiceEnabled, setVoiceEnabled] = useState(true);
    const [speechSupported, setSpeechSupported] = useState(true);
    const [sessionId] = useState(getSessionId);

    const messagesEndRef = useRef(null);
    const recognitionRef = useRef(null);

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
                console.error('Failed to parse saved voice messages:', e);
            }
        }
    }, []);

    // Save messages to localStorage when they change
    useEffect(() => {
        if (messages.length > 1) {
            const toSave = messages.slice(-MAX_MESSAGES);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
        }
    }, [messages]);

    // Initialize speech recognition
    useEffect(() => {
        if (SpeechRecognition) {
            const recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onstart = () => {
                setIsListening(true);
            };

            recognition.onresult = (event) => {
                const transcript = Array.from(event.results)
                    .map(result => result[0].transcript)
                    .join('');

                setInput(transcript);

                // If this is a final result, send the message
                if (event.results[0].isFinal) {
                    handleSend(transcript);
                }
            };

            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                setIsListening(false);
                if (event.error === 'not-allowed') {
                    setSpeechSupported(false);
                }
            };

            recognition.onend = () => {
                setIsListening(false);
            };

            recognitionRef.current = recognition;
        } else {
            setSpeechSupported(false);
        }

        return () => {
            if (recognitionRef.current) {
                recognitionRef.current.abort();
            }
        };
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoading]);

    // Clear chat history
    const clearHistory = () => {
        const welcomeMsg = {
            text: "Hello! I'm your voice-enabled B2B Assistant. Click the microphone to speak, or type below.",
            sender: "bot",
            timestamp: Date.now()
        };
        setMessages([welcomeMsg]);
        localStorage.removeItem(STORAGE_KEY);
        setLastEmotion(null);
    };

    // Text-to-speech function
    const speakText = (text) => {
        if (!speechSynthesis || !voiceEnabled) return;

        // Cancel any ongoing speech
        speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1;
        utterance.pitch = 1;
        utterance.volume = 1;
        utterance.lang = 'en-US';  // Force English language

        // Get all available voices
        const voices = speechSynthesis.getVoices();

        // Select voice based on settings preference
        let chosenVoice = null;

        if (selectedVoice !== 'default') {
            // Match based on settings selection
            const voiceMatchers = {
                'en-US-female': v => v.lang.startsWith('en-US') && (v.name.toLowerCase().includes('female') || v.name.includes('Zira') || v.name.includes('Eva') || v.name.includes('Samantha')),
                'en-US-male': v => v.lang.startsWith('en-US') && (v.name.toLowerCase().includes('male') || v.name.includes('David') || v.name.includes('Mark') || v.name.includes('Alex')),
                'en-GB-female': v => v.lang.startsWith('en-GB') && (v.name.toLowerCase().includes('female') || v.name.includes('Hazel') || v.name.includes('Susan')),
                'en-GB-male': v => v.lang.startsWith('en-GB') && (v.name.toLowerCase().includes('male') || v.name.includes('Daniel') || v.name.includes('Oliver')),
            };

            const matcher = voiceMatchers[selectedVoice];
            if (matcher) {
                chosenVoice = voices.find(matcher);
            }
        }

        // Fallback: use default priority if no match or default selected
        if (!chosenVoice) {
            const voicePreferences = [
                // Microsoft English voices (common on Windows)
                v => v.name.includes('Microsoft Zira') || v.name.includes('Microsoft Eva'),
                v => v.name.includes('Microsoft David') || v.name.includes('Microsoft Mark'),
                // Google English voices (common on Chrome)
                v => v.name.includes('Google US English'),
                v => v.name.includes('Google UK English'),
                // Any English voice
                v => v.lang.startsWith('en-US'),
                v => v.lang.startsWith('en-GB'),
                v => v.lang.startsWith('en'),
                // Fallback: any voice with 'English' in the name
                v => v.name.toLowerCase().includes('english')
            ];

            for (const preference of voicePreferences) {
                chosenVoice = voices.find(preference);
                if (chosenVoice) break;
            }
        }

        if (chosenVoice) {
            utterance.voice = chosenVoice;
            console.log('Using voice:', chosenVoice.name);
        }

        utterance.onstart = () => setIsSpeaking(true);
        utterance.onend = () => setIsSpeaking(false);
        utterance.onerror = () => setIsSpeaking(false);

        speechSynthesis.speak(utterance);
    };

    // Toggle voice recording
    const toggleListening = () => {
        if (!recognitionRef.current) return;

        if (isListening) {
            recognitionRef.current.stop();
        } else {
            // Cancel any ongoing speech before listening
            if (speechSynthesis) {
                speechSynthesis.cancel();
            }
            setInput("");
            recognitionRef.current.start();
        }
    };

    const handleSend = async (textOverride = null) => {
        const textToSend = textOverride || input;
        if (!textToSend.trim()) return;

        // Stop listening if active
        if (isListening && recognitionRef.current) {
            recognitionRef.current.stop();
        }

        // Add User Message immediately
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

            // Extract emotion data
            const emotionData = data.emotion || null;
            setLastEmotion(emotionData);

            // Add typing delay for natural feel (800-1500ms random)
            const typingDelay = 800 + Math.random() * 700;
            await new Promise(resolve => setTimeout(resolve, typingDelay));

            // Add Bot Response
            setMessages(prev => [...prev, {
                text: data.message,
                sender: "bot",
                emotion: emotionData,
                timestamp: Date.now()
            }]);

            // Speak the response if voice is enabled
            if (voiceEnabled) {
                speakText(data.message);
            }

            if (data.action) {
                onNavigate(data.action);
            }

        } catch (error) {
            await new Promise(resolve => setTimeout(resolve, 500));
            const errorMsg = "Network error. Please try again.";
            setMessages(prev => [...prev, { text: errorMsg, sender: "bot", timestamp: Date.now() }]);
            if (voiceEnabled) speakText(errorMsg);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') handleSend();
    };

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

    return (
        <div className="chat-widget voice-chat-widget">
            <button
                className="chat-toggle voice-toggle"
                onClick={() => setIsOpen(!isOpen)}
                aria-label="Toggle Voice Chat Support"
            >
                {isOpen ? "✖" : "🎙️ Voice"}
            </button>

            {isOpen && (
                <div
                    className="chat-window voice-chat-window"
                    role="dialog"
                    aria-label="B2B Voice Assistant"
                >
                    <div className="chat-header voice-header">
                        <span>🎤 Voice Assistant</span>
                        {lastEmotion && (
                            <span className="emotion-indicator" title={`Detected: ${lastEmotion.detected}`}>
                                {lastEmotion.emoji}
                            </span>
                        )}
                        <div className="voice-controls">
                            <button
                                className={`voice-toggle-btn ${voiceEnabled ? 'active' : ''}`}
                                onClick={() => setVoiceEnabled(!voiceEnabled)}
                                title={voiceEnabled ? 'Disable voice responses' : 'Enable voice responses'}
                            >
                                {voiceEnabled ? '🔊' : '🔇'}
                            </button>
                            <button
                                className="clear-history-btn"
                                onClick={clearHistory}
                                title="Clear chat history"
                            >
                                Clear
                            </button>
                            <button onClick={() => setIsOpen(false)} aria-label="Close Chat" className="close-btn">✖</button>
                        </div>
                    </div>

                    <div className="chat-body">
                        {!speechSupported && (
                            <div className="voice-warning">
                                ⚠️ Voice recognition not supported in this browser. Please use text input.
                            </div>
                        )}

                        {messages.map((msg, i) => (
                            <div key={i} className={`message ${msg.sender} ${msg.emotion ? getEmotionClass(msg.emotion.detected) : ''}`}>
                                {msg.sender === 'bot' && msg.emotion && (
                                    <span className="message-emotion-badge" title={`Emotion: ${msg.emotion.detected}`}>
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
                        {isSpeaking && <div className="speaking-indicator">🔊 Speaking...</div>}

                        <div ref={messagesEndRef} />

                        <div className="chips">
                            <button onClick={() => handleSend("Check MOQ")} tabIndex="0">MOQ</button>
                            <button onClick={() => handleSend("Go to Marketplace")} tabIndex="0">Marketplace</button>
                            <button onClick={() => handleSend("I'm frustrated with the wait")} tabIndex="0">Help</button>
                        </div>
                    </div>

                    <div className="chat-input-area voice-input-area">
                        {speechSupported && (
                            <button
                                className={`mic-button ${isListening ? 'recording' : ''}`}
                                onClick={toggleListening}
                                aria-label={isListening ? 'Stop recording' : 'Start recording'}
                                title={isListening ? 'Click to stop' : 'Click to speak'}
                            >
                                {isListening ? '⏹️' : '🎤'}
                            </button>
                        )}
                        <input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={isListening ? "Listening..." : "Type or speak..."}
                            aria-label="Type your message"
                            disabled={isListening}
                        />
                        <button onClick={() => handleSend()} disabled={isListening}>Send</button>
                    </div>

                    {isListening && (
                        <div className="listening-overlay">
                            <div className="listening-animation">
                                <span></span><span></span><span></span>
                            </div>
                            <p>Listening... Speak now</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default VoiceChatWidget;
