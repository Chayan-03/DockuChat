import remarkGfm from "remark-gfm";
import ReactMarkdown from "react-markdown";
import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  Upload, FileText, Trash2, Settings, Send, Loader, XCircle,
  User, ChevronsRight, Sparkles, Eye, EyeOff, Clipboard
} from 'lucide-react'; 

export const ChatWindow = ({ messages }) => {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="space-y-6">
      {messages.map((msg, index) => (
        <div
          key={index}
          className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          {/* ✅ Replace Bot icon with custom image */}
          {msg.role === 'assistant' && (
            <img
              src="/icon.jpg"   // make sure icon.jpg is inside /public
              alt="Bot"
              className="w-8 h-8 flex-shrink-0 rounded-full object-cover"
            />
          )}

          <div
            className={`max-w-xl p-4 rounded-xl shadow-md ${
              msg.role === 'user'
                ? 'bg-gray-800'
                : 'bg-gray-900 border border-gray-800'
            }`}
          >
            <div
              className="prose prose-invert max-w-none"
              dangerouslySetInnerHTML={{
                __html: msg.content.replace(/\n/g, '<br />'),
              }}
            />
          </div>

          {/* Keep user icon as is */}
          {msg.role === 'user' && (
            <User className="w-8 h-8 flex-shrink-0 bg-gray-700 p-1.5 rounded-full" />
          )}
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};
