import React from 'react';

export default function EnvironmentSelector({ environment, onChange }) {
    return (
        <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Environment:</span>
            <select
                value={environment}
                onChange={(e) => onChange(e.target.value)}
                className="rounded border border-gray-300 px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
                <option value="dev">Development</option>
                <option value="prod">Production</option>
            </select>
        </div>
    );
}
