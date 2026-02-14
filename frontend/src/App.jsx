import { useState, useEffect, useRef } from 'react';
import './App.css';
import ChatWidget from './ChatWidget';
import VoiceChatWidget from './VoiceChatWidget';
import PipelineDebugger from './PipelineDebugger';
import About from './About';

// Settings storage key
const SETTINGS_KEY = 'b2b_app_settings';

// Available voices for TTS
// Available voices for TTS (Initial static list, will be populated dynamically)
const INITIAL_VOICE_OPTIONS = [
  { id: 'default', name: 'System Default' }
];

function App() {
  const [activeTab, setActiveTab] = useState('marketplace');

  // Dynamic voice options
  const [voiceOptions, setVoiceOptions] = useState(INITIAL_VOICE_OPTIONS);

  // --- SETTINGS STATE ---
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem(SETTINGS_KEY);
    if (saved) {
      const settings = JSON.parse(saved);
      return settings.darkMode || false;
    }
    return false;
  });

  const [selectedVoice, setSelectedVoice] = useState(() => {
    const saved = localStorage.getItem(SETTINGS_KEY);
    if (saved) {
      const settings = JSON.parse(saved);
      return settings.voice || 'default';
    }
    return 'default';
  });

  const [developerMode, setDeveloperMode] = useState(() => {
    const saved = localStorage.getItem(SETTINGS_KEY);
    if (saved) {
      const settings = JSON.parse(saved);
      return settings.developerMode || false;
    }
    return false;
  });

  const [showDebugger, setShowDebugger] = useState(() => {
    const saved = localStorage.getItem(SETTINGS_KEY);
    if (saved) {
      const settings = JSON.parse(saved);
      return settings.developerMode || false;
    }
    return false;
  });
  const [debuggerMaximized, setDebuggerMaximized] = useState(false);

  // --- FORM STATE ---
  const [rfqForm, setRfqForm] = useState({ companyName: '', targetPrice: '' });
  const [rfqErrors, setRfqErrors] = useState({});
  const [rfqSubmitted, setRfqSubmitted] = useState(false);
  const [showDemoAlert, setShowDemoAlert] = useState(false);

  const [loginForm, setLoginForm] = useState({ email: '' });
  const [loginErrors, setLoginErrors] = useState({});

  // --- MOCK DATA ---
  const products = [
    { id: 1, name: "Industrial Servo Motor", price: "$450.00", moq: "10 Units", image: "/servo_motor.png", category: "Motors" },
    { id: 2, name: "500m Fiber Optic Cable", price: "$120.00", moq: "20 Rolls", image: "/fiber_optic.png", category: "Cables" },
    { id: 3, name: "Heavy Duty Actuator", price: "$85.00", moq: "50 Units", image: "/actuator.png", category: "Actuators" },
  ];

  const suppliers = [
    { name: "Global Steel Works", region: "Germany", rating: "★★★★★" },
    { name: "Shenzhen Electronics", region: "China", rating: "★★★★☆" },
  ];

  // --- SAVE SETTINGS TO LOCALSTORAGE ---
  useEffect(() => {
    try {
      const settings = { darkMode, voice: selectedVoice, developerMode };
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    } catch (e) {
      console.error('Failed to save settings:', e);
    }

    // Apply dark mode class to body
    if (darkMode) {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  }, [darkMode, selectedVoice, developerMode]);

  // --- VALIDATION FUNCTIONS ---
  const validateRfqForm = () => {
    const errors = {};
    if (!rfqForm.companyName.trim()) {
      errors.companyName = 'Company name is required';
    } else if (rfqForm.companyName.trim().length < 2) {
      errors.companyName = 'Company name must be at least 2 characters';
    }
    if (!rfqForm.targetPrice) {
      errors.targetPrice = 'Target price is required';
    } else if (parseFloat(rfqForm.targetPrice) <= 0) {
      errors.targetPrice = 'Price must be a positive number';
    } else if (parseFloat(rfqForm.targetPrice) > 10000000) {
      errors.targetPrice = 'Price cannot exceed $10,000,000';
    }
    setRfqErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const validateLoginForm = () => {
    const errors = {};
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!loginForm.email.trim()) {
      errors.email = 'Email is required';
    } else if (!emailRegex.test(loginForm.email)) {
      errors.email = 'Please enter a valid email address';
    }
    setLoginErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Ref for ChatWidget
  const chatRef = useRef(null);

  // --- FORM HANDLERS ---
  const handleRfqSubmit = (e) => {
    e.preventDefault();
    if (validateRfqForm()) {
      setRfqSubmitted(true);

      // Notify Chatbot invisibly!
      if (chatRef.current) {
        chatRef.current.sendMessage("SYSTEM_RFQ_SUBMITTED");
        chatRef.current.openChat();
      }

      setRfqForm({ companyName: '', targetPrice: '' });
      setTimeout(() => setRfqSubmitted(false), 3000);
    }
  };

  const handleLoginSubmit = (e) => {
    e.preventDefault();
    if (validateLoginForm()) {
      setDemoAlertMessage('Login functionality is currently disabled in this demo.');
      setShowDemoAlert(true);
      setLoginForm({ email: '' });
    }
  };

  const handleAddToCart = () => {
    setDemoAlertMessage('Other features like "Add to Cart" are currently disabled.');
    setShowDemoAlert(true);
  };

  // Callback for Chatbot Navigation
  const handleBotNavigation = (page) => {
    if (page && ['marketplace', 'suppliers', 'rfq', 'login', 'settings'].includes(page)) {
      setActiveTab(page);
    }
  };

  // Handler for when voices are loaded from VoiceChatWidget
  const handleVoicesLoaded = (voices) => {
    const englishVoices = voices.filter(v => v.lang.startsWith('en'));
    const options = [
      { id: 'default', name: 'System Default' },
      ...englishVoices.map(v => ({ id: v.name, name: `${v.name} (${v.lang})` }))
    ];
    setVoiceOptions(options);
  };

  // Add state for dynamic message
  const [demoAlertMessage, setDemoAlertMessage] = useState('Other features like "Add to Cart" are currently disabled.');


  return (
    <div className={`app-container ${darkMode ? 'dark-mode' : ''}`}>
      <header className="header">
        <div className="header-left">
          {/* Optional: <img src="/images/team/college_icon.png" className="header-icon" /> */}
          <h1>Global B2B Hub</h1>
        </div>
        <nav>
          <button className={activeTab === 'marketplace' ? 'active' : ''} onClick={() => setActiveTab('marketplace')}>Marketplace</button>
          <button className={activeTab === 'suppliers' ? 'active' : ''} onClick={() => setActiveTab('suppliers')}>Suppliers</button>
          <button className={activeTab === 'rfq' ? 'active' : ''} onClick={() => setActiveTab('rfq')}>Bulk RFQ</button>
          <button className={activeTab === 'about' ? 'active' : ''} onClick={() => setActiveTab('about')}>About Us</button>
          <button className={activeTab === 'login' ? 'active' : ''} onClick={() => setActiveTab('login')}>Login</button>
          <button className={activeTab === 'settings' ? 'active' : ''} onClick={() => setActiveTab('settings')}>⚙️ Settings</button>
        </nav>
      </header>

      <main className="main-content">
        {activeTab === 'marketplace' && (
          // ... (existing marketplace code)
          <div className="fade-in">
            <h2>Wholesale Marketplace</h2>
            <div className="grid">
              {products.map(p => (
                <div key={p.id} className="card product-card">
                  <div className="product-image-container">
                    <img src={p.image} alt={p.name} className="product-image" />
                    <span className="category-badge">{p.category}</span>
                  </div>
                  <div className="product-info">
                    <h3>{p.name}</h3>
                    <p className="product-price">{p.price}</p>
                    <span className="badge">MOQ: {p.moq}</span>
                    <button className="btn-add-cart" onClick={handleAddToCart}>Add to Cart</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'suppliers' && (
          // ... (existing suppliers code)
          <div className="fade-in">
            <h2>Verified Suppliers</h2>
            <ul>
              {suppliers.map((s, idx) => (
                <li key={idx} className="list-item">
                  <strong>{s.name}</strong> ({s.region}) - {s.rating}
                </li>
              ))}
            </ul>
          </div>
        )}

        {activeTab === 'rfq' && (
          // ... (existing rfq code)
          <div className="fade-in">
            <h2>Request for Quotation</h2>
            {rfqSubmitted && (
              <div className="success-message">
                ✓ RFQ submitted successfully! We'll contact you soon.
              </div>
            )}
            <form className="rfq-form" onSubmit={handleRfqSubmit}>
              <div className="form-group">
                <input
                  placeholder="Company Name"
                  className={`input-field ${rfqErrors.companyName ? 'input-error' : ''}`}
                  value={rfqForm.companyName}
                  onChange={(e) => setRfqForm({ ...rfqForm, companyName: e.target.value })}
                />
                {rfqErrors.companyName && <span className="error-message">{rfqErrors.companyName}</span>}
              </div>
              <div className="form-group">
                <input
                  placeholder="Target Price ($)"
                  type="number"
                  min="0"
                  step="0.01"
                  className={`input-field ${rfqErrors.targetPrice ? 'input-error' : ''}`}
                  value={rfqForm.targetPrice}
                  onChange={(e) => setRfqForm({ ...rfqForm, targetPrice: e.target.value })}
                />
                {rfqErrors.targetPrice && <span className="error-message">{rfqErrors.targetPrice}</span>}
              </div>
              <button type="submit" className="btn-primary">Submit RFQ</button>
            </form>
          </div>
        )}

        {activeTab === 'about' && (
          <About />
        )}

        {activeTab === 'login' && (
          // ... (existing login code)
          <div className="fade-in">
            <h2>Partner Login</h2>
            <form className="login-form" onSubmit={handleLoginSubmit}>
              <div className="form-group">
                <input
                  placeholder="Email"
                  type="email"
                  className={`input-field ${loginErrors.email ? 'input-error' : ''}`}
                  value={loginForm.email}
                  onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                />
                {loginErrors.email && <span className="error-message">{loginErrors.email}</span>}
              </div>
              <button type="submit" className="btn-primary">Login</button>
            </form>
          </div>
        )}

        {activeTab === 'settings' && (
          // ... (existing settings code)
          <div className="fade-in">
            <h2>⚙️ Settings</h2>
            <div className="settings-container">
              {/* Dark Mode Toggle */}
              <div className="settings-section">
                <h3>🎨 Appearance</h3>
                <div className="settings-option">
                  <label htmlFor="darkMode">Dark Mode</label>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      id="darkMode"
                      checked={darkMode}
                      onChange={(e) => setDarkMode(e.target.checked)}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>
                <p className="settings-description">
                  Enable dark mode for a darker color scheme that's easier on the eyes.
                </p>
              </div>

              {/* Voice Selection */}
              <div className="settings-section">
                <h3>🔊 Voice Assistant</h3>
                <div className="settings-option">
                  <label htmlFor="voiceSelect">Text-to-Speech Voice</label>
                  <select
                    id="voiceSelect"
                    className="settings-select"
                    value={selectedVoice}
                    onChange={(e) => setSelectedVoice(e.target.value)}
                  >
                    {voiceOptions.map(voice => (
                      <option key={voice.id} value={voice.id}>
                        {voice.name}
                      </option>
                    ))}
                  </select>
                </div>
                <p className="settings-description">
                  Choose the voice used for text-to-speech in the Voice Chat widget.
                </p>
              </div>

              {/* Chat Settings */}
              <div className="settings-section">
                <h3>💬 Chat</h3>
                <div className="settings-option">
                  <label>Chat History</label>
                  <button
                    className="btn-secondary"
                    onClick={() => {
                      localStorage.removeItem('b2b_chat_history');
                      localStorage.removeItem('b2b_voice_chat_history');
                      // Reload page to reset chat widget state
                      window.location.reload();
                    }}
                  >
                    Clear All History
                  </button>
                </div>
                <p className="settings-description">
                  Clear all saved chat messages from both text and voice chat widgets.
                </p>
              </div>

              {/* Developer Mode */}
              <div className="settings-section">
                <h3>🔧 Developer Mode</h3>
                <div className="settings-option">
                  <label htmlFor="devMode">Pipeline Debugger</label>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      id="devMode"
                      checked={developerMode}
                      onChange={(e) => {
                        setDeveloperMode(e.target.checked);
                        if (e.target.checked) {
                          setShowDebugger(true);
                        } else {
                          setShowDebugger(false);
                        }
                      }}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>
                <p className="settings-description">
                  Show the pipeline debugger to visualize AI processing stages step-by-step.
                </p>
                {developerMode && !showDebugger && (
                  <button
                    className="btn-secondary"
                    onClick={() => setShowDebugger(true)}
                    style={{ marginTop: '10px' }}
                  >
                    📊 Open Debugger
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Text-based Chat Widget */}
      <ChatWidget
        ref={chatRef}
        onNavigate={handleBotNavigation}
        developerMode={developerMode}
        onToggleDeveloperMode={(enabled) => {
          setDeveloperMode(enabled);
          if (enabled) {
            setShowDebugger(true);
          } else {
            setShowDebugger(false);
          }
        }}
      />

      {/* Voice-based Chat Widget */}
      <VoiceChatWidget
        onNavigate={handleBotNavigation}
        selectedVoice={selectedVoice}
        onVoicesLoaded={handleVoicesLoaded}
      />

      {/* Pipeline Debugger (Developer Mode) */}
      {developerMode && showDebugger && (
        <PipelineDebugger
          isMaximized={debuggerMaximized}
          onToggleMaximize={() => setDebuggerMaximized(!debuggerMaximized)}
          onClose={() => setShowDebugger(false)}
        />
      )}

      {/* Demo Alert Modal */}
      {showDemoAlert && (
        <div className="demo-modal-overlay" onClick={() => setShowDemoAlert(false)}>
          <div className="demo-modal" onClick={e => e.stopPropagation()}>
            <h3>🚧 Demo Mode</h3>
            <p>This application is a demo for demonstrating Conversational AI capabilities.<br />{demoAlertMessage}</p>
            <button onClick={() => setShowDemoAlert(false)}>Got it</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;