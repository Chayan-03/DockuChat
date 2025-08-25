import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  Upload, FileText, Trash2, Settings, Send, Loader, XCircle,
  Bot, User, ChevronsRight, Sparkles, Eye, EyeOff, Clipboard
} from 'lucide-react';



export const ApiKeyModal = ({ isOpen, onClose, onSave }) => {
  const [key, setKey] = useState('');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg p-8 w-full max-w-md shadow-xl border border-gray-800">
        <h2 className="text-2xl font-bold mb-4">Enter Gemini API Key</h2>
        <p className="text-gray-400 mb-6 text-sm">
          Your API key is stored only in your browser's local storage and is never sent anywhere except to the Gemini API via your backend.
        </p>
        <input
          type="password"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 mb-6 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          placeholder="Enter your API key..."
        />
        <div className="flex justify-end gap-4">
          <button onClick={onClose} className="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-800 transition-colors">Cancel</button>
          <button onClick={() => onSave(key)} className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 transition-colors">Save Key</button>
        </div>
      </div>
    </div>
  );
};
