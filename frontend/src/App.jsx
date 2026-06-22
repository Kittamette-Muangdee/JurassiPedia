import React, { useState, useEffect, useRef } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// Predefined catalogs default to English
const dinoDirectory = [
  { id: 'trex', emoji: '🦖', name: 'Tyrannosaurus Rex', spec: 'Apex Predator', query: 'Tell me the history of Tyrannosaurus Rex (T-Rex) briefly.' },
  { id: 'raptor', emoji: '⚡', name: 'Velociraptor', spec: 'Pack Hunter', query: 'What special abilities did Velociraptor have?' },
  { id: 'dilo', emoji: '🧪', name: 'Dilophosaurus', spec: 'Venom Spitter', query: 'Did Dilophosaurus actually spit venom scientifically?' },
  { id: 'tri', emoji: '🛡️', name: 'Triceratops', spec: 'Herbivore Shield', query: 'Summarize Triceratops skeletal structure and dimensions.' },
  { id: 'brachio', emoji: '🦕', name: 'Brachiosaurus', spec: 'Sauropod Giant', query: 'How many kilograms of food did a Brachiosaurus eat daily?' }
];

const suggestions = [
  { text: 'Did dinosaurs have feathers?', query: 'Did dinosaurs really have feathers?' },
  { text: 'Which was the smartest?', query: 'Which dinosaur was the most intelligent?' },
  { text: 'Largest herbivore', query: 'What was the largest herbivorous dinosaur?' }
];

const logsDatabase = [
  { text: "PADDOCK GRID 09: 10,000V ACTIVE", type: "success" },
  { text: "DNA SEQUENCER: 98.4% CODING COMPATIBILITY", type: "success" },
  { text: "INFRARED SCANNER: 3 SIGNATURES DETECTED SECTOR 4", type: "success" },
  { text: "WEATHER MONITOR: HEAVY CLOUD COVER REPORTED", type: "success" },
  { text: "THERMAL IMAGING: COLD BLOOD SPECTRAL MATCHING", type: "warning" },
  { text: "COMMUNICATION RELAY: ESTABLISHING SECURE SATELLITE LINK...", type: "success" },
  { text: "RETRIEVAL SYSTEM: CHROMADB EMBEDDING CORRESPONDENCE NOMINAL", type: "success" },
  { text: "ISLA NUBLAR GEOTHERMAL POWER GENERATION STATUS: STABLE", type: "success" },
  { text: "SECURITY LOCKDOWN: TOUR TRACK VEHICLE AUTOPILOT LOCK ON", type: "success" },
  { text: "WARNING: COMPACT RADAR RE-CALIBRATING SWEEP ANGLE", type: "warning" },
  { text: "ANOMALY: PADDOCK 11 MOTION FLICKER IDENTIFIED - DINO RETURNING", type: "warning" },
  { text: "RAG STORAGE CORRESPONDENCE COMPILING SUCCESSFUL", type: "success" }
];

export default function App() {
  const [messages, setMessages] = useState([
    {
      id: 'init',
      text: "Greetings! I am JurassiPedia, your secure prehistoric database expert system. The connection is established. Please transmit your dinosaur inquiries.",
      sender: 'bot'
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [logs, setLogs] = useState([]);
  const [particles, setParticles] = useState([]);
  const [webSearch, setWebSearch] = useState(false);
  const [activeSource, setActiveSource] = useState(null);

  const chatBoxRef = useRef(null);
  const logBoxRef = useRef(null);

  // Initialize ambient background particles
  useEffect(() => {
    const list = Array.from({ length: 22 }, (_, idx) => {
      const size = Math.random() * 5 + 2;
      const left = Math.random() * 100;
      const delay = Math.random() * -20;
      const duration = Math.random() * 18 + 10;
      return { id: idx, size, left, delay, duration };
    });
    setParticles(list);
  }, []);

  // System Diagnostics logs updates
  useEffect(() => {
    const initialLogs = [];
    const now = new Date();
    for (let i = 0; i < 6; i++) {
      const logTime = new Date(now.getTime() - (6 - i) * 6000);
      const timeStr = logTime.toTimeString().split(' ')[0];
      const template = logsDatabase[Math.floor(Math.random() * logsDatabase.length)];
      initialLogs.push({ time: timeStr, text: template.text, type: template.type });
    }
    setLogs(initialLogs);

    const logInterval = setInterval(() => {
      const timeStr = new Date().toTimeString().split(' ')[0];
      const template = logsDatabase[Math.floor(Math.random() * logsDatabase.length)];
      setLogs(prev => {
        const next = [...prev, { time: timeStr, text: template.text, type: template.type }];
        if (next.length > 20) {
          next.shift();
        }
        return next;
      });
    }, 5000);

    return () => clearInterval(logInterval);
  }, []);

  // Auto-scroll boxes to bottom
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages, isSearching]);

  useEffect(() => {
    if (logBoxRef.current) {
      logBoxRef.current.scrollTop = logBoxRef.current.scrollHeight;
    }
  }, [logs]);

  // Transmit query to backend API
  const handleSend = async (customMessage = "") => {
    const query = (customMessage || inputText).trim();
    if (!query || isSearching) return;

    // 1. Add User Message
    const userMsgId = 'user-' + Date.now();
    setMessages(prev => [...prev, { id: userMsgId, text: query, sender: 'user' }]);
    setInputText("");
    setIsSearching(true);

    const botMsgId = 'bot-' + Date.now();

    // Construct history array
    const chatHistory = messages
      .filter(m => m.id !== 'init' && !m.id.startsWith('err') && !m.id.startsWith('net'))
      .map(m => ({
        role: m.sender === 'user' ? 'user' : 'assistant',
        content: m.text
      }));

    try {
      // 2. Fetch from FastAPI
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          message: query,
          history: chatHistory,
          web_search: webSearch
        })
      });

      setIsSearching(false);

      if (!response.ok) {
        const errText = await response.text();
        const errId = 'err-' + Date.now();
        setMessages(prev => [...prev, { 
          id: errId, 
          text: `⚠️ System processing error: ${errText || 'unknown cause'}`, 
          sender: 'bot' 
        }]);
        return;
      }

      // Add placeholder bot message
      setMessages(prev => [...prev, { 
        id: botMsgId, 
        text: "", 
        sender: 'bot',
        sources: [],
        retrievalMs: null,
        generationMs: null,
        isStreaming: true
      }]);

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const cleanLine = line.trim();
          if (cleanLine.startsWith("data: ")) {
            const dataStr = cleanLine.slice(6).trim();
            if (!dataStr) continue;
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.type === 'meta') {
                setMessages(prev => prev.map(m => m.id === botMsgId ? {
                  ...m,
                  sources: parsed.sources || [],
                  retrievalMs: parsed.retrieval_ms
                } : m));
              } else if (parsed.type === 'token') {
                setMessages(prev => prev.map(m => m.id === botMsgId ? {
                  ...m,
                  text: m.text + parsed.text
                } : m));
              } else if (parsed.type === 'done') {
                setMessages(prev => prev.map(m => m.id === botMsgId ? {
                  ...m,
                  generationMs: parsed.generation_ms,
                  faithfulness: parsed.faithfulness,
                  relevance: parsed.relevance,
                  isStreaming: false
                } : m));
              } else if (parsed.type === 'error') {
                setMessages(prev => prev.map(m => m.id === botMsgId ? {
                  ...m,
                  text: m.text + `\n⚠️ [Mainframe Error] ${parsed.text}`,
                  isStreaming: false
                } : m));
              }
            } catch (e) {
              console.error("Error parsing stream chunk:", e);
            }
          }
        }
      }

    } catch (error) {
      setIsSearching(false);
      const networkErrId = 'net-' + Date.now();
      setMessages(prev => [...prev, { 
        id: networkErrId, 
        text: "❌ Transmission failure: Unable to establish contact with the mainframe database. Please check your FastAPI (uvicorn) server process.", 
        sender: 'bot' 
      }]);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  // Helper parsing functions to render markdown bolding (**text**) and lists (* item) in React JSX
  const renderInlineFormatting = (text) => {
    if (!text) return "";
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={index} style={{ color: 'var(--accent-green)', fontWeight: 'bold' }}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  const renderMessageText = (text, isStreaming = false) => {
    if (!text && !isStreaming) return null;
    if (!text && isStreaming) {
      return <div className="bullet-point"><span className="terminal-cursor">▋</span></div>;
    }
    const lines = text.split('\n');
    return lines.map((line, index) => {
      const isLastLine = index === lines.length - 1;
      const trimmed = line.trim();
      if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
        const content = trimmed.substring(2);
        return (
          <div key={index} className="bullet-point" style={{ display: 'flex', gap: '8px', margin: '6px 0 6px 16px' }}>
            <span style={{ color: 'var(--accent-green)' }}>•</span>
            <div>
              {renderInlineFormatting(content)}
              {isStreaming && isLastLine && <span className="terminal-cursor">▋</span>}
            </div>
          </div>
        );
      }
      return (
        <div key={index} style={{ minHeight: line === '' ? '12px' : 'auto', marginBottom: '4px' }}>
          {renderInlineFormatting(line)}
          {isStreaming && isLastLine && <span className="terminal-cursor">▋</span>}
        </div>
      );
    });
  };

  return (
    <>
      {/* Background aesthetics */}
      <div className="crt-overlay"></div>
      <div className="scanline"></div>
      <div id="particlesContainer">
        {particles.map(p => (
          <div
            key={p.id}
            className="particle"
            style={{
              width: `${p.size}px`,
              height: `${p.size}px`,
              left: `${p.left}vw`,
              bottom: '-30px',
              opacity: 0.3,
              animation: `floatParticleAnimation ${p.duration}s linear infinite`,
              animationDelay: `${p.delay}s`
            }}
          />
        ))}
      </div>

      {/* Main Header title */}
      <header className="main-header">
        <div className="logo-container">
          <h1 className="logo">JurassiPedia</h1>
          <div className="subtitle">
            🦖 SECURE PREHISTORIC ARCHIVE // LVL ALPHA
          </div>
        </div>
      </header>

      {/* Main Dashboard Layout */}
      <div className="dashboard-grid">
        
        {/* Left panel: Dino catalog search index */}
        <aside className="side-panel">
          <div className="panel-header">
            <span>PREHISTORIC DIRECTORY</span>
            <span style={{ color: 'var(--accent-amber)' }}>SPECIES CATALOG</span>
          </div>
          <div className="catalog-list">
            {dinoDirectory.map(dino => (
              <div 
                key={dino.id} 
                className="dino-card" 
                onClick={() => handleSend(dino.query)}
              >
                <div className="dino-avatar">{dino.emoji}</div>
                <div className="dino-details">
                  <div className="dino-name">{dino.name}</div>
                  <div className="dino-spec">{dino.spec}</div>
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Center Panel: Chat interface */}
        <main className="chat-panel">
          <div className="chat-control-bar">
            <div className="status-indicator">
              <span className="status-dot pulsing"></span>
              <span>SECURE DATA LINK</span>
            </div>
            
            {/* Satellite Search Toggle */}
            <div className="satellite-toggle" style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }} onClick={() => setWebSearch(prev => !prev)}>
              <span className="status-dot" style={{ 
                backgroundColor: webSearch ? 'var(--accent-amber)' : 'rgba(255, 255, 255, 0.2)',
                boxShadow: webSearch ? '0 0 8px var(--accent-amber)' : 'none',
                width: '6px',
                height: '6px',
                borderRadius: '50%'
              }}></span>
              <span style={{ fontSize: '11px', color: webSearch ? 'var(--accent-amber)' : 'rgba(255,255,255,0.4)', fontFamily: 'var(--font-mono)' }}>
                SATELLITE UPLINK: {webSearch ? 'ONLINE' : 'OFFLINE'}
              </span>
            </div>
            
            <div className="operator-tag">OPERATOR: ACTIVE</div>
          </div>

          {/* Messages scroll box */}
          <div className="chat-box" id="chatBox" ref={chatBoxRef}>
            {messages.map(msg => (
              <div 
                key={msg.id} 
                className={`message ${msg.sender === 'user' ? 'user-msg' : 'bot-msg'}`}
              >
                {renderMessageText(msg.text, msg.isStreaming)}
                
                {/* Sources & Telemetry metadata */}
                {msg.sender === 'bot' && (msg.sources?.length > 0 || msg.retrievalMs !== null || msg.generationMs !== null) && (
                  <div className="message-meta-footer" style={{
                    marginTop: '12px',
                    borderTop: '1px solid rgba(0, 255, 65, 0.12)',
                    paddingTop: '8px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px'
                  }}>
                    {/* Telemetry Badge */}
                    {(msg.retrievalMs !== null || msg.generationMs !== null || msg.faithfulness !== undefined || msg.relevance !== undefined) && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <div className="telemetry-row" style={{
                          fontSize: '9px',
                          color: 'rgba(0, 255, 65, 0.45)',
                          display: 'flex',
                          gap: '12px',
                          fontFamily: 'var(--font-mono)',
                          letterSpacing: '1px'
                        }}>
                          {msg.retrievalMs !== null && (
                            <span>RETRIEVAL_LATENCY: <strong style={{ color: 'var(--accent-amber)' }}>{msg.retrievalMs}ms</strong></span>
                          )}
                          {msg.generationMs !== null && (
                            <span>GENERATION_LATENCY: <strong style={{ color: 'var(--accent-green)' }}>{msg.generationMs}ms</strong></span>
                          )}
                        </div>
                        
                        {/* Evaluation Metrics */}
                        {(msg.faithfulness !== undefined || msg.relevance !== undefined) && (
                          <div className="telemetry-row" style={{
                            fontSize: '9px',
                            color: 'rgba(0, 255, 65, 0.45)',
                            display: 'flex',
                            gap: '12px',
                            fontFamily: 'var(--font-mono)',
                            letterSpacing: '1px'
                          }}>
                            {msg.faithfulness !== undefined && msg.faithfulness !== null && (
                              <span>FAITHFULNESS: <strong style={{ color: msg.faithfulness >= 80 ? 'var(--accent-green)' : 'var(--accent-amber)' }}>{msg.faithfulness}%</strong></span>
                            )}
                            {msg.relevance !== undefined && msg.relevance !== null && (
                              <span>ANSWER_RELEVANCE: <strong style={{ color: msg.relevance >= 80 ? 'var(--accent-green)' : 'var(--accent-amber)' }}>{msg.relevance}%</strong></span>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Source citations */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="citations-container">
                        <div style={{
                          fontSize: '10px',
                          color: 'var(--accent-amber)',
                          marginBottom: '4px',
                          fontFamily: 'var(--font-mono)',
                          letterSpacing: '1px'
                        }}>
                          SOURCES_FOUND:
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {Array.from(new Set(msg.sources.map(s => JSON.stringify(s)))).map((strObj, idx) => {
                            const srcObj = JSON.parse(strObj);
                            const label = srcObj.label || srcObj;
                            const content = srcObj.content || "No snippet content available.";

                            const parts = label.split("::");
                            const name = parts[0];
                            const score = parts[1];
                            const isWeb = name.includes("🌐");
                            const filename = name.replace(/\\/g, '/').split('/').pop().replace("🌐", "").trim();
                            
                            // Check if score is a valid match percentage (numbers only)
                            const isNumericScore = !isNaN(score) && score !== '0';
                            const scoreText = isNumericScore ? `(${score}% Match)` : (score ? `(${score})` : '');
                            
                            return (
                              <span 
                                key={idx} 
                                className="source-citation-badge" 
                                onClick={() => setActiveSource({ label: name, scoreText, content })}
                                style={{
                                  fontSize: '10px',
                                  background: isWeb ? 'rgba(0, 168, 255, 0.05)' : 'rgba(212, 175, 55, 0.05)',
                                  border: isWeb ? '1px solid rgba(0, 168, 255, 0.2)' : '1px solid rgba(212, 175, 55, 0.2)',
                                  color: isWeb ? '#00a8ff' : 'var(--accent-amber)',
                                  padding: '2px 6px',
                                  borderRadius: '3px',
                                  fontFamily: 'var(--font-mono)',
                                  textTransform: 'uppercase',
                                  cursor: 'pointer'
                                }}
                              >
                                {isWeb ? '🌐' : '📁'} {filename} {scoreText}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            {isSearching && (
              <div className="message bot-msg" style={{ opacity: 0.85 }}>
                Retrieving data records and cross-referencing genetic profiles...
              </div>
            )}
          </div>

          {/* Quick Suggestion Chips */}
          <div className="suggestions-row">
            {suggestions.map((chip, idx) => (
              <span 
                key={idx} 
                className="suggestion-chip" 
                onClick={() => handleSend(chip.query)}
              >
                {chip.text}
              </span>
            ))}
          </div>

          {/* Text Input Row */}
          <div className="input-area">
            <input 
              type="text" 
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Input transmission query here..."
            />
            <button onClick={() => handleSend()} className="send-btn">
              <span>TRANSMIT</span>
              <svg className="send-icon" viewBox="0 0 24 24" width="16" height="16">
                <path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>
        </main>

        {/* Right panel: Radar scanner & Diagnostics telemetry */}
        <aside className="side-panel">
          <div className="panel-header">
            <span>GRID MONITOR</span>
            <span style={{ color: 'var(--accent-red)' }}>SECTOR 4</span>
          </div>
          
          {/* Sweeping radar widget */}
          <div className="radar-widget">
            <div className="radar">
              <div className="radar-sweep"></div>
              <div className="radar-ring ring-1"></div>
              <div className="radar-ring ring-2"></div>
              <div className="radar-ring ring-3"></div>
              <div className="radar-crosshair-h"></div>
              <div className="radar-crosshair-v"></div>
              <div className="blip blip-1"></div>
              <div className="blip blip-2"></div>
              <div className="blip blip-3"></div>
            </div>
          </div>

          <div className="panel-header">
            <span>SYSTEM DIAGNOSTICS</span>
            <span className="stat-val-ok">SECURE</span>
          </div>

          {/* Status Metrics list */}
          <div className="system-stats">
            <div className="stat-row">
              <span>FENCE VOLTAGE:</span>
              <span className="stat-val-ok">10,000 V // ONLINE</span>
            </div>
            <div className="stat-row">
              <span>DNA SEQUENCER:</span>
              <span className="stat-val-ok">ACTIVE</span>
            </div>
            <div className="stat-row">
              <span>RETRIEVAL SYSTEM:</span>
              <span className="stat-val-ok">GROQ-LLAMA3-RAG</span>
            </div>
            <div className="stat-row">
              <span>VECTOR INDEX:</span>
              <span className="stat-val-ok">CHROMADB</span>
            </div>
          </div>

          <div className="panel-header">
            <span>SECURITY FEED LOGS</span>
          </div>

          {/* Diagnostic dynamic logs box */}
          <div className="system-logs" id="systemLogs" ref={logBoxRef}>
            {logs.map((log, idx) => (
              <div key={idx} className="log-entry">
                <span className="log-time">[{log.time}]</span>
                <span className={log.type === 'warning' ? 'log-warning' : 'log-success'}>
                  {log.text}
                </span>
              </div>
            ))}
          </div>
        </aside>

      </div>

      {/* Citations Preview sliding drawer */}
      {activeSource && (
        <div className="source-drawer-overlay" onClick={() => setActiveSource(null)}>
          <div className="source-drawer" onClick={e => e.stopPropagation()}>
            <div className="drawer-header">
              <span>SOURCE PREVIEW RECORD</span>
              <button className="close-btn" onClick={() => setActiveSource(null)}>✖ CLOSE</button>
            </div>
            <div className="drawer-body">
              <div className="drawer-meta-row" style={{ marginBottom: '12px' }}>
                <strong style={{ color: 'var(--accent-amber)' }}>SOURCE RECORD:</strong> <span style={{ color: '#fff', wordBreak: 'break-all' }}>{activeSource.label}</span>
              </div>
              {activeSource.scoreText && (
                <div className="drawer-meta-row" style={{ marginBottom: '16px' }}>
                  <strong style={{ color: 'var(--accent-green)' }}>MATCH METRIC:</strong> <span style={{ color: 'var(--accent-green)' }}>{activeSource.scoreText}</span>
                </div>
              )}
              <hr style={{ border: 'none', borderTop: '1px solid rgba(0, 255, 65, 0.15)', margin: '16px 0' }} />
              <div className="drawer-content-box">
                <div className="content-title" style={{ fontSize: '11px', color: 'var(--accent-amber)', marginBottom: '8px', textTransform: 'uppercase' }}>
                  Extracted Context Snippet:
                </div>
                <pre className="content-text" style={{
                  flex: 1,
                  margin: 0,
                  background: 'rgba(0, 255, 65, 0.02)',
                  border: '1px solid rgba(0, 255, 65, 0.15)',
                  borderRadius: '4px',
                  padding: '14px',
                  fontSize: '11.5px',
                  color: 'var(--accent-green)',
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'var(--font-mono)',
                  overflowY: 'auto',
                  lineHeight: '1.5'
                }}>{activeSource.content}</pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Embedded Sci-Fi styles */}
      <style>{`
        @keyframes blinkCursor {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
        .terminal-cursor {
          color: var(--accent-green);
          animation: blinkCursor 0.8s steps(2, start) infinite;
          display: inline-block;
          vertical-align: middle;
          font-weight: bold;
          margin-left: 3px;
        }
        .source-drawer-overlay {
          position: fixed;
          top: 0;
          left: 0;
          width: 100vw;
          height: 100vh;
          background: rgba(0, 0, 0, 0.7);
          backdrop-filter: blur(3px);
          z-index: 1000;
          display: flex;
          justify-content: flex-end;
        }
        .source-drawer {
          width: 440px;
          height: 100%;
          background: #020902;
          border-left: 2px solid var(--accent-green);
          box-shadow: -10px 0 30px rgba(0, 255, 65, 0.12);
          display: flex;
          flex-direction: column;
          padding: 24px;
          font-family: var(--font-mono);
          box-sizing: border-box;
          animation: slideInDrawer 0.25s ease-out;
        }
        @keyframes slideInDrawer {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
        .drawer-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          border-bottom: 2px solid var(--accent-green);
          padding-bottom: 12px;
          margin-bottom: 20px;
        }
        .drawer-header span {
          font-size: 13px;
          font-weight: bold;
          color: var(--accent-green);
          letter-spacing: 2px;
        }
        .drawer-header .close-btn {
          background: none;
          border: 1px solid var(--accent-red);
          color: var(--accent-red);
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 10px;
          cursor: pointer;
          font-family: inherit;
        }
        .drawer-header .close-btn:hover {
          background: rgba(255, 0, 0, 0.15);
          box-shadow: 0 0 8px var(--accent-red);
        }
        .drawer-body {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-height: 0;
        }
        .drawer-content-box {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-height: 0;
        }
      `}</style>
    </>
  );
}
