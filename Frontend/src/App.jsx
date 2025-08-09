// Filename: src/App.jsx
// First, ensure you have installed the necessary packages:
// npm install axios lucide-react
// And set up Tailwind CSS according to the official Vite guide.

import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { Upload, FileText, Trash2, Settings, Send, Loader, XCircle, Bot, User, ChevronsRight, Sparkles } from 'lucide-react';

// Base URL for your FastAPI backend
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
            setIsApiKeyModalOpen(true); // Prompt for API key if not found
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
        <div className="flex h-screen bg-gray-900 text-white font-sans">
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
                <main className="flex-1 p-4 md:p-6 flex flex-col overflow-y-auto">
                    {selectedDocument ? (
                        <ChatWindow messages={messages} />
                    ) : (
                        <WelcomeScreen />
                    )}
                </main>

                {error && <ErrorMessage message={error} onDismiss={() => setError(null)} />}

                <div className="p-4 md:p-6 bg-gray-900 border-t border-gray-700">
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

// --- Sidebar Component ---
const Sidebar = ({ documents, selectedDocument, onSelectDocument, fetchDocuments, apiKey, setError, isOpen, setIsOpen, onSettingsClick }) => {
    const fileInputRef = useRef(null);

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            await axios.post(`${API_URL}/upload/`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                    'gemini-api-key': apiKey
                }
            });
            fetchDocuments();
        } catch (err) {
            console.error("Error uploading file:", err);
            setError(err.response?.data?.detail || "Failed to upload file.");
        }
    };

    const handleDeleteDocument = async (docName, e) => {
        e.stopPropagation();
        if (window.confirm(`Are you sure you want to delete ${docName}? This action cannot be undone.`)) {
            try {
                await axios.delete(`${API_URL}/documents/${docName}`);
                fetchDocuments();
                if (selectedDocument === docName) {
                    onSelectDocument(null);
                }
            } catch (err) {
                console.error("Error deleting document:", err);
                setError(err.response?.data?.detail || "Failed to delete document.");
            }
        }
    };

    return (
        <>
            <div className={`flex-shrink-0 bg-gray-800 flex flex-col transition-all duration-300 overflow-hidden ${isOpen ? 'w-64 md:w-72' : 'w-0'}`}>
                <div className="flex-1 p-4 overflow-y-auto">
                    <button
                        onClick={() => fileInputRef.current.click()}
                        className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg p-3 mb-4 transition-colors"
                    >
                        <Upload size={20} />
                        <span>Upload Document</span>
                    </button>
                    {/* *** FIX: Added .xlsx and .xls to the accept attribute *** */}
                    <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".pdf,.jpg,.jpeg,.png,.csv,.xlsx,.xls" />

                    <h2 className="text-lg font-semibold mb-2 text-gray-300">Documents</h2>
                    <div className="space-y-2">
                        {documents.map(doc => (
                            <div
                                key={doc}
                                onClick={() => onSelectDocument(doc)}
                                className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${selectedDocument === doc ? 'bg-indigo-500' : 'bg-gray-700 hover:bg-gray-600'}`}
                            >
                                <div className="flex items-center gap-3 overflow-hidden">
                                    <FileText size={18} className="flex-shrink-0" />
                                    <span className="truncate" title={doc}>{doc}</span>
                                </div>
                                <button onClick={(e) => handleDeleteDocument(doc, e)} className="text-gray-400 hover:text-red-500 flex-shrink-0">
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="p-4 border-t border-gray-700">
                    <button onClick={onSettingsClick} className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-gray-700 transition-colors">
                        <Settings size={20} />
                        <span>API Key Settings</span>
                    </button>
                </div>
            </div>
            <button onClick={() => setIsOpen(!isOpen)} className="bg-gray-800 h-12 self-center rounded-r-lg px-1 text-gray-400 hover:bg-gray-700 z-10">
                <ChevronsRight className={`transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
            </button>
        </>
    );
};

// --- Chat Window Component ---
const ChatWindow = ({ messages }) => {
    const messagesEndRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    return (
        <div className="space-y-6">
            {messages.map((msg, index) => (
                <div key={index} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {msg.role === 'assistant' && <Bot className="w-8 h-8 flex-shrink-0 bg-indigo-600 p-1.5 rounded-full" />}
                    <div className={`max-w-xl p-4 rounded-xl shadow-md ${msg.role === 'user' ? 'bg-gray-700' : 'bg-gray-800'}`}>
                        <div className="prose prose-invert max-w-none" dangerouslySetInnerHTML={{ __html: msg.content.replace(/\n/g, '<br />') }}></div>
                    </div>
                    {msg.role === 'user' && <User className="w-8 h-8 flex-shrink-0 bg-gray-600 p-1.5 rounded-full" />}
                </div>
            ))}
            <div ref={messagesEndRef} />
        </div>
    );
};

// --- Welcome Screen Component ---
const WelcomeScreen = () => (
    <div className="flex flex-col items-center justify-center h-full text-center">
        <Sparkles className="w-16 h-16 text-indigo-400 mb-4" />
        <h1 className="text-3xl font-bold mb-2">Multimodal RAG Assistant</h1>
        <p className="text-gray-400">Upload a document and select it from the sidebar to begin.</p>
    </div>
);


// --- Query Input Component ---
const QueryInput = ({ query, setQuery, onSendQuery, isLoading, disabled }) => {
    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSendQuery();
        }
    };

    return (
        <div className="relative">
      <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={disabled ? "Please select a document to start chatting" : "Ask a question about the selected document..."}
          className="w-full bg-gray-800 border border-gray-600 rounded-lg p-4 pr-12 resize-none focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          rows="1"
          disabled={disabled || isLoading}
      />
            <button
                onClick={onSendQuery}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-indigo-500 disabled:text-gray-600 disabled:cursor-not-allowed"
                disabled={isLoading || !query.trim()}
            >
                {isLoading ? <Loader className="animate-spin" size={24} /> : <Send size={24} />}
            </button>
        </div>
    );
};

// --- API Key Modal Component ---
const ApiKeyModal = ({ isOpen, onClose, onSave }) => {
    const [key, setKey] = useState('');

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50">
            <div className="bg-gray-800 rounded-lg p-8 w-full max-w-md shadow-xl">
                <h2 className="text-2xl font-bold mb-4">Enter Gemini API Key</h2>
                <p className="text-gray-400 mb-6">Your API key is stored only in your browser's local storage and is never sent anywhere except to the Gemini API via your backend.</p>
                <input
                    type="password"
                    value={key}
                    onChange={(e) => setKey(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg p-3 mb-6 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    placeholder="Enter your API key..."
                />
                <div className="flex justify-end gap-4">
                    <button onClick={onClose} className="px-4 py-2 rounded-lg bg-gray-600 hover:bg-gray-700 transition-colors">Cancel</button>
                    <button onClick={() => onSave(key)} className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 transition-colors">Save Key</button>
                </div>
            </div>
        </div>
    );
};

// --- Error Message Component ---
const ErrorMessage = ({ message, onDismiss }) => (
    <div className="p-4 mx-6 mb-4 bg-red-900 border border-red-700 rounded-lg flex items-center justify-between">
        <p>{message}</p>
        <button onClick={onDismiss} className="text-red-300 hover:text-white">
            <XCircle size={20} />
        </button>
    </div>
);



// // Filename: src/App.jsx
// // First, ensure you have installed the necessary packages:
// // npm install axios lucide-react
// // And set up Tailwind CSS according to the official Vite guide.
//
// import React, { useState, useEffect, useRef, useCallback } from 'react';
// import axios from 'axios';
// import { Upload, FileText, Trash2, Settings, Send, Loader, XCircle, Bot, User, ChevronsRight, Sparkles, HelpCircle } from 'lucide-react';
//
// // Base URL for your FastAPI backend
// const API_URL = 'http://127.0.0.1:8000';
//
// // --- Main App Component ---
// export default function App() {
//     const [apiKey, setApiKey] = useState('');
//     const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);
//
//     const [documents, setDocuments] = useState([]);
//     const [selectedDocument, setSelectedDocument] = useState(null);
//
//     const [messages, setMessages] = useState([]);
//     const [query, setQuery] = useState('');
//     const [isLoading, setIsLoading] = useState(false);
//     const [error, setError] = useState(null);
//
//     const [sidebarOpen, setSidebarOpen] = useState(true);
//
//     // Load API key from local storage on initial render
//     useEffect(() => {
//         const storedApiKey = localStorage.getItem('geminiApiKey');
//         if (storedApiKey) {
//             setApiKey(storedApiKey);
//         } else {
//             setIsApiKeyModalOpen(true); // Prompt for API key if not found
//         }
//     }, []);
//
//     // Fetch the list of documents from the backend
//     const fetchDocuments = useCallback(async () => {
//         try {
//             const response = await axios.get(`${API_URL}/documents/`);
//             setDocuments(response.data);
//         } catch (err) {
//             console.error("Error fetching documents:", err);
//             setError("Could not fetch documents. Is the backend server running?");
//         }
//     }, []);
//
//     useEffect(() => {
//         fetchDocuments();
//     }, [fetchDocuments]);
//
//     // Handle document selection
//     const handleSelectDocument = (doc) => {
//         if (selectedDocument === doc) {
//             setSelectedDocument(null);
//             setMessages([]);
//         } else {
//             setSelectedDocument(doc);
//             setMessages([{
//                 role: 'assistant',
//                 content: `You can now ask questions about the document: **${doc}**`
//             }]);
//         }
//     };
//
//     // Handle sending a query to the backend
//     const handleSendQuery = async () => {
//         if (!query.trim() || !selectedDocument || isLoading) return;
//
//         setIsLoading(true);
//         setError(null);
//         const userMessage = { role: 'user', content: query };
//         setMessages(prev => [...prev, userMessage]);
//         setQuery('');
//
//         try {
//             const response = await axios.post(
//                 `${API_URL}/query/${selectedDocument}`,
//                 null,
//                 {
//                     params: { query },
//                     headers: { 'gemini-api-key': apiKey }
//                 }
//             );
//             const assistantMessage = { role: 'assistant', content: response.data.answer };
//             setMessages(prev => [...prev, assistantMessage]);
//         } catch (err) {
//             console.error("Error sending query:", err);
//             const errorMessage = err.response?.data?.detail || "An unexpected error occurred while querying.";
//             setError(errorMessage);
//             setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${errorMessage}` }]);
//         } finally {
//             setIsLoading(false);
//         }
//     };
//
//     return (
//         <div className="flex h-screen bg-gray-900 text-white font-sans">
//             <ApiKeyModal
//                 isOpen={isApiKeyModalOpen}
//                 onClose={() => setIsApiKeyModalOpen(false)}
//                 onSave={(key) => {
//                     setApiKey(key);
//                     localStorage.setItem('geminiApiKey', key);
//                     setIsApiKeyModalOpen(false);
//                 }}
//             />
//
//             <Sidebar
//                 documents={documents}
//                 selectedDocument={selectedDocument}
//                 onSelectDocument={handleSelectDocument}
//                 fetchDocuments={fetchDocuments}
//                 apiKey={apiKey}
//                 setError={setError}
//                 isOpen={sidebarOpen}
//                 setIsOpen={setSidebarOpen}
//                 onSettingsClick={() => setIsApiKeyModalOpen(true)}
//             />
//
//             <div className="flex-1 flex flex-col transition-all duration-300">
//                 <main className="flex-1 p-4 md:p-6 flex flex-col overflow-y-auto">
//                     {selectedDocument ? (
//                         <ChatWindow messages={messages} />
//                     ) : (
//                         <WelcomeScreen />
//                     )}
//                 </main>
//
//                 {error && <ErrorMessage message={error} onDismiss={() => setError(null)} />}
//
//                 <div className="p-4 md:p-6 bg-gray-900 border-t border-gray-700">
//                     <QueryInput
//                         query={query}
//                         setQuery={setQuery}
//                         onSendQuery={handleSendQuery}
//                         isLoading={isLoading}
//                         disabled={!selectedDocument}
//                     />
//                 </div>
//             </div>
//         </div>
//     );
// }
//
// // --- Sidebar Component ---
// const Sidebar = ({ documents, selectedDocument, onSelectDocument, fetchDocuments, apiKey, setError, isOpen, setIsOpen, onSettingsClick }) => {
//     const fileInputRef = useRef(null);
//
//     const handleFileUpload = async (event) => {
//         const file = event.target.files[0];
//         if (!file) return;
//
//         const formData = new FormData();
//         formData.append('file', file);
//
//         try {
//             await axios.post(`${API_URL}/upload/`, formData, {
//                 headers: {
//                     'Content-Type': 'multipart/form-data',
//                     'gemini-api-key': apiKey
//                 }
//             });
//             fetchDocuments();
//         } catch (err) {
//             console.error("Error uploading file:", err);
//             setError(err.response?.data?.detail || "Failed to upload file.");
//         }
//     };
//
//     const handleDeleteDocument = async (docName, e) => {
//         e.stopPropagation();
//         if (window.confirm(`Are you sure you want to delete ${docName}? This action cannot be undone.`)) {
//             try {
//                 await axios.delete(`${API_URL}/documents/${docName}`);
//                 fetchDocuments();
//                 if (selectedDocument === docName) {
//                     onSelectDocument(null);
//                 }
//             } catch (err) {
//                 console.error("Error deleting document:", err);
//                 setError(err.response?.data?.detail || "Failed to delete document.");
//             }
//         }
//     };
//
//     return (
//         <>
//             <div className={`flex-shrink-0 bg-gray-800 flex flex-col transition-all duration-300 overflow-hidden ${isOpen ? 'w-64 md:w-72' : 'w-0'}`}>
//                 <div className="flex-1 p-4 overflow-y-auto">
//                     <button
//                         onClick={() => fileInputRef.current.click()}
//                         className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg p-3 mb-4 transition-colors"
//                     >
//                         <Upload size={20} />
//                         <span>Upload Document</span>
//                     </button>
//                     <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".pdf,.jpg,.jpeg,.png,.csv" />
//
//                     <h2 className="text-lg font-semibold mb-2 text-gray-300">Documents</h2>
//                     <div className="space-y-2">
//                         {documents.map(doc => (
//                             <div
//                                 key={doc}
//                                 onClick={() => onSelectDocument(doc)}
//                                 className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${selectedDocument === doc ? 'bg-indigo-500' : 'bg-gray-700 hover:bg-gray-600'}`}
//                             >
//                                 <div className="flex items-center gap-3 overflow-hidden">
//                                     <FileText size={18} className="flex-shrink-0" />
//                                     <span className="truncate" title={doc}>{doc}</span>
//                                 </div>
//                                 <button onClick={(e) => handleDeleteDocument(doc, e)} className="text-gray-400 hover:text-red-500 flex-shrink-0">
//                                     <Trash2 size={16} />
//                                 </button>
//                             </div>
//                         ))}
//                     </div>
//                 </div>
//                 <div className="p-4 border-t border-gray-700">
//                     <button onClick={onSettingsClick} className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-gray-700 transition-colors">
//                         <Settings size={20} />
//                         <span>API Key Settings</span>
//                     </button>
//                 </div>
//             </div>
//             <button onClick={() => setIsOpen(!isOpen)} className="bg-gray-800 h-12 self-center rounded-r-lg px-1 text-gray-400 hover:bg-gray-700 z-10">
//                 <ChevronsRight className={`transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
//             </button>
//         </>
//     );
// };
//
// // --- Chat Window Component ---
// const ChatWindow = ({ messages }) => {
//     const messagesEndRef = useRef(null);
//
//     useEffect(() => {
//         messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
//     }, [messages]);
//
//     return (
//         <div className="space-y-6">
//             {messages.map((msg, index) => (
//                 <div key={index} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
//                     {msg.role === 'assistant' && <Bot className="w-8 h-8 flex-shrink-0 bg-indigo-600 p-1.5 rounded-full" />}
//                     <div className={`max-w-xl p-4 rounded-xl shadow-md ${msg.role === 'user' ? 'bg-gray-700' : 'bg-gray-800'}`}>
//                         <div className="prose prose-invert max-w-none" dangerouslySetInnerHTML={{ __html: msg.content.replace(/\n/g, '<br />') }}></div>
//                     </div>
//                     {msg.role === 'user' && <User className="w-8 h-8 flex-shrink-0 bg-gray-600 p-1.5 rounded-full" />}
//                 </div>
//             ))}
//             <div ref={messagesEndRef} />
//         </div>
//     );
// };
//
// // --- Welcome Screen Component ---
// const WelcomeScreen = () => (
//     <div className="flex flex-col items-center justify-center h-full text-center">
//         <Sparkles className="w-16 h-16 text-indigo-400 mb-4" />
//         <h1 className="text-3xl font-bold mb-2">Multimodal RAG Assistant</h1>
//         <p className="text-gray-400">Upload a document and select it from the sidebar to begin.</p>
//     </div>
// );
//
//
// // --- Query Input Component ---
// const QueryInput = ({ query, setQuery, onSendQuery, isLoading, disabled }) => {
//     const handleKeyPress = (e) => {
//         if (e.key === 'Enter' && !e.shiftKey) {
//             e.preventDefault();
//             onSendQuery();
//         }
//     };
//
//     return (
//         <div className="relative">
//       <textarea
//           value={query}
//           onChange={(e) => setQuery(e.target.value)}
//           onKeyPress={handleKeyPress}
//           placeholder={disabled ? "Please select a document to start chatting" : "Ask a question about the selected document..."}
//           className="w-full bg-gray-800 border border-gray-600 rounded-lg p-4 pr-12 resize-none focus:ring-2 focus:ring-indigo-500 focus:outline-none"
//           rows="1"
//           disabled={disabled || isLoading}
//       />
//             <button
//                 onClick={onSendQuery}
//                 className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-indigo-500 disabled:text-gray-600 disabled:cursor-not-allowed"
//                 disabled={isLoading || !query.trim()}
//             >
//                 {isLoading ? <Loader className="animate-spin" size={24} /> : <Send size={24} />}
//             </button>
//         </div>
//     );
// };
//
// // --- API Key Modal Component ---
// const ApiKeyModal = ({ isOpen, onClose, onSave }) => {
//     const [key, setKey] = useState('');
//
//     if (!isOpen) return null;
//
//     return (
//         <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50">
//             <div className="bg-gray-800 rounded-lg p-8 w-full max-w-md shadow-xl">
//                 <h2 className="text-2xl font-bold mb-4">Enter Gemini API Key</h2>
//                 <p className="text-gray-400 mb-6">Your API key is stored only in your browser's local storage and is never sent anywhere except to the Gemini API via your backend.</p>
//                 <input
//                     type="password"
//                     value={key}
//                     onChange={(e) => setKey(e.target.value)}
//                     className="w-full bg-gray-700 border border-gray-600 rounded-lg p-3 mb-6 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
//                     placeholder="Enter your API key..."
//                 />
//                 <div className="flex justify-end gap-4">
//                     <button onClick={onClose} className="px-4 py-2 rounded-lg bg-gray-600 hover:bg-gray-700 transition-colors">Cancel</button>
//                     <button onClick={() => onSave(key)} className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 transition-colors">Save Key</button>
//                 </div>
//             </div>
//         </div>
//     );
// };
//
// // --- Error Message Component ---
// const ErrorMessage = ({ message, onDismiss }) => (
//     <div className="p-4 mx-6 mb-4 bg-red-900 border border-red-700 rounded-lg flex items-center justify-between">
//         <p>{message}</p>
//         <button onClick={onDismiss} className="text-red-300 hover:text-white">
//             <XCircle size={20} />
//         </button>
//     </div>
// );
