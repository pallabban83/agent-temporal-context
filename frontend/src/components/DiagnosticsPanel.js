import React, { useState } from 'react';
import {
  Box,
  Button,
  Typography,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Grid,
  Divider,
  Paper,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import BuildIcon from '@mui/icons-material/Build';
import SyncIcon from '@mui/icons-material/Sync';
import AssessmentIcon from '@mui/icons-material/Assessment';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InfoIcon from '@mui/icons-material/Info';
import { runDiagnostics, rebuildMetadata, fullRepair } from '../api';

function DiagnosticsPanel() {
  const [loading, setLoading] = useState(false);
  const [diagnosticReport, setDiagnosticReport] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [rebuildLoading, setRebuildLoading] = useState(false);
  const [repairLoading, setRepairLoading] = useState(false);

  const handleRunDiagnostics = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await runDiagnostics();

      if (response.success) {
        setDiagnosticReport(response.data);
        setSuccess('Diagnostics completed successfully');
      } else {
        setError('Failed to run diagnostics');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
      console.error('Diagnostics error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRebuildMetadata = async () => {
    setRebuildLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await rebuildMetadata();

      if (response.success) {
        setSuccess(`Metadata rebuilt successfully! ${response.data.metadata_count} documents processed.`);
        // Re-run diagnostics after rebuild
        handleRunDiagnostics();
      } else {
        setError('Failed to rebuild metadata');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
      console.error('Rebuild metadata error:', err);
    } finally {
      setRebuildLoading(false);
    }
  };

  const handleFullRepair = async () => {
    setRepairLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fullRepair();

      if (response.success) {
        setSuccess(`Full repair completed! ${response.data.metadata_count} documents synced.`);
        // Re-run diagnostics after repair
        handleRunDiagnostics();
      } else {
        setError('Failed to complete full repair');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
      console.error('Full repair error:', err);
    } finally {
      setRepairLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon color="success" />;
      case 'needs_rag_sync':
        return <WarningIcon color="warning" />;
      case 'partial_issues':
        return <ErrorIcon color="error" />;
      default:
        return <InfoIcon />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'needs_rag_sync':
        return 'warning';
      case 'partial_issues':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        <AssessmentIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        System Diagnostics & Sync Repair
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Check sync status between Vector Search, RAG Engine, and metadata cache.
        Identify and fix issues with citations and document retrieval.
      </Typography>

      <Divider sx={{ my: 2 }} />

      {/* Actions */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Button
            fullWidth
            variant="contained"
            color="primary"
            onClick={handleRunDiagnostics}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : <AssessmentIcon />}
          >
            {loading ? 'Running...' : 'Run Diagnostics'}
          </Button>
        </Grid>
        <Grid item xs={12} md={4}>
          <Button
            fullWidth
            variant="outlined"
            color="secondary"
            onClick={handleRebuildMetadata}
            disabled={rebuildLoading}
            startIcon={rebuildLoading ? <CircularProgress size={20} /> : <BuildIcon />}
          >
            {rebuildLoading ? 'Rebuilding...' : 'Rebuild Metadata'}
          </Button>
        </Grid>
        <Grid item xs={12} md={4}>
          <Button
            fullWidth
            variant="outlined"
            color="warning"
            onClick={handleFullRepair}
            disabled={repairLoading}
            startIcon={repairLoading ? <CircularProgress size={20} /> : <SyncIcon />}
          >
            {repairLoading ? 'Repairing...' : 'Full Repair'}
          </Button>
        </Grid>
      </Grid>

      {/* Alerts */}
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

      {/* Diagnostic Report */}
      {diagnosticReport && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              {getStatusIcon(diagnosticReport.status)}
              <Typography variant="h6" sx={{ ml: 1 }}>
                Status:
              </Typography>
              <Chip
                label={diagnosticReport.status?.toUpperCase() || 'UNKNOWN'}
                color={getStatusColor(diagnosticReport.status)}
                sx={{ ml: 2 }}
              />
            </Box>

            <Divider sx={{ my: 2 }} />

            {/* Summary Statistics */}
            <Typography variant="subtitle1" gutterBottom fontWeight="bold">
              Summary
            </Typography>
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={4}>
                <Paper elevation={0} sx={{ p: 2, bgcolor: 'primary.light', color: 'primary.contrastText' }}>
                  <Typography variant="h4">{diagnosticReport.metadata_count || 0}</Typography>
                  <Typography variant="body2">Metadata Entries</Typography>
                </Paper>
              </Grid>
              <Grid item xs={4}>
                <Paper elevation={0} sx={{ p: 2, bgcolor: 'secondary.light', color: 'secondary.contrastText' }}>
                  <Typography variant="h4">{diagnosticReport.gcs_documents_count || 0}</Typography>
                  <Typography variant="body2">GCS Documents</Typography>
                </Paper>
              </Grid>
              <Grid item xs={4}>
                <Paper elevation={0} sx={{ p: 2, bgcolor: 'success.light', color: 'success.contrastText' }}>
                  <Typography variant="h4">{diagnosticReport.rag_files_count || 0}</Typography>
                  <Typography variant="body2">RAG Engine Files</Typography>
                </Paper>
              </Grid>
            </Grid>

            {/* Issues */}
            {(diagnosticReport.missing_metadata?.length > 0 ||
              diagnosticReport.missing_rag?.length > 0 ||
              diagnosticReport.orphaned_metadata?.length > 0 ||
              diagnosticReport.citation_issues_count > 0) && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle1" gutterBottom fontWeight="bold" color="error">
                  Issues Detected
                </Typography>

                {diagnosticReport.missing_metadata?.length > 0 && (
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <ErrorIcon color="error" sx={{ mr: 1 }} />
                      <Typography>
                        Missing Metadata: {diagnosticReport.missing_metadata.length} documents
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        These documents exist in GCS but are missing from the metadata cache,
                        which will cause citation failures.
                      </Typography>
                      <Paper elevation={0} sx={{ p: 2, bgcolor: 'grey.100', maxHeight: 200, overflow: 'auto' }}>
                        <Typography variant="body2" component="pre" sx={{ fontSize: '0.75rem' }}>
                          {diagnosticReport.missing_metadata.slice(0, 10).join('\n')}
                          {diagnosticReport.missing_metadata.length > 10 && '\n...'}
                        </Typography>
                      </Paper>
                    </AccordionDetails>
                  </Accordion>
                )}

                {diagnosticReport.missing_rag?.length > 0 && (
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <WarningIcon color="warning" sx={{ mr: 1 }} />
                      <Typography>
                        Missing RAG Engine Sync: {diagnosticReport.missing_rag.length} documents
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        These documents exist in GCS but are not registered with RAG Engine.
                        They won't appear in query results.
                      </Typography>
                      <Paper elevation={0} sx={{ p: 2, bgcolor: 'grey.100', maxHeight: 200, overflow: 'auto' }}>
                        <Typography variant="body2" component="pre" sx={{ fontSize: '0.75rem' }}>
                          {diagnosticReport.missing_rag.slice(0, 10).join('\n')}
                          {diagnosticReport.missing_rag.length > 10 && '\n...'}
                        </Typography>
                      </Paper>
                    </AccordionDetails>
                  </Accordion>
                )}

                {diagnosticReport.orphaned_metadata?.length > 0 && (
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <WarningIcon color="warning" sx={{ mr: 1 }} />
                      <Typography>
                        Orphaned Metadata: {diagnosticReport.orphaned_metadata.length} entries
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        These metadata entries don't have corresponding GCS documents.
                      </Typography>
                      <Paper elevation={0} sx={{ p: 2, bgcolor: 'grey.100', maxHeight: 200, overflow: 'auto' }}>
                        <Typography variant="body2" component="pre" sx={{ fontSize: '0.75rem' }}>
                          {diagnosticReport.orphaned_metadata.slice(0, 10).join('\n')}
                          {diagnosticReport.orphaned_metadata.length > 10 && '\n...'}
                        </Typography>
                      </Paper>
                    </AccordionDetails>
                  </Accordion>
                )}

                {diagnosticReport.citation_issues_count > 0 && (
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <WarningIcon color="warning" sx={{ mr: 1 }} />
                      <Typography>
                        Citation Issues: {diagnosticReport.citation_issues_count} documents
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        These documents have incomplete citation metadata (missing title, date, or file URL).
                      </Typography>
                      <List dense>
                        {diagnosticReport.citation_issues_sample?.slice(0, 5).map((issue, idx) => (
                          <ListItem key={idx}>
                            <ListItemIcon>
                              <ErrorIcon fontSize="small" color="warning" />
                            </ListItemIcon>
                            <ListItemText
                              primary={issue.doc_id}
                              secondary={issue.issues.join(', ')}
                            />
                          </ListItem>
                        ))}
                      </List>
                    </AccordionDetails>
                  </Accordion>
                )}
              </>
            )}

            {/* Recommendations */}
            {diagnosticReport.recommendations?.length > 0 && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle1" gutterBottom fontWeight="bold">
                  Recommendations
                </Typography>
                <List>
                  {diagnosticReport.recommendations.map((rec, idx) => (
                    <ListItem key={idx}>
                      <ListItemIcon>
                        <InfoIcon color="info" />
                      </ListItemIcon>
                      <ListItemText primary={rec} />
                    </ListItem>
                  ))}
                </List>
              </>
            )}

            {/* Healthy Status */}
            {diagnosticReport.status === 'healthy' && (
              <Alert severity="success" sx={{ mt: 2 }}>
                <Typography variant="body1" fontWeight="bold">
                  All systems are healthy!
                </Typography>
                <Typography variant="body2">
                  Vector Search, RAG Engine, and metadata cache are all in sync with complete citation information.
                </Typography>
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* Help Text */}
      {!diagnosticReport && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              About Diagnostics
            </Typography>
            <Typography variant="body2" paragraph>
              The diagnostic tool checks for sync issues between three critical components:
            </Typography>
            <List>
              <ListItem>
                <ListItemIcon>
                  <CheckCircleIcon color="primary" />
                </ListItemIcon>
                <ListItemText
                  primary="Vector Search Index"
                  secondary="Stores temporal-aware embeddings for semantic search"
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <CheckCircleIcon color="primary" />
                </ListItemIcon>
                <ListItemText
                  primary="RAG Engine"
                  secondary="Retrieves document text content for query results"
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <CheckCircleIcon color="primary" />
                </ListItemIcon>
                <ListItemText
                  primary="Metadata Cache"
                  secondary="Provides citation information (titles, dates, source URLs)"
                />
              </ListItem>
            </List>

            <Divider sx={{ my: 2 }} />

            <Typography variant="h6" gutterBottom>
              Repair Options
            </Typography>
            <List>
              <ListItem>
                <ListItemIcon>
                  <BuildIcon color="secondary" />
                </ListItemIcon>
                <ListItemText
                  primary="Rebuild Metadata"
                  secondary="Reconstructs the metadata cache by reading all GCS documents. Use this if citations are broken."
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <SyncIcon color="warning" />
                </ListItemIcon>
                <ListItemText
                  primary="Full Repair"
                  secondary="Rebuilds metadata AND re-registers all documents with RAG Engine. This is the most comprehensive fix."
                />
              </ListItem>
            </List>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}

export default DiagnosticsPanel;
