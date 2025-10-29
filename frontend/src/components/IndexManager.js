import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  TextField,
  Typography,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  Grid,
  Chip,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Paper,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import InfoIcon from '@mui/icons-material/Info';
import DeleteIcon from '@mui/icons-material/Delete';
import ClearIcon from '@mui/icons-material/Clear';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { createIndex, getIndexInfo, clearIndexDatapoints, deleteIndex } from '../api';

function IndexManager() {
  const [description, setDescription] = useState('Temporal Context Vector Search Index');
  const [dimensions, setDimensions] = useState(768);
  const [indexAlgorithm, setIndexAlgorithm] = useState('brute_force');
  const [loading, setLoading] = useState(false);
  const [indexInfo, setIndexInfo] = useState(null);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadIndexInfo();
  }, []);

  const loadIndexInfo = async () => {
    try {
      const response = await getIndexInfo();
      if (response.success) {
        setIndexInfo(response.data);
      }
    } catch (err) {
      console.error('Error loading index info:', err);
    }
  };

  const handleCreateIndex = async () => {
    if (!description.trim()) {
      setError('Please enter a description');
      return;
    }

    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const response = await createIndex(description, dimensions, indexAlgorithm);

      if (response.success) {
        setMessage({
          type: 'success',
          text: 'Vector Search index created and deployed successfully! Resource names saved to .env file.',
          details: response.data,
        });
        await loadIndexInfo();
      } else {
        setError(response.error || 'Failed to create index');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to create index');
    } finally {
      setLoading(false);
    }
  };

  const handleClearDatapoints = async () => {
    if (!window.confirm('Are you sure you want to clear all datapoints from the index? This will:\n- Remove all datapoints from the Vector Search index\n- Delete all document files from GCS\n- Clear all metadata\n\nThe index infrastructure will remain intact.')) {
      return;
    }

    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const response = await clearIndexDatapoints();

      if (response.success) {
        setMessage({
          type: 'success',
          text: response.data.message || 'Datapoints cleared successfully',
          details: response.data,
        });
        await loadIndexInfo();
      } else {
        setError(response.error || 'Failed to clear datapoints');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to clear datapoints');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteIndex = async () => {
    if (!window.confirm('Are you sure you want to delete the Vector Search infrastructure? This will:\n- Delete the Vector Search index\n- Delete the index endpoint\n- Remove all datapoints\n- Delete all files from GCS\n\nThis action CANNOT be undone.')) {
      return;
    }

    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const response = await deleteIndex();

      if (response.success) {
        setMessage({
          type: 'success',
          text: 'Vector Search infrastructure deleted successfully',
          details: response.data,
        });
        setIndexInfo(null);
      } else {
        setError(response.error || 'Failed to delete index');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to delete index');
    } finally {
      setLoading(false);
    }
  };

  const indexExists = indexInfo?.index_available && indexInfo?.endpoint_available;

  return (
    <Box>
      <Typography variant="h5" gutterBottom sx={{ fontWeight: 700, mb: 3 }}>
        🗄️ Vector Search Index Management
      </Typography>

      {/* Current Index Status */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <InfoIcon color="primary" />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Current Index Status
            </Typography>
          </Box>

          {indexInfo ? (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Status:
                  </Typography>
                  {indexExists ? (
                    <Chip
                      icon={<CheckCircleIcon />}
                      label="Active"
                      color="success"
                      size="small"
                    />
                  ) : (
                    <Chip label="Not Created" color="default" size="small" />
                  )}
                </Box>
              </Grid>

              {indexInfo.index_available && (
                <>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" color="text.secondary">
                      Index Name:
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 500 }}>
                      {indexInfo.index_display_name || 'N/A'}
                    </Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                      Index Resource:
                    </Typography>
                    <Paper
                      sx={{
                        p: 1,
                        bgcolor: 'grey.50',
                        fontFamily: 'monospace',
                        fontSize: '0.75rem',
                        overflow: 'auto',
                      }}
                    >
                      {indexInfo.index_id}
                    </Paper>
                  </Grid>
                </>
              )}

              {indexInfo.endpoint_available && (
                <>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" color="text.secondary">
                      Endpoint Name:
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 500 }}>
                      {indexInfo.endpoint_display_name || 'N/A'}
                    </Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                      Endpoint Resource:
                    </Typography>
                    <Paper
                      sx={{
                        p: 1,
                        bgcolor: 'grey.50',
                        fontFamily: 'monospace',
                        fontSize: '0.75rem',
                        overflow: 'auto',
                      }}
                    >
                      {indexInfo.endpoint_id}
                    </Paper>
                  </Grid>
                </>
              )}

              {indexInfo.deployed_index_id && (
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary">
                    Deployed Index ID:
                  </Typography>
                  <Typography variant="body1" sx={{ fontWeight: 500, fontFamily: 'monospace' }}>
                    {indexInfo.deployed_index_id}
                  </Typography>
                </Grid>
              )}
            </Grid>
          ) : (
            <Typography variant="body2" color="text.secondary">
              Loading index information...
            </Typography>
          )}
        </CardContent>
      </Card>

      <Divider sx={{ my: 3 }} />

      {/* Create New Index */}
      {!indexExists && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
              <AddIcon color="primary" />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Create New Vector Search Index
              </Typography>
            </Box>

            <Alert severity="info" sx={{ mb: 3 }}>
              This will create a new Vector Search index and endpoint. The process may take several minutes.
              Resource names will be automatically saved to your .env file.
            </Alert>

            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Index Description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Enter a description for your index"
                  disabled={loading}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Embedding Dimensions"
                  type="number"
                  value={dimensions}
                  onChange={(e) => setDimensions(parseInt(e.target.value))}
                  disabled={loading}
                  helperText="768 for text-embedding-005"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth disabled={loading}>
                  <InputLabel>Index Algorithm</InputLabel>
                  <Select
                    value={indexAlgorithm}
                    onChange={(e) => setIndexAlgorithm(e.target.value)}
                    label="Index Algorithm"
                  >
                    <MenuItem value="brute_force">
                      Brute Force (Fast deployment, exact search)
                    </MenuItem>
                    <MenuItem value="tree_ah">
                      Tree-AH (Slower deployment, approximate search, production)
                    </MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <Button
                  variant="contained"
                  onClick={handleCreateIndex}
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={20} /> : <AddIcon />}
                  fullWidth
                  size="large"
                >
                  {loading ? 'Creating Index...' : 'Create Index & Deploy'}
                </Button>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Clear Datapoints & Delete Index */}
      {indexExists && (
        <Card sx={{ borderColor: 'warning.main', borderWidth: 1, borderStyle: 'solid' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <DeleteIcon color="warning" />
              <Typography variant="h6" sx={{ fontWeight: 600, color: 'warning.main' }}>
                Maintenance & Danger Zone
              </Typography>
            </Box>

            {/* Clear Datapoints */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                Clear All Datapoints
              </Typography>
              <Alert severity="info" sx={{ mb: 2 }}>
                Remove all datapoints from the index and delete all associated files from GCS. The index infrastructure remains intact. Faster than recreating the index.
              </Alert>
              <Button
                variant="outlined"
                color="warning"
                onClick={handleClearDatapoints}
                disabled={loading}
                startIcon={loading ? <CircularProgress size={20} /> : <ClearIcon />}
                fullWidth
              >
                {loading ? 'Clearing...' : 'Clear All Datapoints'}
              </Button>
            </Box>

            <Divider sx={{ my: 2 }} />

            {/* Delete Infrastructure */}
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'error.main' }}>
                Delete Infrastructure
              </Typography>
              <Alert severity="error" sx={{ mb: 2 }}>
                Permanently delete the index, endpoint, and all associated files from GCS. This cannot be undone.
              </Alert>
              <Button
                variant="outlined"
                color="error"
                onClick={handleDeleteIndex}
                disabled={loading}
                startIcon={loading ? <CircularProgress size={20} /> : <DeleteIcon />}
                fullWidth
              >
                {loading ? 'Deleting...' : 'Delete Vector Search Infrastructure'}
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Messages */}
      {message && (
        <Alert severity={message.type} sx={{ mt: 3 }} onClose={() => setMessage(null)}>
          <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
            {message.text}
          </Typography>
          {message.details && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Details:
              </Typography>
              <Paper
                sx={{
                  p: 1,
                  mt: 0.5,
                  bgcolor: 'grey.50',
                  fontFamily: 'monospace',
                  fontSize: '0.7rem',
                  maxHeight: 200,
                  overflow: 'auto',
                }}
              >
                {JSON.stringify(message.details, null, 2)}
              </Paper>
            </Box>
          )}
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mt: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
    </Box>
  );
}

export default IndexManager;
