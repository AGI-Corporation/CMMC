
import React, { useState } from 'react';

const ComplianceAdvisor: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/agents/mistral/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      const data = await response.json();
      setAnswer(data.answer);
    } catch (error) {
      console.error('Error asking advisor:', error);
      setAnswer('Sorry, I encountered an error while processing your request.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="bg-indigo-600 px-6 py-4">
        <h3 className="text-lg font-bold text-white">Mistral Compliance Advisor</h3>
        <p className="text-xs text-indigo-100 uppercase tracking-widest">AI-Powered CMMC & ZT Guidance</p>
      </div>
      <div className="p-6">
        <form onSubmit={handleAsk} className="mb-4">
          <textarea
            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
            rows={3}
            placeholder="Ask a compliance question (e.g., 'How do I implement AC.1.001?')"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          ></textarea>
          <button
            type="submit"
            disabled={loading}
            className="mt-2 w-full bg-indigo-600 text-white py-2 rounded-lg font-bold hover:bg-indigo-700 transition disabled:opacity-50"
          >
            {loading ? 'Consulting Mistral...' : 'Ask Advisor'}
          </button>
        </form>
        {answer && (
          <div className="mt-4 p-4 bg-indigo-50 rounded-lg border border-indigo-100">
            <h4 className="text-xs font-bold text-indigo-800 uppercase mb-2">Mistral's Response:</h4>
            <div className="text-sm text-gray-700 whitespace-pre-wrap">{answer}</div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ComplianceAdvisor;
