import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  Upload, FileText, Trash2, Settings, Send, Loader, XCircle,
  Bot, User, ChevronsRight, Sparkles, Eye, EyeOff, Clipboard
} from 'lucide-react';


export const WelcomeScreen = () => (
  <div className="flex flex-col items-center justify-center h-full text-center space-y-3">
    <Sparkles className="w-16 h-16 text-indigo-400 mb-4 animate-pulse" />
    <h1 className="text-3xl font-bold mb-2">Multimodal RAG Assistant</h1>
    <p className="text-gray-400">Upload a document and select it from the sidebar to begin.</p>
  </div>
);