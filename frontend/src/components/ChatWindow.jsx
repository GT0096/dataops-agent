import React from 'react';

export default function ChatWindow({ messages }) {
    return (
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg, idx) => (
                <div
                    key={idx}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                    <div
                        className={`max-w-3xl rounded-lg px-4 py-2 ${msg.role === 'user'
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-200 text-gray-900'
                            }`}
                    >
                        <div className="font-medium text-sm mb-1">
                            {msg.role === 'user' ? 'You' : 'Assistant'}
                        </div>
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                    </div>
                </div>
            ))}
        </div>
    );
}
