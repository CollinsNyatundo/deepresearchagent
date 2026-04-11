import {
  Paper,
  Stack,
  Title,
  Text,
  Badge,
  Button,
  Anchor,
  Group,
  Loader,
  Divider,
} from '@mantine/core';
import {
  IconZoomIn,
  IconExternalLink,
  IconQuote,
} from '@tabler/icons-react';
import type { MindmapNode, CitationRef } from '../../types/api';

type Props = {
  node: MindmapNode;
  onDrillDeeper: (nodeId: string) => void;
  loading: boolean;
};

const TYPE_CONFIG: Record<string, { color: string; label: string }> = {
  root: { color: 'indigo', label: 'Root' },
  section: { color: 'teal', label: 'Section' },
  detail: { color: 'blue', label: 'Detail' },
};

export function NodeDetailsPanel({ node, onDrillDeeper, loading }: Props) {
  const typeConf = TYPE_CONFIG[node.type] || TYPE_CONFIG.detail;

  // Normalize citations — can be strings or CitationRef objects
  const citations: CitationRef[] = (node.citations || []).map((c, _i) => {
    if (typeof c === 'string') {
      return { id: c, url: '#', title: c };
    }
    return c as CitationRef;
  });

  return (
    <Paper
      p="lg"
      shadow="sm"
      w={360}
      style={{
        borderLeft: '1px solid var(--mantine-color-gray-3)',
        height: '100%',
        overflowY: 'auto',
        background: 'var(--mantine-color-body)',
      }}
    >
      <Stack gap="md">
        {/* Header */}
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Title order={4} style={{ flex: 1 }}>
            {node.label}
          </Title>
          <Badge color={typeConf.color} variant="light" size="sm">
            {typeConf.label}
          </Badge>
        </Group>

        {/* Summary */}
        {node.summary && (
          <>
            <Divider />
            <Text size="sm" c="dimmed" style={{ lineHeight: 1.6 }}>
              {node.summary}
            </Text>
          </>
        )}

        {/* Citations */}
        {citations.length > 0 && (
          <>
            <Divider
              label={
                <Group gap={4}>
                  <IconQuote size={14} />
                  <Text size="xs">Citations ({citations.length})</Text>
                </Group>
              }
              labelPosition="left"
            />
            <Stack gap="xs">
              {citations.map((cit, i) => (
                <Anchor
                  key={i}
                  href={cit.url !== '#' ? cit.url : undefined}
                  target="_blank"
                  size="sm"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '4px 8px',
                    borderRadius: 'var(--mantine-radius-sm)',
                    background: 'var(--mantine-color-gray-0)',
                  }}
                >
                  <IconExternalLink size={14} style={{ flexShrink: 0 }} />
                  <Text size="xs" lineClamp={1}>
                    {cit.title || cit.url}
                  </Text>
                </Anchor>
              ))}
            </Stack>
          </>
        )}

        {/* Drill Deeper */}
        <Divider />
        <Button
          leftSection={
            loading ? (
              <Loader size={14} color="white" />
            ) : (
              <IconZoomIn size={18} />
            )
          }
          variant="gradient"
          gradient={{ from: 'indigo', to: 'violet', deg: 135 }}
          fullWidth
          onClick={() => onDrillDeeper(node.id)}
          disabled={loading}
        >
          {loading ? 'Expanding…' : 'Drill Deeper'}
        </Button>
      </Stack>
    </Paper>
  );
}
