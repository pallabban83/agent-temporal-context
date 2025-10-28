import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Grid,
  Chip,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction
} from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import { importDocuments, uploadDocument } from '../api';

function DocumentImporter() {
  const [documents, setDocuments] = useState([]);
  const [currentDoc, setCurrentDoc] = useState({ content: '', metadata: {} });
  const [documentDate, setDocumentDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [file, setFile] = useState(null);
  const [chunkSize, setChunkSize] = useState(300);
  const [chunkOverlap, setChunkOverlap] = useState(60);

  const handleAddDocument = () => {
    if (!currentDoc.content.trim()) {
      setError('Document content cannot be empty');
      return;
    }

    const newDoc = {
      content: currentDoc.content,
      metadata: {
        ...currentDoc.metadata,
        ...(documentDate && { document_date: documentDate }),
        added_at: new Date().toISOString(),
      },
      id: `doc_${Date.now()}`,
    };

    setDocuments([...documents, newDoc]);
    setCurrentDoc({ content: '', metadata: {} });
    setDocumentDate('');
    setError(null);
  };

  const handleRemoveDocument = (index) => {
    setDocuments(documents.filter((_, i) => i !== index));
  };

  const handleImportDocuments = async () => {
    if (documents.length === 0) {
      setError('No documents to import');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await importDocuments(documents);

      if (response.success) {
        setSuccess(`Successfully imported ${documents.length} document(s)!`);
        setDocuments([]);
      } else {
        setError('Failed to import documents');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleUploadFile = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    // Validate chunk parameters
    if (chunkOverlap >= chunkSize) {
      setError('Chunk overlap must be less than chunk size');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await uploadDocument(
        file,
        documentDate || null,
        chunkSize,
        chunkOverlap
      );

      if (response.success) {
        setSuccess(`Successfully uploaded ${file.name}! (Chunk size: ${chunkSize}, Overlap: ${chunkOverlap})`);
        setFile(null);
        setDocumentDate('');
        // Reset file input
        document.getElementById('file-upload').value = '';
      } else {
        setError('Failed to upload file');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Import Documents
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Add documents to the RAG corpus. Supports PDF, DOCX, and text files. The system will extract temporal context automatically.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* File Upload Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <UploadFileIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h6">Upload File</Typography>
              </Box>

              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Supported formats: PDF, DOCX, TXT, MD, JSON
              </Typography>

              <input
                id="file-upload"
                type="file"
                accept=".pdf,.docx,.txt,.md,.json"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
              <label htmlFor="file-upload">
                <Button
                  variant="outlined"
                  component="span"
                  fullWidth
                  startIcon={<CloudUploadIcon />}
                >
                  Choose File
                </Button>
              </label>

              {file && (
                <Chip
                  label={file.name}
                  onDelete={() => setFile(null)}
                  sx={{ mt: 1 }}
                  color="primary"
                />
              )}

              <TextField
                fullWidth
                label="Document Date (Optional)"
                type="date"
                value={documentDate}
                onChange={(e) => setDocumentDate(e.target.value)}
                margin="normal"
                InputLabelProps={{ shrink: true }}
                helperText="Specify a date for temporal context"
              />

              <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                Chunking Configuration
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Chunk Size"
                    type="number"
                    value={chunkSize}
                    onChange={(e) => setChunkSize(parseInt(e.target.value) || 300)}
                    inputProps={{ min: 100, max: 5000, step: 100 }}
                    helperText="Characters per chunk"
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Chunk Overlap"
                    type="number"
                    value={chunkOverlap}
                    onChange={(e) => setChunkOverlap(parseInt(e.target.value) || 60)}
                    inputProps={{ min: 0, max: 500, step: 50 }}
                    helperText="Overlap between chunks"
                  />
                </Grid>
              </Grid>

              <Button
                fullWidth
                variant="contained"
                onClick={handleUploadFile}
                disabled={loading || !file}
                sx={{ mt: 2 }}
                startIcon={loading ? <CircularProgress size={20} /> : <UploadFileIcon />}
              >
                {loading ? 'Uploading...' : 'Upload & Import'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Manual Entry Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <AddIcon sx={{ mr: 1, color: 'success.main' }} />
                <Typography variant="h6">Add Document Manually</Typography>
              </Box>

              <TextField
                fullWidth
                label="Document Content"
                placeholder="Enter your document text here..."
                value={currentDoc.content}
                onChange={(e) =>
                  setCurrentDoc({ ...currentDoc, content: e.target.value })
                }
                margin="normal"
                multiline
                rows={6}
              />

              <TextField
                fullWidth
                label="Document Date (Optional)"
                type="date"
                value={documentDate}
                onChange={(e) => setDocumentDate(e.target.value)}
                margin="normal"
                InputLabelProps={{ shrink: true }}
                helperText="Specify a date for temporal context"
              />

              <Button
                fullWidth
                variant="outlined"
                onClick={handleAddDocument}
                sx={{ mt: 2 }}
                startIcon={<AddIcon />}
              >
                Add to Queue
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Document Queue */}
        {documents.length > 0 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Document Queue ({documents.length})
                </Typography>

                <List>
                  {documents.map((doc, index) => (
                    <ListItem key={doc.id} divider>
                      <ListItemText
                        primary={`Document ${index + 1}`}
                        secondary={
                          <>
                            {doc.content.substring(0, 100)}...
                            {doc.metadata.document_date && (
                              <Chip
                                label={`Date: ${doc.metadata.document_date}`}
                                size="small"
                                sx={{ ml: 1 }}
                              />
                            )}
                          </>
                        }
                      />
                      <ListItemSecondaryAction>
                        <IconButton
                          edge="end"
                          onClick={() => handleRemoveDocument(index)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))}
                </List>

                <Button
                  fullWidth
                  variant="contained"
                  onClick={handleImportDocuments}
                  disabled={loading}
                  sx={{ mt: 2 }}
                  startIcon={loading ? <CircularProgress size={20} /> : <CloudUploadIcon />}
                >
                  {loading ? 'Importing...' : `Import ${documents.length} Document(s)`}
                </Button>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}

export default DocumentImporter;
