import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  Upload, FileText, Trash2, Settings, Send, Loader, XCircle,
  Bot, User, ChevronsRight, Sparkles, Eye, EyeOff, Clipboard
} from 'lucide-react';



export const Sidebar = ({ documents, selectedDocument, onSelectDocument, fetchDocuments, apiKey, setError, isOpen, setIsOpen, onSettingsClick }) => {
  const fileInputRef = useRef(null);
  const [showKey, setShowKey] = useState(false);

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
      <div className={`flex-shrink-0 bg-gray-900 flex flex-col transition-all duration-300 overflow-hidden border-r border-gray-800 ${isOpen ? 'w-72' : 'w-0'}`}>
        <div className="flex-1 p-4 overflow-y-auto">
          <button
            onClick={() => fileInputRef.current.click()}
            className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg p-3 mb-4 transition-colors"
          >
            <Upload size={20} />
            <span>Upload Document</span>
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            className="hidden"
            accept=".pdf,.jpg,.jpeg,.png,.csv,.xlsx,.xls"
          />

          <h2 className="text-lg font-semibold mb-2 text-gray-300">Documents</h2>
          <div className="space-y-2">
            {documents.map(doc => (
              <div
                key={doc}
                onClick={() => onSelectDocument(doc)}
                className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${selectedDocument === doc ? 'bg-indigo-500' : 'bg-gray-800 hover:bg-gray-700'}`}
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
        <div className="p-4 border-t border-gray-800 space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Stored API Key</label>
            <div className="flex items-center gap-2">
              <input
                type={showKey ? "text" : "password"}
                value={apiKey || ""}
                readOnly
                className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2 text-sm"
              />
              <button
                onClick={() => setShowKey(!showKey)}
                className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
              >
                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(apiKey);
                  alert("API key copied!");
                }}
                className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
              >
                <Clipboard size={16} />
              </button>
            </div>
          </div>

          <button
            onClick={onSettingsClick}
            className="w-full flex items-center gap-3 p-3 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
          >
            <Settings size={20} />
            <span>Update API Key</span>
          </button>
        </div>
      </div>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="bg-gray-900 h-12 self-center rounded-r-lg px-1 text-gray-400 hover:bg-gray-800 z-10"
      >
        <ChevronsRight className={`transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
      </button>
    </>
  );
};