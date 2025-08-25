import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  Upload, FileText, Trash2, Settings, Send, Loader, XCircle,
  Bot, User, ChevronsRight, Sparkles, Eye, EyeOff, Clipboard
} from 'lucide-react';


export const ErrorMessage = ({ message, onDismiss }) => (
  <div className="p-4 mx-6 mb-4 bg-red-900 border border-red-700 rounded-lg flex items-center justify-between shadow">
    <p>{message}</p>
    <button onClick={onDismiss} className="text-red-300 hover:text-white">
      <XCircle size={20} />
    </button>
  </div>
);