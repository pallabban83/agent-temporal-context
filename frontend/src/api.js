import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Vector Search Infrastructure Management
export const createVectorSearchInfrastructure = async (description, dimensions = 768, indexAlgorithm = 'brute_force') => {
  const response = await api.post('/vector-search/create', {
    description,
    dimensions,
    index_algorithm: indexAlgorithm,
  });
  return response.data;
};

// Corpus Management
export const createCorpus = async (description, dimensions = 768) => {
  const response = await api.post('/corpus/create', { description, dimensions });
  return response.data;
};

export const getCorpusInfo = async () => {
  const response = await api.get('/corpus/info');
  return response.data;
};

export const clearDatapoints = async () => {
  const response = await api.post('/corpus/clear-datapoints');
  return response.data;
};

export const registerExistingDocuments = async () => {
  const response = await api.post('/corpus/register-existing-documents');
  return response.data;
};

// Diagnostics and Repair
export const runDiagnostics = async () => {
  const response = await api.get('/corpus/diagnostics');
  return response.data;
};

export const rebuildMetadata = async () => {
  const response = await api.post('/corpus/rebuild-metadata');
  return response.data;
};

export const fullRepair = async () => {
  const response = await api.post('/corpus/full-repair');
  return response.data;
};

export const deleteVectorSearchInfrastructure = async () => {
  const response = await api.delete('/vector-search/delete');
  return response.data;
};

export const deleteCorpus = async () => {
  const response = await api.delete('/corpus/delete');
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

// Query
export const queryCorpus = async (query, topK = 5, temporalFilter = null) => {
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
