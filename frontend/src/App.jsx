import React, { useState } from 'react';
import ChatWindow from './components/ChatWindow';
import InputBar from './components/InputBar';
import EnvironmentSelector from './components/EnvironmentSelector';
import ToolTracePanel from './components/ToolTracePanel';
import { chatAPI } from './services/api';

function App() {
    const [messages, setMessages] = useState([]);
    const [environment, setEnvironment] = useState('dev');
    const [isLoading, setIsLoading] = useState(false);
    const [toolTraces, setToolTraces] = useState([]);
    const [showTraces, setShowTraces] = useState(false);

    const handleSend = async (userMessage) => {
        // Add user message
        const newMessages = [
            ...messages,
            { role: 'user', content: userMessage },
        ];
        setMessages(newMessages);
        setIsLoading(true);

        try {
            // Send to backend
            const response = await chatAPI.sendMessage(
                userMessage,
                environment,
                messages
            );

            // Add assistant response
            setMessages([
                ...newMessages,
                { role: 'assistant', content: response.message },
            ]);

            // Update tool traces
            if (response.tool_traces) {
                setToolTraces((prev) => [...prev, ...response.tool_traces]);
            }
        } catch (error) {
            console.error('Chat error:', error);
            setMessages([
                ...newMessages,
                {
                    role: 'assistant',
                    content: `Error: ${error.message}`,
                },
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-screen bg-gray-50">
            {/* Header */}
            <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
                <h1 className="text-xl font-bold text-gray-800">MCP DataOps Assistant</h1>
                <EnvironmentSelector
                    environment={environment}
                    onChange={setEnvironment}
                />
            </header>

            {/* Chat */}
            <ChatWindow messages={messages} />

            {/* Loading indicator */}
            {isLoading && (
                <div className="px-4 py-2 text-sm text-gray-500">
                    Processing your request...
                </div>
            )}

            {/* Input */}
            <InputBar onSend={handleSend} disabled={isLoading} />

            {/* Tool Traces */}
            <ToolTracePanel
                traces={toolTraces}
                isOpen={showTraces}
                onToggle={() => setShowTraces(!showTraces)}
            />
        </div>
    );
}

export default App;
