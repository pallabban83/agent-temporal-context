import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import LinkIcon from '@mui/icons-material/Link';
import DescriptionIcon from '@mui/icons-material/Description';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import ClearIcon from '@mui/icons-material/Clear';
import AddCommentIcon from '@mui/icons-material/AddComment';
import SourceIcon from '@mui/icons-material/Source';
import ReactMarkdown from 'react-markdown';
import { sendChatMessage } from '../api';

function ChatInterface() {
  // Load messages and sessionId from localStorage on mount
  const [messages, setMessages] = useState(() => {
    const savedMessages = localStorage.getItem('chatMessages');
    return savedMessages ? JSON.parse(savedMessages) : [];
  });
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(() => {
    return localStorage.getItem('chatSessionId') || null;
  });
  const messagesEndRef = useRef(null);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('chatMessages', JSON.stringify(messages));
  }, [messages]);

  // Save sessionId to localStorage whenever it changes
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('chatSessionId', sessionId);
    }
  }, [sessionId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = inputMessage;
    setInputMessage('');
    setError(null);

    // Add user message to chat
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: userMessage, timestamp: new Date().toISOString() },
    ]);

    setLoading(true);

    try {
      // Build conversation history
      const conversationHistory = messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));

      // Send to agent with session ID
      const response = await sendChatMessage(userMessage, conversationHistory, sessionId);

      if (response.success) {
        // Store session_id from response to maintain conversation
        if (response.data.session_id) {
          setSessionId(response.data.session_id);
        }

        const agentMessage = {
          role: 'assistant',
          content: response.data.response,
          toolResults: response.data.tool_results,
          timestamp: response.data.timestamp,
        };

        setMessages((prev) => [...prev, agentMessage]);
      } else {
        setError('Failed to get response from agent');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setSessionId(null);
    localStorage.removeItem('chatMessages');
    localStorage.removeItem('chatSessionId');
  };

  const handleNewSession = () => {
    // Clear chat history and session
    setMessages([]);
    setSessionId(null);
    localStorage.removeItem('chatMessages');
    localStorage.removeItem('chatSessionId');

    // Show a system message indicating new session started
    const systemMessage = {
      role: 'assistant',
      content: 'New session started. How can I help you today?',
      timestamp: new Date().toISOString(),
    };
    setMessages([systemMessage]);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          <Typography variant="h5" gutterBottom>
            Chat with Temporal RAG Agent
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Ask the agent to create a corpus, import documents, or query for information with temporal context.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="contained"
            color="primary"
            size="small"
            startIcon={<AddCommentIcon />}
            onClick={handleNewSession}
          >
            New Session
          </Button>
          <Button
            variant="outlined"
            color="error"
            size="small"
            startIcon={<ClearIcon />}
            onClick={handleClearChat}
            disabled={messages.length === 0}
          >
            Clear Chat
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Chat Messages */}
      <Paper
        variant="outlined"
        sx={{
          height: 400,
          overflowY: 'auto',
          p: 2,
          mb: 2,
          backgroundColor: '#fafafa',
        }}
      >
        {messages.length === 0 ? (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: 'text.secondary',
            }}
          >
            <Typography>Start a conversation with the agent...</Typography>
          </Box>
        ) : (
          messages.map((message, index) => (
            <Box key={index} sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                {message.role === 'user' ? (
                  <PersonIcon sx={{ mr: 1, color: 'primary.main' }} />
                ) : (
                  <SmartToyIcon sx={{ mr: 1, color: 'secondary.main' }} />
                )}
                <Typography variant="subtitle2" fontWeight="bold">
                  {message.role === 'user' ? 'You' : 'Agent'}
                </Typography>
                <Typography variant="caption" sx={{ ml: 1, color: 'text.secondary' }}>
                  {new Date(message.timestamp).toLocaleTimeString()}
                </Typography>
              </Box>

              <Paper sx={{ p: 1.5, backgroundColor: message.role === 'user' ? '#e3f2fd' : '#fff' }}>
                {message.role === 'user' ? (
                  <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                    {message.content}
                  </Typography>
                ) : (
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <Typography variant="body1" sx={{ mb: 1 }}>{children}</Typography>,
                      strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
                      em: ({ children }) => <em>{children}</em>,
                      ul: ({ children }) => <ul style={{ marginLeft: '1.5rem', marginBottom: '0.5rem' }}>{children}</ul>,
                      ol: ({ children }) => <ol style={{ marginLeft: '1.5rem', marginBottom: '0.5rem' }}>{children}</ol>,
                      li: ({ children }) => <li style={{ marginBottom: '0.25rem' }}>{children}</li>,
                      code: ({ inline, children }) => inline ? (
                        <code style={{ backgroundColor: '#f5f5f5', padding: '2px 4px', borderRadius: '3px', fontFamily: 'monospace' }}>
                          {children}
                        </code>
                      ) : (
                        <pre style={{ backgroundColor: '#f5f5f5', padding: '8px', borderRadius: '4px', overflow: 'auto' }}>
                          <code style={{ fontFamily: 'monospace' }}>{children}</code>
                        </pre>
                      )
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                )}

                {/* Sources Section - Show documents with rerank scores */}
                {message.toolResults && message.toolResults.some(tool =>
                  tool.tool === 'query_corpus' && tool.result.success && tool.result.result?.results
                ) && (
                  <Box sx={{ mt: 2, p: 2, backgroundColor: '#f8f9fa', borderRadius: 2, border: '1px solid #e0e0e0' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
                      <SourceIcon color="primary" />
                      <Typography variant="h6" fontWeight="bold">
                        Sources
                      </Typography>
                    </Box>
                    {message.toolResults
                      .filter(tool => tool.tool === 'query_corpus' && tool.result.success && tool.result.result?.results)
                      .map((tool, toolIdx) => (
                        <Box key={toolIdx}>
                          {/* Only show the first (most relevant) result */}
                          {tool.result.result.results.slice(0, 1).map((result, idx) => (
                            <Paper
                              key={idx}
                              elevation={1}
                              sx={{
                                p: 2,
                                backgroundColor: '#fff',
                                border: '2px solid #1976d2'
                              }}
                            >
                              {/* Title and Most Relevant badge */}
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                                <Typography variant="subtitle1" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flex: 1, pr: 2 }}>
                                  <DescriptionIcon fontSize="small" color="primary" />
                                  {result.title || 'Document'}
                                </Typography>
                                <Chip
                                  label="Most Relevant"
                                  color="primary"
                                  size="small"
                                  sx={{ flexShrink: 0 }}
                                />
                              </Box>

                              {/* Similarity Score */}
                              <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                                {result.score !== undefined && (
                                  <Chip
                                    label={`Similarity: ${(result.score * 100).toFixed(1)}%`}
                                    size="small"
                                    color="primary"
                                    sx={{ fontWeight: 'bold' }}
                                  />
                                )}
                              </Box>

                              {/* Content Preview */}
                              {result.content_preview && (
                                <Typography variant="body2" sx={{ mb: 1.5, color: 'text.secondary', fontStyle: 'italic' }}>
                                  {result.content_preview}
                                </Typography>
                              )}

                              {/* Citation and Link */}
                              {result.citation && (
                                <Box>
                                  {result.citation.formatted && (
                                    <Typography variant="caption" display="block" sx={{ mb: 1, color: 'text.secondary' }}>
                                      {result.citation.formatted}
                                    </Typography>
                                  )}
                                  {result.citation.clickable_link && (
                                    <Button
                                      variant="outlined"
                                      size="small"
                                      startIcon={<LinkIcon />}
                                      href={result.citation.clickable_link}
                                      target="_blank"
                                      sx={{ textTransform: 'none' }}
                                    >
                                      View Source
                                    </Button>
                                  )}
                                </Box>
                              )}
                            </Paper>
                          ))}
                        </Box>
                      ))}
                  </Box>
                )}

                {/* Show tool results if any */}
                {message.toolResults && message.toolResults.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Divider sx={{ mb: 1 }} />
                    {message.toolResults.map((tool, idx) => (
                      <Accordion key={idx} sx={{ mt: 1 }}>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Chip
                              label={tool.tool}
                              size="small"
                              color={tool.result.success ? 'success' : 'error'}
                            />
                            <Typography variant="caption" color="text.secondary">
                              {tool.result.success ? 'Completed' : 'Failed'}
                            </Typography>
                          </Box>
                        </AccordionSummary>
                        <AccordionDetails>
                          {/* Display query results with citations */}
                          {tool.tool === 'query_corpus' && tool.result.success && tool.result.result?.results ? (
                            <Box>
                              <Typography variant="caption" color="text.secondary" gutterBottom>
                                Found {tool.result.result.results.length} result(s)
                              </Typography>
                              {tool.result.result.results.map((result, ridx) => (
                                <Paper key={ridx} elevation={1} sx={{ p: 2, mt: 1, backgroundColor: '#f5f5f5' }}>
                                  {/* Title and Score */}
                                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                    <Typography variant="subtitle2" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                      <DescriptionIcon fontSize="small" />
                                      {result.title || `Document ${ridx + 1}`}
                                    </Typography>
                                    <Chip
                                      label={`${(result.score * 100).toFixed(1)}%`}
                                      size="small"
                                      color="primary"
                                    />
                                  </Box>

                                  {/* Content Preview */}
                                  {result.content_preview && (
                                    <Typography variant="body2" sx={{ mb: 1, fontStyle: 'italic', fontSize: '0.85rem' }}>
                                      {result.content_preview}
                                    </Typography>
                                  )}

                                  {/* Images */}
                                  {result.images && result.images.length > 0 && (
                                    <Box sx={{ mb: 1 }}>
                                      <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                                        Images ({result.images.length}):
                                      </Typography>
                                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                        {result.images.map((image, imgIdx) => (
                                          <Box
                                            key={imgIdx}
                                            sx={{
                                              cursor: 'pointer',
                                              '&:hover': { opacity: 0.8 }
                                            }}
                                            onClick={() => window.open(image.url, '_blank')}
                                          >
                                            <Box
                                              component="img"
                                              src={image.url}
                                              alt={image.description || `Image ${imgIdx + 1}`}
                                              sx={{
                                                maxWidth: 150,
                                                maxHeight: 100,
                                                borderRadius: 1,
                                                border: '1px solid #ddd',
                                                objectFit: 'cover'
                                              }}
                                            />
                                            {image.description && (
                                              <Typography
                                                variant="caption"
                                                sx={{
                                                  display: 'block',
                                                  mt: 0.5,
                                                  fontSize: '0.65rem',
                                                  maxWidth: 150,
                                                  overflow: 'hidden',
                                                  textOverflow: 'ellipsis',
                                                  whiteSpace: 'nowrap'
                                                }}
                                              >
                                                {image.description}
                                              </Typography>
                                            )}
                                          </Box>
                                        ))}
                                      </Box>
                                    </Box>
                                  )}

                                  {/* Citation */}
                                  {result.citation && (
                                    <>
                                      <Typography variant="caption" display="block" gutterBottom>
                                        {result.citation.formatted}
                                      </Typography>
                                      {result.citation.clickable_link && (
                                        <Button
                                          variant="outlined"
                                          size="small"
                                          startIcon={<LinkIcon />}
                                          href={result.citation.clickable_link}
                                          target="_blank"
                                          sx={{ mt: 1, textTransform: 'none' }}
                                        >
                                          View Source
                                        </Button>
                                      )}
                                    </>
                                  )}

                                  {/* Metadata */}
                                  {result.citation && (
                                    <Box sx={{ display: 'flex', gap: 0.5, mt: 1, flexWrap: 'wrap' }}>
                                      {result.citation.date && (
                                        <Chip icon={<AccessTimeIcon />} label={result.citation.date} size="small" variant="outlined" />
                                      )}
                                    </Box>
                                  )}
                                </Paper>
                              ))}
                            </Box>
                          ) : (
                            <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem' }}>
                              {JSON.stringify(tool.result, null, 2)}
                            </Typography>
                          )}
                        </AccordionDetails>
                      </Accordion>
                    ))}
                  </Box>
                )}
              </Paper>
            </Box>
          ))
        )}
        <div ref={messagesEndRef} />
      </Paper>

      {/* Input Area */}
      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          multiline
          maxRows={4}
          placeholder="Type your message..."
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <Button
          variant="contained"
          onClick={handleSendMessage}
          disabled={loading || !inputMessage.trim()}
          endIcon={loading ? <CircularProgress size={20} /> : <SendIcon />}
        >
          Send
        </Button>
      </Box>

      {/* Example prompts */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="caption" color="text.secondary">
          Try asking:
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
          {[
            'Create a new corpus for financial documents',
            'Show me information about the current corpus',
            'Import a document about Q4 2023 earnings',
          ].map((example, idx) => (
            <Chip
              key={idx}
              label={example}
              size="small"
              onClick={() => setInputMessage(example)}
              sx={{ cursor: 'pointer' }}
            />
          ))}
        </Box>
      </Box>
    </Box>
  );
}

export default ChatInterface;
