import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Vector Search Index Management
export const createIndex = async (description, dimensions = 768, indexAlgorithm = 'brute_force') => {
  const response = await api.post('/index/create', {
    description,
    dimensions,
    index_algorithm: indexAlgorithm,
  });
  return response.data;
};

export const getIndexInfo = async () => {
  const response = await api.get('/index/info');
  return response.data;
};

export const clearIndexDatapoints = async () => {
  const response = await api.post('/index/clear');
  return response.data;
};

export const deleteIndex = async () => {
  const response = await api.delete('/index/delete');
  return response.data;
};

// Document Management
export const importDocuments = async (documents, bucketName = null) => {
  const response = await api.post('/documents/import', {
    documents,
    bucket_name: bucketName,
  });
  return response.data;
};

export const uploadDocument = async (file, documentDate = null, chunkSize = 1000, chunkOverlap = 200) => {
  const formData = new FormData();
  formData.append('file', file);
  if (documentDate) {
    formData.append('document_date', documentDate);
  }
  formData.append('chunk_size', chunkSize.toString());
  formData.append('chunk_overlap', chunkOverlap.toString());

  const response = await api.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const importFromGCS = async (gcsPath, documentDate = null, recursive = true, chunkSize = 1000, chunkOverlap = 200) => {
  const formData = new FormData();
  formData.append('gcs_path', gcsPath);
  if (documentDate) {
    formData.append('document_date', documentDate);
  }
  formData.append('recursive', recursive.toString());
  formData.append('chunk_size', chunkSize.toString());
  formData.append('chunk_overlap', chunkOverlap.toString());

  const response = await api.post('/documents/import_from_gcs', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// Query
export const queryIndex = async (query, topK = 5, temporalFilter = null) => {
  const response = await api.post('/query', {
    query,
    top_k: topK,
    temporal_filter: temporalFilter,
  });
  return response.data;
};

// Get Document by ID
export const getDocument = async (documentId) => {
  const response = await api.get(`/documents/${documentId}`);
  return response.data;
};

// Chat
export const sendChatMessage = async (message, conversationHistory = null, sessionId = null, userId = 'default_user') => {
  const response = await api.post('/chat', {
    message,
    conversation_history: conversationHistory,
    session_id: sessionId,
    user_id: userId,
  });
  return response.data;
};

// Temporal Context
export const extractTemporalContext = async (text) => {
  const response = await api.post('/temporal/extract', { text });
  return response.data;
};

export default api;
