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
  List,
  Paper,
  Divider
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import LinkIcon from '@mui/icons-material/Link';
import DescriptionIcon from '@mui/icons-material/Description';
import { queryIndex, extractTemporalContext } from '../api';

function QueryInterface() {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [temporalFilter, setTemporalFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [temporalInfo, setTemporalInfo] = useState(null);
  const [error, setError] = useState(null);

  const handleQuery = async () => {
    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Parse temporal filter if provided
      let filter = null;
      if (temporalFilter.trim()) {
        try {
          filter = JSON.parse(temporalFilter);
        } catch {
          filter = { document_date: temporalFilter };
        }
      }

      const response = await queryIndex(query, topK, filter);

      if (response.success) {
        setResults(response.data);
      } else {
        setError('Failed to query corpus');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleExtractTemporal = async () => {
    if (!query.trim()) {
      setError('Please enter text to analyze');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await extractTemporalContext(query);

      if (response.success) {
        setTemporalInfo(response.data);
      } else {
        setError('Failed to extract temporal context');
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
        Query RAG Corpus
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Search for information with temporal context awareness.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Query Input Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <SearchIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Search Query
              </Typography>

              <TextField
                fullWidth
                label="Query"
                placeholder="e.g., What were the Q4 2023 revenue figures?"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                margin="normal"
                multiline
                rows={3}
              />

              <TextField
                fullWidth
                label="Number of Results"
                type="number"
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value))}
                margin="normal"
                inputProps={{ min: 1, max: 20 }}
              />

              <TextField
                fullWidth
                label="Temporal Filter (Optional)"
                placeholder='e.g., 2023-12-31 or {"year": "2023"}'
                value={temporalFilter}
                onChange={(e) => setTemporalFilter(e.target.value)}
                margin="normal"
                helperText="Enter a date or JSON filter"
              />

              <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                <Button
                  fullWidth
                  variant="contained"
                  onClick={handleQuery}
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={20} /> : <SearchIcon />}
                >
                  {loading ? 'Searching...' : 'Search'}
                </Button>

                <Button
                  variant="outlined"
                  onClick={handleExtractTemporal}
                  disabled={loading}
                  startIcon={<AccessTimeIcon />}
                >
                  Analyze Temporal
                </Button>
              </Box>

              {/* Example queries */}
              <Box sx={{ mt: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Try these examples:
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mt: 1 }}>
                  {[
                    'Revenue in 2023',
                    'January 2024 updates',
                    'Recent changes in March',
                  ].map((example, idx) => (
                    <Chip
                      key={idx}
                      label={example}
                      size="small"
                      onClick={() => setQuery(example)}
                      sx={{ cursor: 'pointer', alignSelf: 'flex-start' }}
                    />
                  ))}
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Results Section */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Results
              </Typography>

              {results ? (
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Query: {results.query}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Found {results.results.length} result(s)
                  </Typography>

                  <List sx={{ mt: 2 }}>
                    {results.results.length > 0 ? (
                      results.results.map((result, index) => (
                        <Paper key={index} elevation={2} sx={{ mb: 2, p: 2 }}>
                          {/* Title and Score */}
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                            <Typography variant="subtitle1" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <DescriptionIcon fontSize="small" />
                              {result.title || `Document ${index + 1}`}
                            </Typography>
                            <Chip
                              label={`Relevance: ${result.citation?.score ? (result.citation.score * 100).toFixed(2) + '%' : result.score ? (result.score * 100).toFixed(2) + '%' : 'N/A'}`}
                              color="primary"
                              size="small"
                            />
                          </Box>

                          {/* Content Preview */}
                          {result.content_preview && (
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: 'italic' }}>
                              {result.content_preview}
                            </Typography>
                          )}

                          {/* Images */}
                          {result.images && result.images.length > 0 && (
                            <Box sx={{ mb: 2 }}>
                              <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                                Related Images ({result.images.length}):
                              </Typography>
                              <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
                                {result.images.map((image, idx) => (
                                  <Box
                                    key={idx}
                                    sx={{
                                      position: 'relative',
                                      cursor: 'pointer',
                                      '&:hover': {
                                        opacity: 0.8,
                                      }
                                    }}
                                    onClick={() => window.open(image.url, '_blank')}
                                  >
                                    <Box
                                      component="img"
                                      src={image.url}
                                      alt={image.description || `Image ${idx + 1}`}
                                      sx={{
                                        maxWidth: 200,
                                        maxHeight: 150,
                                        borderRadius: 2,
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
                                          fontSize: '0.7rem',
                                          maxWidth: 200,
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
                            <Box sx={{ mb: 1 }}>
                              <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                                Citation:
                              </Typography>
                              <Typography variant="body2" sx={{ mb: 1 }}>
                                {result.citation.formatted}
                              </Typography>

                              {/* Clickable Link */}
                              {result.citation.clickable_link && (
                                <Button
                                  variant="outlined"
                                  size="small"
                                  startIcon={<LinkIcon />}
                                  href={result.citation.clickable_link}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  sx={{ textTransform: 'none' }}
                                >
                                  View Source
                                </Button>
                              )}
                            </Box>
                          )}

                          {/* Metadata Tags */}
                          {result.citation && (
                            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
                              {result.citation.page_number !== undefined && (
                                <Chip
                                  icon={<DescriptionIcon />}
                                  label={`Page ${result.citation.page_number}`}
                                  size="small"
                                  variant="outlined"
                                  color="primary"
                                />
                              )}
                              {result.citation.page_chunk_index !== undefined && (
                                <Chip
                                  label={`Chunk ${result.citation.page_chunk_index}`}
                                  size="small"
                                  variant="outlined"
                                  color="primary"
                                />
                              )}
                              {result.citation.quality_score !== undefined && (
                                <Chip
                                  label={`Quality: ${(result.citation.quality_score * 100).toFixed(0)}%`}
                                  size="small"
                                  variant="outlined"
                                  color={result.citation.quality_score > 0.7 ? 'success' : 'default'}
                                />
                              )}
                              {result.citation.date && (
                                <Chip
                                  icon={<AccessTimeIcon />}
                                  label={result.citation.date}
                                  size="small"
                                  variant="outlined"
                                />
                              )}
                              {result.citation.source && result.citation.source !== 'Unknown' && (
                                <Chip
                                  label={result.citation.source}
                                  size="small"
                                  variant="outlined"
                                />
                              )}
                            </Box>
                          )}
                        </Paper>
                      ))
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        No results found.
                      </Typography>
                    )}
                  </List>

                  {results.temporal_filter && (
                    <Box sx={{ mt: 2 }}>
                      <Chip
                        label={`Temporal Filter: ${JSON.stringify(results.temporal_filter)}`}
                        size="small"
                        color="primary"
                      />
                    </Box>
                  )}
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Enter a query and click Search to see results.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Temporal Analysis Results */}
        {temporalInfo && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <AccessTimeIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Temporal Context Analysis
                </Typography>

                <Paper variant="outlined" sx={{ p: 2, backgroundColor: '#f5f5f5' }}>
                  <Typography variant="body2" gutterBottom>
                    <strong>Analyzed Text:</strong> {temporalInfo.text}
                  </Typography>
                  <Divider sx={{ my: 1 }} />
                  <Typography variant="body2" gutterBottom>
                    <strong>Temporal Entities Found:</strong> {temporalInfo.entity_count}
                  </Typography>

                  {temporalInfo.temporal_entities.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="caption" color="text.secondary">
                        Detected Dates and Years:
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                        {temporalInfo.temporal_entities.map((entity, idx) => (
                          <Chip
                            key={idx}
                            label={`${entity.type}: ${entity.value}`}
                            size="small"
                            color={entity.type === 'date' ? 'primary' : 'secondary'}
                          />
                        ))}
                      </Box>
                    </Box>
                  )}
                </Paper>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}

export default QueryInterface;
