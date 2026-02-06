import React from 'react';

export default function ToolTracePanel({ traces, isOpen, onToggle }) {
    if (!isOpen) {
        return (
            <button
                onClick={onToggle}
                className="fixed bottom-20 right-4 bg-gray-700 text-white px-4 py-2 rounded-lg hover:bg-gray-800"
            >
                Show Tool Traces ({traces.length})
            </button>
        );
    }

    return (
        <div className="fixed right-0 top-0 h-full w-96 bg-gray-800 text-white p-4 overflow-y-auto shadow-lg">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-bold">Tool Execution Traces</h2>
                <button
                    onClick={onToggle}
                    className="text-gray-400 hover:text-white text-xl"
                >
                    ✕
                </button>
            </div>
            <div className="space-y-4">
                {traces.map((trace, idx) => (
                    <div key={idx} className="bg-gray-700 rounded-lg p-3">
                        <div className="font-medium text-blue-400 mb-2">{trace.tool_name}</div>
                        <div className="text-sm">
                            <div className="text-gray-400 mb-1">Input:</div>
                            <pre className="bg-gray-900 p-2 rounded text-xs overflow-x-auto">
                                {JSON.stringify(trace.input_data, null, 2)}
                            </pre>
                        </div>
                        <div className="text-sm mt-2">
                            <div className="text-gray-400 mb-1">Output:</div>
                            <pre className="bg-gray-900 p-2 rounded text-xs overflow-x-auto max-h-40">
                                {JSON.stringify(trace.output_data, null, 2)}
                            </pre>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
