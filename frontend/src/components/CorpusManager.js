import React, { useState, useEffect } from 'react';
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
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions
} from '@mui/material';
import StorageIcon from '@mui/icons-material/Storage';
import InfoIcon from '@mui/icons-material/Info';
import DeleteIcon from '@mui/icons-material/Delete';
import WarningIcon from '@mui/icons-material/Warning';
import ClearAllIcon from '@mui/icons-material/ClearAll';
import CloudIcon from '@mui/icons-material/Cloud';
import CloudSyncIcon from '@mui/icons-material/CloudSync';
import { createVectorSearchInfrastructure, createCorpus, getCorpusInfo, deleteCorpus, deleteVectorSearchInfrastructure, clearDatapoints, registerExistingDocuments } from '../api';

function CorpusManager() {
  // Vector Search Infrastructure state (STEP 1)
  const [vsDescription, setVsDescription] = useState('Vector Search for Temporal RAG');
  const [vsDimensions, setVsDimensions] = useState(768);
  const [vsLoading, setVsLoading] = useState(false);

  // Corpus state (STEP 2)
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [corpusInfo, setCorpusInfo] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [deleteInfraDialogOpen, setDeleteInfraDialogOpen] = useState(false);
  const [deletingInfra, setDeletingInfra] = useState(false);
  const [registering, setRegistering] = useState(false);

  useEffect(() => {
    loadCorpusInfo();
  }, []);

  const loadCorpusInfo = async () => {
    try {
      const response = await getCorpusInfo();
      if (response.success) {
        setCorpusInfo(response.data);
      }
    } catch (err) {
      console.error('Error loading corpus info:', err);
    }
  };

  const handleCreateVectorSearch = async () => {
    if (!vsDescription.trim()) {
      setError('Please provide a description for Vector Search');
      return;
    }

    setVsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await createVectorSearchInfrastructure(vsDescription, vsDimensions, 'brute_force');

      if (response.success) {
        setSuccess(`Vector Search created! Index and endpoint saved to configuration. You can now create a RAG corpus (Step 2).`);
        setVsDescription('Vector Search for Temporal RAG');
      } else {
        setError('Failed to create Vector Search infrastructure');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setVsLoading(false);
    }
  };

  const handleCreateCorpus = async () => {
    if (!description.trim()) {
      setError('Please provide a description');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await createCorpus(description, 768);

      if (response.success) {
        setSuccess('Corpus created successfully!');
        setDescription('');
        await loadCorpusInfo();
      } else {
        setError('Failed to create corpus');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleClearDatapoints = async () => {
    setClearing(true);
    setError(null);
    setSuccess(null);
    setClearDialogOpen(false);

    try {
      const response = await clearDatapoints();

      if (response.success) {
        setSuccess(response.data.message || 'All documents cleared successfully! You can now upload new documents.');
        await loadCorpusInfo();
      } else {
        setError('Failed to clear documents');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setClearing(false);
    }
  };

  const handleRegisterExistingDocuments = async () => {
    setRegistering(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await registerExistingDocuments();

      if (response.success) {
        const data = response.data;
        const batchInfo = data.total_batches > 1
          ? ` in ${data.batches_processed}/${data.total_batches} batches`
          : '';
        setSuccess(`Successfully registered ${data.documents_registered} documents with RAG Engine${batchInfo}! Queries will now return text content.`);
      } else {
        setError('Failed to register documents with RAG Engine');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setRegistering(false);
    }
  };

  const handleDeleteVectorSearchInfrastructure = async () => {
    setDeletingInfra(true);
    setError(null);
    setSuccess(null);
    setDeleteInfraDialogOpen(false);

    try {
      const response = await deleteVectorSearchInfrastructure();

      if (response.success) {
        setSuccess('Vector Search infrastructure deleted successfully! You can now create new infrastructure using STEP 1.');
        await loadCorpusInfo();
      } else {
        setError('Failed to delete Vector Search infrastructure');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setDeletingInfra(false);
    }
  };

  const handleDeleteCorpus = async () => {
    setDeleting(true);
    setError(null);
    setSuccess(null);
    setDeleteDialogOpen(false);

    try {
      const response = await deleteCorpus();

      if (response.success) {
        setSuccess('Corpus and all resources deleted successfully! You can now create a new corpus with StreamUpdate enabled.');
        await loadCorpusInfo();
      } else {
        setError('Failed to delete corpus');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        RAG Corpus Management
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Create and manage your Vertex AI RAG corpus with Vector Search backend.
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

      <Typography variant="h6" gutterBottom sx={{ mt: 3, mb: 2, color: 'primary.main' }}>
        Two-Step Setup Process
      </Typography>

      <Grid container spacing={3}>
        {/* STEP 1: Create Vector Search Infrastructure */}
        <Grid item xs={12} md={6}>
          <Card sx={{ border: '2px solid', borderColor: 'primary.light' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <CloudIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h6">STEP 1: Create Vector Search</Typography>
              </Box>
              <Alert severity="info" sx={{ mb: 2 }}>
                Create the underlying Vector Search index and endpoint infrastructure.
                This step takes 2-5 minutes.
              </Alert>

              <TextField
                fullWidth
                label="Description"
                placeholder="Vector Search for Temporal RAG"
                value={vsDescription}
                onChange={(e) => setVsDescription(e.target.value)}
                margin="normal"
                multiline
                rows={2}
              />

              <TextField
                fullWidth
                label="Embedding Dimensions"
                type="number"
                value={vsDimensions}
                onChange={(e) => setVsDimensions(parseInt(e.target.value))}
                margin="normal"
                helperText="Default: 768 (text-embedding-005)"
              />

              <Button
                fullWidth
                variant="contained"
                onClick={handleCreateVectorSearch}
                disabled={vsLoading}
                sx={{ mt: 2 }}
                startIcon={vsLoading ? <CircularProgress size={20} /> : <CloudIcon />}
              >
                {vsLoading ? 'Creating Vector Search...' : 'Create Vector Search Infrastructure'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* STEP 2: Create RAG Corpus */}
        <Grid item xs={12} md={6}>
          <Card sx={{ border: '2px solid', borderColor: 'secondary.light' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <StorageIcon sx={{ mr: 1, color: 'secondary.main' }} />
                <Typography variant="h6">STEP 2: Create RAG Corpus</Typography>
              </Box>
              <Alert severity="warning" sx={{ mb: 2 }}>
                Run this AFTER Step 1 completes or if you already have Vector Search configured.
              </Alert>
              <Alert severity="info" sx={{ mb: 2 }}>
                <strong>Note:</strong> RAG Engine requires an empty Vector Search index. If your index contains documents, use "Clear All Documents from Index" first.
              </Alert>

              <TextField
                fullWidth
                label="Description"
                placeholder="e.g., Financial reports with temporal context"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                margin="normal"
                multiline
                rows={4}
              />

              <Button
                fullWidth
                variant="contained"
                onClick={handleCreateCorpus}
                disabled={loading}
                sx={{ mt: 2 }}
                startIcon={loading ? <CircularProgress size={20} /> : <StorageIcon />}
              >
                {loading ? 'Creating...' : 'Create Corpus'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Corpus Info Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <InfoIcon sx={{ mr: 1, color: 'info.main' }} />
                <Typography variant="h6">Current Corpus Info</Typography>
              </Box>

              {corpusInfo ? (
                <Box>
                  {/* Status Message */}
                  {corpusInfo.message && (
                    <Alert
                      severity={corpusInfo.status === 'created' ? 'success' : 'info'}
                      sx={{ mb: 2 }}
                    >
                      {corpusInfo.message}
                    </Alert>
                  )}

                  {/* Show corpus name only if RAG corpus exists */}
                  {corpusInfo.corpus_name && (
                    <>
                      <Typography variant="body2" gutterBottom>
                        <strong>Corpus Name:</strong> {corpusInfo.corpus_name}
                      </Typography>
                      <Divider sx={{ my: 1 }} />
                    </>
                  )}

                  {/* Always show project info */}
                  <Typography variant="body2" gutterBottom>
                    <strong>Project ID:</strong> {corpusInfo.project_id}
                  </Typography>
                  <Divider sx={{ my: 1 }} />

                  <Typography variant="body2" gutterBottom>
                    <strong>Location:</strong> {corpusInfo.location}
                  </Typography>
                  <Divider sx={{ my: 1 }} />

                  {/* Show availability status */}
                  <Typography variant="body2" gutterBottom>
                    <strong>Index Available:</strong>{' '}
                    {corpusInfo.index_available ? (
                      <span style={{ color: 'green' }}>✓ Yes</span>
                    ) : (
                      <span style={{ color: 'gray' }}>✗ No</span>
                    )}
                  </Typography>
                  <Divider sx={{ my: 1 }} />

                  <Typography variant="body2" gutterBottom>
                    <strong>Endpoint Available:</strong>{' '}
                    {corpusInfo.endpoint_available ? (
                      <span style={{ color: 'green' }}>✓ Yes</span>
                    ) : (
                      <span style={{ color: 'gray' }}>✗ No</span>
                    )}
                  </Typography>

                  {/* Show index/endpoint names if available */}
                  {corpusInfo.index_display_name && (
                    <>
                      <Divider sx={{ my: 1 }} />
                      <Typography variant="body2" gutterBottom>
                        <strong>Index:</strong> {corpusInfo.index_display_name}
                      </Typography>
                    </>
                  )}

                  {corpusInfo.endpoint_display_name && (
                    <>
                      <Divider sx={{ my: 1 }} />
                      <Typography variant="body2" gutterBottom>
                        <strong>Endpoint:</strong> {corpusInfo.endpoint_display_name}
                      </Typography>
                    </>
                  )}

                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={loadCorpusInfo}
                    sx={{ mt: 2 }}
                    size="small"
                  >
                    Refresh Info
                  </Button>

                  {/* Clear All Documents Button - show if index is available */}
                  {corpusInfo.index_available && (
                    <Button
                      fullWidth
                      variant="outlined"
                      color="warning"
                      onClick={() => setClearDialogOpen(true)}
                      disabled={clearing}
                      sx={{ mt: 1 }}
                      size="small"
                      startIcon={clearing ? <CircularProgress size={16} /> : <ClearAllIcon />}
                    >
                      {clearing ? 'Clearing...' : 'Clear All Documents from Index'}
                    </Button>
                  )}

                  {/* Register Existing Documents Button - show if corpus exists */}
                  {corpusInfo.corpus_available && (
                    <Button
                      fullWidth
                      variant="outlined"
                      color="info"
                      onClick={handleRegisterExistingDocuments}
                      disabled={registering}
                      sx={{ mt: 1 }}
                      size="small"
                      startIcon={registering ? <CircularProgress size={16} /> : <CloudSyncIcon />}
                    >
                      {registering ? 'Registering...' : 'Register Existing Documents with RAG'}
                    </Button>
                  )}

                  {/* Delete Vector Search Infrastructure Button - show if index/endpoint available */}
                  {(corpusInfo.index_available || corpusInfo.endpoint_available) && (
                    <Button
                      fullWidth
                      variant="outlined"
                      color="error"
                      onClick={() => setDeleteInfraDialogOpen(true)}
                      disabled={deletingInfra}
                      sx={{ mt: 1 }}
                      size="small"
                      startIcon={deletingInfra ? <CircularProgress size={16} /> : <DeleteIcon />}
                    >
                      {deletingInfra ? 'Deleting...' : 'Delete Vector Search Infrastructure'}
                    </Button>
                  )}

                  {/* Delete Corpus Button - only show if RAG corpus exists */}
                  {corpusInfo.status === 'created' && (
                    <Button
                      fullWidth
                      variant="outlined"
                      color="error"
                      onClick={() => setDeleteDialogOpen(true)}
                      disabled={deleting}
                      sx={{ mt: 1 }}
                      size="small"
                      startIcon={deleting ? <CircularProgress size={16} /> : <DeleteIcon />}
                    >
                      {deleting ? 'Deleting...' : 'Delete Corpus'}
                    </Button>
                  )}
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Loading corpus information...
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Clear Documents Confirmation Dialog */}
      <Dialog
        open={clearDialogOpen}
        onClose={() => setClearDialogOpen(false)}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningIcon color="warning" />
          Clear All Documents
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to clear all documents from the index?
            <br /><br />
            This will:
            <ul>
              <li>Remove all datapoints from the Vector Search index</li>
              <li>Clear all document metadata</li>
              <li>Keep the index and endpoint intact (no recreation needed)</li>
              <li>Allow you to create a RAG corpus (RAG Engine requires an empty index)</li>
            </ul>
            <strong>Use this to prepare for RAG corpus creation or to start fresh with new documents.</strong>
            <br /><br />
            After clearing, you can create a RAG corpus or upload new documents.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setClearDialogOpen(false)} color="primary">
            Cancel
          </Button>
          <Button onClick={handleClearDatapoints} color="warning" variant="contained" autoFocus>
            Clear All Documents
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Vector Search Infrastructure Confirmation Dialog */}
      <Dialog
        open={deleteInfraDialogOpen}
        onClose={() => setDeleteInfraDialogOpen(false)}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningIcon color="error" />
          Delete Vector Search Infrastructure
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete the Vector Search index and endpoint?
            <br /><br />
            This will:
            <ul>
              <li>Undeploy the index from the endpoint</li>
              <li>Delete the index endpoint</li>
              <li>Delete the Vector Search index</li>
              <li>Remove ALL datapoints (cannot be recovered)</li>
            </ul>
            <strong>This action cannot be undone.</strong>
            <br /><br />
            After deletion, you can create fresh Vector Search infrastructure using STEP 1.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteInfraDialogOpen(false)} color="primary">
            Cancel
          </Button>
          <Button onClick={handleDeleteVectorSearchInfrastructure} color="error" variant="contained" autoFocus>
            Delete Infrastructure
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Corpus Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningIcon color="warning" />
          Confirm Corpus Deletion
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete the RAG corpus and all associated resources?
            <br /><br />
            This will:
            <ul>
              <li>Delete the RAG corpus</li>
              <li>Undeploy the index from the endpoint</li>
              <li>Delete the index endpoint</li>
              <li>Delete the Vector Search index</li>
              <li>Clear all GCS files and document metadata</li>
            </ul>
            <strong>This action cannot be undone.</strong>
            <br /><br />
            After deletion, you can create new infrastructure using STEP 1.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} color="primary">
            Cancel
          </Button>
          <Button onClick={handleDeleteCorpus} color="error" variant="contained" autoFocus>
            Delete Corpus
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default CorpusManager;
