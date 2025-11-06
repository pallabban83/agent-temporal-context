import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  CircularProgress,
  LinearProgress,
  Alert,
  Card,
  CardContent,
  Grid,
  Chip,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Checkbox
} from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CloudIcon from '@mui/icons-material/Cloud';
import FolderIcon from '@mui/icons-material/Folder';
import { importDocuments, uploadDocument, importFromGCS } from '../api';

function DocumentImporter() {
  const [documents, setDocuments] = useState([]);
  const [currentDoc, setCurrentDoc] = useState({ content: '', metadata: {} });
  const [documentDate, setDocumentDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [files, setFiles] = useState([]); // Changed to array for multiple files
  const [chunkSize, setChunkSize] = useState(1000);
  const [chunkOverlap, setChunkOverlap] = useState(200);
  const [gcsPath, setGcsPath] = useState('');
  const [gcsRecursive, setGcsRecursive] = useState(true);
  const [gcsResults, setGcsResults] = useState(null);
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 });
  const [gcsImporting, setGcsImporting] = useState(false);

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
    const selectedFiles = Array.from(event.target.files);
    setFiles(selectedFiles);
    setError(null);
  };

  const handleRemoveFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const handleUploadFile = async () => {
    if (files.length === 0) {
      setError('Please select at least one file');
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
    setUploadProgress({ current: 0, total: files.length });

    const successfulUploads = [];
    const failedUploads = [];

    try {
      // Upload files sequentially
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setUploadProgress({ current: i + 1, total: files.length });

        try {
          const response = await uploadDocument(
            file,
            documentDate || null,
            chunkSize,
            chunkOverlap
          );

          if (response.success) {
            successfulUploads.push(file.name);
          } else {
            failedUploads.push({ name: file.name, error: 'Upload failed' });
          }
        } catch (err) {
          failedUploads.push({ name: file.name, error: err.message });
        }
      }

      // Show results
      if (successfulUploads.length > 0) {
        setSuccess(
          `Successfully uploaded ${successfulUploads.length} of ${files.length} file(s)! (Chunk size: ${chunkSize}, Overlap: ${chunkOverlap})`
        );
      }

      if (failedUploads.length > 0) {
        setError(
          `Failed to upload ${failedUploads.length} file(s): ${failedUploads.map(f => f.name).join(', ')}`
        );
      }

      // Clear files if all successful
      if (failedUploads.length === 0) {
        setFiles([]);
        setDocumentDate('');
        // Reset file input
        document.getElementById('file-upload').value = '';
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
      setUploadProgress({ current: 0, total: 0 });
    }
  };

  const handleGCSImport = async () => {
    if (!gcsPath.trim()) {
      setError('Please enter a GCS path');
      return;
    }

    if (!gcsPath.startsWith('gs://')) {
      setError('GCS path must start with gs://');
      return;
    }

    // Validate chunk parameters
    if (chunkOverlap >= chunkSize) {
      setError('Chunk overlap must be less than chunk size');
      return;
    }

    setLoading(true);
    setGcsImporting(true);
    setError(null);
    setSuccess(null);
    setGcsResults(null);

    try {
      const response = await importFromGCS(gcsPath, documentDate, gcsRecursive, chunkSize, chunkOverlap);

      if (response.success) {
        setGcsResults(response.data);

        const successCount = response.data.files_imported || 0;
        const totalCount = response.data.files_found || 0;
        const failCount = response.data.files_failed || 0;

        if (successCount > 0) {
          setSuccess(
            `Successfully imported ${successCount} of ${totalCount} file${totalCount > 1 ? 's' : ''} from GCS! ` +
            `(Chunk size: ${chunkSize}, Overlap: ${chunkOverlap})` +
            (failCount > 0 ? ` | ${failCount} file${failCount > 1 ? 's' : ''} failed` : '')
          );
        }

        if (failCount > 0 && successCount === 0) {
          setError(`Failed to import all ${totalCount} file${totalCount > 1 ? 's' : ''} from GCS`);
        }

        setGcsPath('');
        setDocumentDate('');
      } else {
        setError('Failed to import from GCS');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
      setGcsImporting(false);
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
                multiple
              />
              <label htmlFor="file-upload">
                <Button
                  variant="outlined"
                  component="span"
                  fullWidth
                  startIcon={<CloudUploadIcon />}
                >
                  Choose Files
                </Button>
              </label>

              {files.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Selected Files ({files.length}):
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {files.map((file, index) => (
                      <Chip
                        key={index}
                        label={file.name}
                        onDelete={() => handleRemoveFile(index)}
                        color="primary"
                        size="small"
                      />
                    ))}
                  </Box>
                </Box>
              )}

              {loading && uploadProgress.total > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Uploading {uploadProgress.current} of {uploadProgress.total} files...
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={(uploadProgress.current / uploadProgress.total) * 100}
                    sx={{ mt: 1 }}
                  />
                </Box>
              )}

              <TextField
                fullWidth
                label="Document Date (Optional)"
                type="date"
                value={documentDate}
                onChange={(e) => setDocumentDate(e.target.value)}
                margin="normal"
                InputLabelProps={{ shrink: true }}
                helperText="Specify a date for temporal context. If not provided, the system will attempt to extract it from the filename."
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
                disabled={loading || files.length === 0}
                sx={{ mt: 2 }}
                startIcon={loading ? <CircularProgress size={20} /> : <UploadFileIcon />}
              >
                {loading
                  ? `Uploading ${uploadProgress.current}/${uploadProgress.total}...`
                  : files.length > 0
                  ? `Upload & Import ${files.length} File${files.length > 1 ? 's' : ''}`
                  : 'Upload & Import'}
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
                helperText="Specify a date for temporal context. If not provided, the system will attempt to extract it from the filename."
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

        {/* GCS Import Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <CloudIcon sx={{ mr: 1, color: 'info.main' }} />
                <Typography variant="h6">Import from GCS</Typography>
              </Box>

              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Import files directly from Google Cloud Storage without re-uploading
              </Typography>

              <TextField
                fullWidth
                label="GCS Path"
                placeholder="gs://bucket-name/path/to/folder/ or gs://bucket-name/file.pdf"
                value={gcsPath}
                onChange={(e) => setGcsPath(e.target.value)}
                margin="normal"
                helperText="Enter a GCS path to a file or folder"
              />

              <TextField
                fullWidth
                label="Document Date (Optional)"
                placeholder="2023-12-31"
                value={documentDate}
                onChange={(e) => setDocumentDate(e.target.value)}
                margin="normal"
                type="date"
                InputLabelProps={{ shrink: true }}
                helperText="Specify a date for temporal context. If not provided, the system will attempt to extract it from the filename."
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
                    onChange={(e) => setChunkSize(parseInt(e.target.value) || 1000)}
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
                    onChange={(e) => setChunkOverlap(parseInt(e.target.value) || 200)}
                    inputProps={{ min: 0, max: 500, step: 50 }}
                    helperText="Overlap between chunks"
                  />
                </Grid>
              </Grid>

              <Box sx={{ display: 'flex', alignItems: 'center', mt: 2, mb: 2 }}>
                <Checkbox
                  checked={gcsRecursive}
                  onChange={(e) => setGcsRecursive(e.target.checked)}
                  id="recursive-checkbox"
                />
                <label htmlFor="recursive-checkbox">
                  <Typography variant="body2">
                    <FolderIcon sx={{ fontSize: 16, verticalAlign: 'middle', mr: 0.5 }} />
                    Import all files from subfolders recursively
                  </Typography>
                </label>
              </Box>

              {gcsImporting && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Scanning and importing files from GCS...
                  </Typography>
                  <LinearProgress />
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    This may take a while depending on the number of files
                  </Typography>
                </Box>
              )}

              <Button
                fullWidth
                variant="contained"
                onClick={handleGCSImport}
                disabled={loading}
                startIcon={loading ? <CircularProgress size={20} /> : <CloudIcon />}
              >
                {gcsImporting ? 'Importing from GCS...' : 'Import from GCS'}
              </Button>

              {/* Results Display */}
              {gcsResults && (
                <Box sx={{ mt: 2, p: 2, backgroundColor: '#f5f5f5', borderRadius: 1 }}>
                  <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
                    Import Summary
                  </Typography>
                  <Grid container spacing={2} sx={{ mt: 1 }}>
                    <Grid item xs={4}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="primary">
                          {gcsResults.files_found || 0}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Found
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={4}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="success.main">
                          {gcsResults.files_imported || 0}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Imported
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={4}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="error.main">
                          {gcsResults.files_failed || 0}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Failed
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>

                  {gcsResults.imported_files && gcsResults.imported_files.length > 0 && (
                    <Box sx={{ mt: 3 }}>
                      <Typography variant="subtitle2" color="success.main" gutterBottom sx={{ fontWeight: 'bold' }}>
                        Successfully Imported ({gcsResults.imported_files.length})
                      </Typography>
                      <Box sx={{ maxHeight: 200, overflowY: 'auto', border: '1px solid #e0e0e0', borderRadius: 1, p: 1 }}>
                        {gcsResults.imported_files.slice(0, 10).map((file, idx) => (
                          <Box key={idx} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', py: 0.5 }}>
                            <Typography variant="body2" sx={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {file.filename}
                            </Typography>
                            <Chip
                              label={`${file.chunks_created} chunks`}
                              size="small"
                              color="success"
                              variant="outlined"
                              sx={{ ml: 1 }}
                            />
                          </Box>
                        ))}
                        {gcsResults.imported_files.length > 10 && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, textAlign: 'center' }}>
                            ... and {gcsResults.imported_files.length - 10} more
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  )}

                  {gcsResults.failed_files && gcsResults.failed_files.length > 0 && (
                    <Box sx={{ mt: 3 }}>
                      <Typography variant="subtitle2" color="error.main" gutterBottom sx={{ fontWeight: 'bold' }}>
                        Failed Files ({gcsResults.failed_files.length})
                      </Typography>
                      <Box sx={{ maxHeight: 200, overflowY: 'auto', border: '1px solid #ffcdd2', borderRadius: 1, p: 1, backgroundColor: '#fff5f5' }}>
                        {gcsResults.failed_files.map((file, idx) => (
                          <Box key={idx} sx={{ py: 0.5, borderBottom: idx < gcsResults.failed_files.length - 1 ? '1px solid #ffebee' : 'none' }}>
                            <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                              {file.filename}
                            </Typography>
                            <Typography variant="caption" color="error.main">
                              {file.error}
                            </Typography>
                          </Box>
                        ))}
                      </Box>
                    </Box>
                  )}
                </Box>
              )}

              {/* Example paths */}
              <Box sx={{ mt: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Examples:
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mt: 1 }}>
                  {[
                    'gs://my-bucket/documents/',
                    'gs://my-bucket/reports/2023/',
                    'gs://my-bucket/file.pdf',
                  ].map((example, idx) => (
                    <Chip
                      key={idx}
                      label={example}
                      size="small"
                      onClick={() => setGcsPath(example)}
                      sx={{ cursor: 'pointer', alignSelf: 'flex-start' }}
                    />
                  ))}
                </Box>
              </Box>
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
