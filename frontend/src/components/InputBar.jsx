import React, { useState } from 'react';

export default function InputBar({ onSend, disabled }) {
    const [input, setInput] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (input.trim() && !disabled) {
            onSend(input);
            setInput('');
        }
    };

    return (
        <form onSubmit={handleSubmit} className="flex gap-2 p-4 border-t border-gray-200 bg-white">
            <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about pipelines, secrets, logs, or infrastructure..."
                disabled={disabled}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
                type="submit"
                disabled={disabled || !input.trim()}
                className="rounded-lg bg-blue-500 px-6 py-2 text-white hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
                Send
            </button>
        </form>
    );
}
