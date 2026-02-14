import { useState, useEffect } from 'react';

// Debug API URL
const DEBUG_API_URL = import.meta.env.VITE_API_URL?.replace('/chat', '/chat/debug') || 'http://127.0.0.1:5000/chat/debug';

// Pipeline stage definitions for visualization
const PIPELINE_STAGES = [
    { id: 1, name: 'Input', icon: '📥', description: 'Raw message received' },
    { id: 2, name: 'Context Manager', icon: '📋', description: 'Session & history' },
    { id: 3, name: 'Reference Resolution', icon: '🔗', description: 'Resolve "it", "that"' },
    { id: 4, name: 'Emotion Detection', icon: '😊', description: 'Analyze sentiment' },
    { id: 5, name: 'Entity Extraction', icon: '🏷️', description: 'Products, quantities' },
    { id: 6, name: 'Intent Detection', icon: '🎯', description: 'Semantic + Fuzzy NLU' },
    { id: 7, name: 'Dialog Manager', icon: '💬', description: 'Multi-turn flows' },
    { id: 8, name: 'Response Generator', icon: '⚙️', description: 'Template or LLM' },
    { id: 9, name: 'Output', icon: '📤', description: 'Final response' }
];

const PipelineDebugger = ({ isMaximized, onToggleMaximize, onClose }) => {
    const [input, setInput] = useState('');
    const [currentStep, setCurrentStep] = useState(0);
    const [stagesData, setStagesData] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState(null);

    // Reset debugger
    const handleReset = () => {
        setCurrentStep(0);
        setStagesData(null);
        setError(null);
        setInput('');
    };

    // Process message through pipeline
    const handleProcess = async () => {
        if (!input.trim()) return;

        setIsProcessing(true);
        setError(null);
        setCurrentStep(0);

        try {
            const response = await fetch(DEBUG_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: input,
                    sessionId: 'debug_' + Date.now()
                })
            });

            const data = await response.json();

            if (data.error) {
                setError(data.error);
            } else {
                setStagesData(data.stages);
                setCurrentStep(1); // Start at first stage
            }
        } catch (err) {
            setError('Failed to connect to debug API: ' + err.message);
        } finally {
            setIsProcessing(false);
        }
    };

    // Navigate stages
    const handlePrev = () => {
        if (currentStep > 1) setCurrentStep(currentStep - 1);
    };

    const handleNext = () => {
        if (stagesData && currentStep < stagesData.length) {
            setCurrentStep(currentStep + 1);
        }
    };

    // Get current stage data
    const getCurrentStageData = () => {
        if (!stagesData || currentStep === 0) return null;
        return stagesData.find(s => s.id === currentStep);
    };

    // Format JSON for display
    const formatJson = (data) => {
        return JSON.stringify(data, null, 2);
    };

    return (
        <div className={`pipeline-debugger ${isMaximized ? 'maximized' : ''}`}>
            {/* Header */}
            <div className="pipeline-header">
                <span className="pipeline-title">🔧 Pipeline Debugger</span>
                <div className="pipeline-controls">
                    <button
                        className="pipeline-btn"
                        onClick={onToggleMaximize}
                        title={isMaximized ? 'Minimize' : 'Maximize'}
                    >
                        {isMaximized ? '🗗' : '🗖'}
                    </button>
                    <button
                        className="pipeline-btn"
                        onClick={onClose}
                        title="Close"
                    >
                        ✕
                    </button>
                </div>
            </div>

            {/* Input Area */}
            <div className="pipeline-input-area">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleProcess()}
                    placeholder="Enter message to debug..."
                    className="pipeline-input"
                    disabled={isProcessing}
                />
                <button
                    onClick={handleProcess}
                    className="pipeline-send-btn"
                    disabled={isProcessing || !input.trim()}
                >
                    {isProcessing ? '⏳' : '▶ Process'}
                </button>
                <button
                    onClick={handleReset}
                    className="pipeline-reset-btn"
                    title="Reset"
                >
                    ↺
                </button>
            </div>

            {/* Architecture Diagram */}
            <div className="pipeline-architecture">
                <div className="pipeline-stages-row pipeline-row-1">
                    {PIPELINE_STAGES.slice(0, 5).map((stage) => (
                        <div
                            key={stage.id}
                            className={`pipeline-stage ${currentStep === stage.id ? 'active' :
                                currentStep > stage.id ? 'complete' : 'pending'
                                }`}
                            onClick={() => stagesData && stage.id <= stagesData.length && setCurrentStep(stage.id)}
                        >
                            <div className="stage-icon">{stage.icon}</div>
                            <div className="stage-name">{stage.name}</div>
                            <div className="stage-id">#{stage.id}</div>
                        </div>
                    ))}
                </div>

                <div className="pipeline-connector">
                    <div className="connector-line"></div>
                    <div className="connector-arrow">▼</div>
                </div>

                <div className="pipeline-stages-row pipeline-row-2">
                    {PIPELINE_STAGES.slice(5).reverse().map((stage) => (
                        <div
                            key={stage.id}
                            className={`pipeline-stage ${currentStep === stage.id ? 'active' :
                                currentStep > stage.id ? 'complete' : 'pending'
                                }`}
                            onClick={() => stagesData && stage.id <= stagesData.length && setCurrentStep(stage.id)}
                        >
                            <div className="stage-icon">{stage.icon}</div>
                            <div className="stage-name">{stage.name}</div>
                            <div className="stage-id">#{stage.id}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Step Controls */}
            <div className="pipeline-step-controls">
                <button
                    onClick={handlePrev}
                    disabled={currentStep <= 1}
                    className="step-btn"
                >
                    ◀ Prev
                </button>
                <span className="step-indicator">
                    {currentStep > 0 ? `Step ${currentStep} of ${stagesData?.length || 9}` : 'Enter message to start'}
                </span>
                <button
                    onClick={handleNext}
                    disabled={!stagesData || currentStep >= stagesData.length}
                    className="step-btn"
                >
                    Next ▶
                </button>
            </div>

            {/* Data Package Viewer */}
            <div className="pipeline-data-viewer">
                <div className="data-header">
                    <span className="data-title">📦 Data Package</span>
                    {getCurrentStageData() && (
                        <span className="data-timing">
                            ⏱ {getCurrentStageData().duration_ms}ms
                        </span>
                    )}
                </div>

                <div className="data-content">
                    {error && (
                        <div className="data-error">
                            ❌ Error: {error}
                        </div>
                    )}

                    {!stagesData && !error && (
                        <div className="data-placeholder">
                            Enter a message above and click "Process" to see the pipeline in action.
                        </div>
                    )}

                    {getCurrentStageData() && (
                        <>
                            {/* Code Module Info */}
                            {getCurrentStageData().code && (
                                <div className="code-module-info">
                                    <div className="code-module-header">📁 Code Module</div>
                                    <div className="code-module-row">
                                        <span className="code-label">Module:</span>
                                        <span className="code-value">{getCurrentStageData().code.module}</span>
                                    </div>
                                    <div className="code-module-row">
                                        <span className="code-label">Function:</span>
                                        <span className="code-value code-function">{getCurrentStageData().code.function}</span>
                                    </div>
                                    {getCurrentStageData().code.class && (
                                        <div className="code-module-row">
                                            <span className="code-label">Class:</span>
                                            <span className="code-value">{getCurrentStageData().code.class}</span>
                                        </div>
                                    )}
                                    {getCurrentStageData().code.library && (
                                        <div className="code-module-row">
                                            <span className="code-label">Library:</span>
                                            <span className="code-value code-library">{getCurrentStageData().code.library}</span>
                                        </div>
                                    )}
                                    <div className="code-module-desc">
                                        {getCurrentStageData().code.description}
                                    </div>
                                </div>
                            )}

                            {/* Data Package */}
                            <div className="data-package-header">📦 Data Package</div>
                            <pre className="data-json">
                                {formatJson(getCurrentStageData().data)}
                            </pre>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default PipelineDebugger;
