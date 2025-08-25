import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  Upload, FileText, Trash2, Settings, Send, Loader, XCircle,
  Bot, User, ChevronsRight, Sparkles, Eye, EyeOff, Clipboard
} from 'lucide-react';


export const QueryInput = ({ query, setQuery, onSendQuery, isLoading, disabled }) => {
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
        className="w-full bg-gray-900 border border-gray-700 rounded-lg p-4 pr-12 resize-none focus:ring-2 focus:ring-indigo-500 focus:outline-none"
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