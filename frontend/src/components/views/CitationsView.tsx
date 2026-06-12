import { useEffect, useState, useRef } from 'react';
import {
  Paper,
  Text,
  Anchor,
  Group,
  Stack,
  Badge,
  Loader,
  Center,
  ScrollArea,
  ThemeIcon,
} from '@mantine/core';
import { IconLink, IconQuote } from '@tabler/icons-react';
import { api } from '../../api/client';
import type { ResearchResult } from '../../types/api';

type Props = {
  runId: string;
};

export function CitationsView({ runId }: Props) {
  const [runDetails, setRunDetails] = useState<ResearchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [highlightedId, setHighlightedId] = useState<string | null>(null);
  
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const fetchDetails = () => {
    setLoading(true);
    api
      .getRunDetails(runId)
      .then((details) => {
        setRunDetails(details);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDetails();

    // Listen for resynthesis-complete to reload citations
    const handleResynthesisComplete = (e: Event) => {
      const customEvent = e as CustomEvent<{ runId: string }>;
      if (customEvent.detail.runId === runId) {
        fetchDetails();
      }
    };

    window.addEventListener('resynthesis-complete', handleResynthesisComplete);
    return () => {
      window.removeEventListener('resynthesis-complete', handleResynthesisComplete);
    };
  }, [runId]);

  // Hook up event listeners for inline report highlighting to scroll cards into view
  useEffect(() => {
    const handleHighlight = (e: Event) => {
      const customEvent = e as CustomEvent<{ url?: string; id?: string }>;
      const { id } = customEvent.detail;
      if (id) {
        // Normalize id (e.g. c1 or 1)
        const normalizedId = id.startsWith('c') ? id : `c${id}`;
        setHighlightedId(normalizedId);
        
        const cardEl = cardRefs.current[normalizedId];
        if (cardEl) {
          cardEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }
    };

    const handleClearHighlight = () => {
      setHighlightedId(null);
    };

    window.addEventListener('highlight-citation', handleHighlight);
    window.addEventListener('clear-highlight-citation', handleClearHighlight);

    return () => {
      window.removeEventListener('highlight-citation', handleHighlight);
      window.removeEventListener('clear-highlight-citation', handleClearHighlight);
    };
  }, []);

  const handleMouseEnterCard = (id: string) => {
    const event = new CustomEvent('highlight-citation-in-report', { detail: { id } });
    window.dispatchEvent(event);
  };

  const handleMouseLeaveCard = () => {
    const event = new CustomEvent('clear-highlight-citation-in-report');
    window.dispatchEvent(event);
  };

  if (loading) {
    return (
      <Center py={100}>
        <Stack align="center" gap="xs">
          <Loader size="lg" color="mint" />
          <Text size="sm" c="dimmed">Compiling sources…</Text>
        </Stack>
      </Center>
    );
  }

  if (error) {
    return (
      <Center py={100}>
        <Text c="red" size="sm">Failed to load citations: {error}</Text>
      </Center>
    );
  }

  const citations = runDetails?.citations || [];

  if (citations.length === 0) {
    return (
      <Center py={100}>
        <Text c="dimmed" size="sm">No citations found for this research run.</Text>
      </Center>
    );
  }

  return (
    <ScrollArea style={{ height: 'calc(100vh - 180px)' }} offsetScrollbars>
      <Stack gap="md" pr="md" pb="xl">
        <div>
          <Text fw={700} size="lg" style={{ fontFamily: 'Fira Sans' }}>
            Compiled Citations & Sources
          </Text>
          <Text size="xs" c="dimmed" mt={2}>
            Total unique references crawled: {citations.length}
          </Text>
        </div>

        {citations.map((citation, index) => {
          // Normalize id
          const citeId = citation.id.startsWith('c') ? citation.id : `c${citation.id}`;
          const isHighlighted = highlightedId === citeId;
          const displayIdx = citation.id.replace(/^c/, '') || String(index + 1);

          return (
            <Paper
              key={citation.id}
              ref={(el) => { cardRefs.current[citeId] = el; }}
              id={`citation-card-${citeId}`}
              p="md"
              radius="md"
              withBorder
              onMouseEnter={() => handleMouseEnterCard(citeId)}
              onMouseLeave={handleMouseLeaveCard}
              style={{
                backgroundColor: 'var(--color-slate-900)',
                borderColor: isHighlighted ? 'var(--color-gold-500)' : 'var(--color-slate-800)',
                boxShadow: isHighlighted ? '0 0 12px rgba(245, 158, 11, 0.25)' : 'none',
                transition: 'border-color 200ms ease, box-shadow 200ms ease, transform 150ms',
                transform: isHighlighted ? 'scale(1.01)' : 'none',
              }}
            >
              <Stack gap="xs">
                {/* Header row */}
                <Group justify="space-between" align="flex-start" wrap="nowrap">
                  <Group gap="xs" align="flex-start" style={{ flex: 1 }}>
                    <ThemeIcon
                      size="md"
                      variant="light"
                      color={isHighlighted ? "amber" : "mint"}
                      style={{
                        fontFamily: 'Fira Code',
                        fontWeight: 700,
                        backgroundColor: isHighlighted ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.1)',
                        color: isHighlighted ? 'var(--color-gold-500)' : 'var(--color-mint-500)',
                        flexShrink: 0,
                      }}
                    >
                      {displayIdx}
                    </ThemeIcon>
                    <Anchor
                      href={citation.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      fw={600}
                      size="sm"
                      style={{
                        fontFamily: 'Fira Sans',
                        color: 'var(--color-text-main)',
                        lineHeight: 1.4,
                      }}
                      underline="hover"
                    >
                      {citation.title || 'Source Reference'}
                    </Anchor>
                  </Group>

                  {citation.domain && (
                    <Badge
                      variant="outline"
                      color="gray"
                      size="xs"
                      styles={{
                        root: {
                          borderColor: 'var(--color-slate-800)',
                          color: 'var(--color-text-muted)',
                        }
                      }}
                    >
                      {citation.domain}
                    </Badge>
                  )}
                </Group>

                {/* Snippet block */}
                {citation.snippet && (
                  <Paper
                    p="sm"
                    radius="sm"
                    style={{
                      backgroundColor: 'var(--color-slate-950)',
                      border: '1px solid var(--color-slate-850)',
                    }}
                  >
                    <Group gap="xs" align="flex-start" wrap="nowrap">
                      <IconQuote size={14} color="var(--color-mint-500)" style={{ flexShrink: 0, marginTop: 2 }} />
                      <Text
                        size="xs"
                        c="dimmed"
                        style={{
                          fontFamily: 'Fira Sans',
                          lineHeight: 1.6,
                        }}
                      >
                        {citation.snippet}
                      </Text>
                    </Group>
                  </Paper>
                )}

                {/* Link row */}
                <Group gap="xs" justify="space-between" mt={4}>
                  <Anchor
                    href={citation.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    size="xxs"
                    c="mint"
                    truncate
                    style={{
                      fontFamily: 'Fira Code',
                      maxWidth: '85%',
                    }}
                  >
                    <IconLink size={10} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                    {citation.url}
                  </Anchor>
                  
                  {citation.accessed_at && (
                    <Text size="10px" c="dimmed">
                      Accessed {new Date(citation.accessed_at).toLocaleDateString()}
                    </Text>
                  )}
                </Group>
              </Stack>
            </Paper>
          );
        })}
      </Stack>
    </ScrollArea>
  );
}
