import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  Upload, FileText, Trash2, Settings, Send, Loader, XCircle,
  Bot, User, ChevronsRight, Sparkles, Eye, EyeOff, Clipboard
} from 'lucide-react';

import { WelcomeScreen } from './components/WelcomeScreen';
import { QueryInput } from './components/QueryInput';
import { ChatWindow } from './components/ChatWindow';
import { Sidebar } from './components/Sidebar';
import { ApiKeyModal } from './components/ApikeyModal';
import { ErrorMessage } from './components/ErrorMessage';




// or any icons you prefer

const API_URL = 'http://127.0.0.1:8000';

// --- Main App Component ---
export default function App() {
  const [apiKey, setApiKey] = useState('');
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);

  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);

  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Load API key from local storage on initial render
  useEffect(() => {
    const storedApiKey = localStorage.getItem('geminiApiKey');
    if (storedApiKey) {
      setApiKey(storedApiKey);
    } else {
      setIsApiKeyModalOpen(true);
    }
  }, []);

  // Fetch the list of documents from the backend
  const fetchDocuments = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/documents/`);
      setDocuments(response.data);
    } catch (err) {
      console.error("Error fetching documents:", err);
      setError("Could not fetch documents. Is the backend server running?");
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Handle document selection
  const handleSelectDocument = (doc) => {
    if (selectedDocument === doc) {
      setSelectedDocument(null);
      setMessages([]);
    } else {
      setSelectedDocument(doc);
      setMessages([{
        role: 'assistant',
        content: `You can now ask questions about the document: **${doc}**`
      }]);
    }
  };

  // Handle sending a query to the backend
  const handleSendQuery = async () => {
    if (!query.trim() || !selectedDocument || isLoading) return;

    setIsLoading(true);
    setError(null);
    const userMessage = { role: 'user', content: query };
    setMessages(prev => [...prev, userMessage]);
    setQuery('');

    try {
      const response = await axios.post(
        `${API_URL}/query/${selectedDocument}`,
        null,
        {
          params: { query },
          headers: { 'gemini-api-key': apiKey }
        }
      );
      const assistantMessage = { role: 'assistant', content: response.data.answer };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Error sending query:", err);
      const errorMessage = err.response?.data?.detail || "An unexpected error occurred while querying.";
      setError(errorMessage);
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${errorMessage}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-950 text-white font-sans">
      <ApiKeyModal
        isOpen={isApiKeyModalOpen}
        onClose={() => setIsApiKeyModalOpen(false)}
        onSave={(key) => {
          setApiKey(key);
          localStorage.setItem('geminiApiKey', key);
          setIsApiKeyModalOpen(false);
        }}
      />

      <Sidebar
        documents={documents}
        selectedDocument={selectedDocument}
        onSelectDocument={handleSelectDocument}
        fetchDocuments={fetchDocuments}
        apiKey={apiKey}
        setError={setError}
        isOpen={sidebarOpen}
        setIsOpen={setSidebarOpen}
        onSettingsClick={() => setIsApiKeyModalOpen(true)}
      />

      <div className="flex-1 flex flex-col transition-all duration-300">
        <main className="flex-1 p-6 flex flex-col overflow-y-auto">
          {selectedDocument ? (
            <ChatWindow messages={messages} />
          ) : (
            <WelcomeScreen />
          )}
        </main>

        {error && <ErrorMessage message={error} onDismiss={() => setError(null)} />}

        <div className="p-4 bg-gray-900 border-t border-gray-700">
          <QueryInput
            query={query}
            setQuery={setQuery}
            onSendQuery={handleSendQuery}
            isLoading={isLoading}
            disabled={!selectedDocument}
          />
        </div>
      </div>
    </div>
  );
}



