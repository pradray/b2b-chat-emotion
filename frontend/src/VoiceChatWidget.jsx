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

const VoiceChatWidget = ({ onNavigate, selectedVoice = 'default', onVoicesLoaded }) => {
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
    const [availableVoices, setAvailableVoices] = useState([]);
    const [errorMessage, setErrorMessage] = useState(null);

    // Permission States
    const [micPermission, setMicPermission] = useState('prompt'); // 'granted', 'denied', 'prompt'

    const [sessionId] = useState(getSessionId);

    const messagesEndRef = useRef(null);
    const recognitionRef = useRef(null);
    const handleSendRef = useRef(null);


    // Load available voices
    useEffect(() => {
        const loadVoices = () => {
            const voices = speechSynthesis.getVoices();
            if (voices.length > 0) {
                setAvailableVoices(voices);
                console.log(`Loaded ${voices.length} voices:`, voices.map(v => `${v.name} (${v.lang})`));
                if (onVoicesLoaded) {
                    onVoicesLoaded(voices);
                }
            }
        };

        // Try to load immediately
        loadVoices();

        // Chrome loads voices asynchronously
        if (speechSynthesis && speechSynthesis.onvoiceschanged !== undefined) {
            speechSynthesis.onvoiceschanged = loadVoices;
        }

        return () => {
            if (speechSynthesis) {
                speechSynthesis.onvoiceschanged = null;
            }
        };
    }, []);

    // Check Microphone Permission
    useEffect(() => {
        const checkPermission = async () => {
            if (navigator.permissions && navigator.permissions.query) {
                try {
                    const permissionStatus = await navigator.permissions.query({ name: 'microphone' });
                    setMicPermission(permissionStatus.state);

                    permissionStatus.onchange = () => {
                        console.log("Microphone permission changed to:", permissionStatus.state);
                        setMicPermission(permissionStatus.state);
                    };
                } catch (e) {
                    console.warn("Permission API not supported:", e);
                }
            }
        };

        checkPermission();
    }, []);

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

            recognition.onspeechstart = () => {
                // Speech detected, so mic is working! Clear the silence warning timer.
                if (recognition.silenceTimer) clearTimeout(recognition.silenceTimer);
                setErrorMessage(null);
            };

            recognition.onstart = () => {
                setIsListening(true);
                setErrorMessage(null);

                // Set a timeout to warn about potential hardware mute if no speech is detected (removed in favor of visual check)
                // We keep a fallback timeout just in case
                recognition.silenceTimer = setTimeout(() => {
                    setErrorMessage("Hearing silence... Is your microphone muted?");
                }, 8000);
            };

            recognition.onresult = (event) => {
                // Clear silence warning
                if (recognition.silenceTimer) clearTimeout(recognition.silenceTimer);
                setErrorMessage(null);

                const transcript = Array.from(event.results)
                    .map(result => result[0].transcript)
                    .join('');

                setInput(transcript);

                // If this is a final result, send the message
                if (event.results[0].isFinal) {
                    if (handleSendRef.current) {
                        handleSendRef.current(transcript);
                    }
                }
            };

            recognition.onerror = (event) => {
                if (recognition.silenceTimer) clearTimeout(recognition.silenceTimer);

                console.error('Speech recognition error:', event.error);
                setIsListening(false);
                if (event.error === 'not-allowed') {
                    setErrorMessage("Microphone access blocked. Please check permissions.");
                    setSpeechSupported(false);
                    setMicPermission('denied'); // Force update state
                } else if (event.error === 'no-speech') {
                    // Usually just means timeout
                    setErrorMessage("No speech detected. Please try again.");
                } else {
                    setErrorMessage(`Voice error: ${event.error}`);
                }
            };

            recognition.onend = () => {
                if (recognition.silenceTimer) clearTimeout(recognition.silenceTimer);
                setIsListening(false);
            };

            recognitionRef.current = recognition;
        } else {
            setSpeechSupported(false);
            setErrorMessage("Voice recognition not supported in this browser.");
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
        setErrorMessage(null);
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
        utterance.lang = 'en-US';

        // Select voice based on settings preference
        let chosenVoice = null;

        if (availableVoices.length > 0) {
            if (selectedVoice !== 'default') {
                // Try to find exact name match first (since we now pass full names from App)
                chosenVoice = availableVoices.find(v => v.name === selectedVoice);

                // If not found (maybe legacy ID?), try the old matchers
                if (!chosenVoice) {
                    // Helper for loose lang match
                    const matchLang = (voiceLang, targetLang) => {
                        const v = voiceLang.toLowerCase().replace('_', '-');
                        const t = targetLang.toLowerCase();
                        return v.startsWith(t);
                    };

                    // Match based on settings selection
                    const voiceMatchers = {
                        'en-US-female': v => matchLang(v.lang, 'en-us') && (
                            v.name.toLowerCase().includes('female') ||
                            v.name.includes('Zira') ||
                            v.name.includes('Eva') ||
                            v.name.includes('Samantha') ||
                            v.name.includes('Google US English')
                        ),
                        'en-US-male': v => matchLang(v.lang, 'en-us') && (
                            v.name.toLowerCase().includes('male') ||
                            v.name.includes('David') ||
                            v.name.includes('Mark') ||
                            v.name.includes('Alex')
                        ),
                        'en-GB-female': v => matchLang(v.lang, 'en-gb') && (
                            v.name.toLowerCase().includes('female') ||
                            v.name.includes('Hazel') ||
                            v.name.includes('Susan') ||
                            v.name.includes('Google UK English Female')
                        ),
                        'en-GB-male': v => matchLang(v.lang, 'en-gb') && (
                            v.name.toLowerCase().includes('male') ||
                            v.name.includes('Daniel') ||
                            v.name.includes('Oliver') ||
                            v.name.includes('Google UK English Male')
                        ),
                    };

                    const matcher = voiceMatchers[selectedVoice];
                    if (matcher) {
                        chosenVoice = availableVoices.find(matcher);
                    }
                }
                // Fallback if still no match
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
                        chosenVoice = availableVoices.find(preference);
                        if (chosenVoice) break;
                    }
                }
            }
        }

        if (chosenVoice) {
            utterance.voice = chosenVoice;
            console.log('Using voice:', chosenVoice.name);
        } else {
            console.warn('No specific voice found, using system default.');
        }

        utterance.onstart = () => setIsSpeaking(true);
        utterance.onend = () => setIsSpeaking(false);
        utterance.onerror = (e) => {
            console.error('TTS Error:', e);
            setIsSpeaking(false);
        };

        speechSynthesis.speak(utterance);
    };

    const testSound = () => {
        if (!speechSynthesis) return;

        // Force un-mute temporarily for test if user has muted locally? 
        // No, respect user setting but warn if muted.
        if (!voiceEnabled) {
            setErrorMessage("Voice is active but muted by you. Unmute to hear.");
            // Optional: automatically unmute? Better to let user control.
        }

        const utterance = new SpeechSynthesisUtterance("Testing audio volume. One, two, three.");
        utterance.volume = 1;
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
            setErrorMessage(null);
            try {
                recognitionRef.current.start();
            } catch (e) {
                console.error("Failed to start recognition:", e);
                setErrorMessage("Could not start microphone. Refresh and try again.");
            }
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
        setErrorMessage(null);

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

    // Keep ref updated
    useEffect(() => {
        handleSendRef.current = handleSend;
    }, [handleSend]);

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
                                className="test-sound-btn"
                                onClick={testSound}
                                title="Test Audio Volume"
                                style={{ fontSize: '0.8rem', padding: '2px 6px', marginRight: '5px' }}
                            >
                                🔊 Test
                            </button>
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

                    {/* Diagnostic Bar */}
                    <div className="diagnostic-bar" style={{
                        padding: '4px 8px',
                        fontSize: '0.75rem',
                        backgroundColor: '#f5f5f5',
                        borderBottom: '1px solid #eee',
                        display: 'flex',
                        justifyContent: 'space-between',
                        color: '#666'
                    }}>
                        <span title="Microphone Access Status">
                            {micPermission === 'granted' && "✅ Access Granted"}
                            {micPermission === 'denied' && "🚫 Access Denied"}
                            {micPermission === 'prompt' && "⚠️ Allow Access"}
                        </span>
                        <span>
                            {!voiceEnabled ? "🔇 Muted" : "🔊 Sound On"}
                        </span>
                    </div>

                    <div className="chat-body">
                        {!speechSupported && (
                            <div className="voice-warning error">
                                ⚠️ Voice recognition not supported in this browser. Please use Chrome.
                            </div>
                        )}

                        {micPermission === 'denied' && (
                            <div className="voice-warning error">
                                🚫 Microphone access is blocked. Please allow access in your browser settings (Lock icon in address bar).
                            </div>
                        )}

                        {errorMessage && (
                            <div className="voice-warning error">
                                {errorMessage}
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
                            <button onClick={() => handleSend("Suppliers")} tabIndex="0">Suppliers</button>
                        </div>
                    </div>

                    <div className="chat-input-area voice-input-area">
                        {speechSupported && (
                            <button
                                className={`mic-button ${isListening ? 'recording' : ''}`}
                                onClick={toggleListening}
                                disabled={micPermission === 'denied'}
                                aria-label={isListening ? 'Stop recording' : 'Start recording'}
                                title={micPermission === 'denied' ? 'Microphone blocked' : (isListening ? 'Click to stop' : 'Click to speak')}
                                style={micPermission === 'denied' ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
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
