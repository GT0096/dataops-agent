// API base URL - defaults to /api in production (nginx proxies to backend)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const chatAPI = {
    async sendMessage(message, environment = 'dev', history = []) {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message,
                environment,
                history,
            }),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || 'Failed to send message');
        }

        return response.json();
    },

    async checkHealth() {
        const response = await fetch(`${API_BASE_URL}/health`);
        return response.json();
    },
};
