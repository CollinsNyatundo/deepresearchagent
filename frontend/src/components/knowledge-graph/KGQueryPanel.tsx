/**
 * KGQueryPanel — Strategy B: Query the knowledge graph via MCP bridge.
 *
 * Allows users to ask questions against the knowledge graph using
 * graph-traversal (BFS or DFS) rather than brute-force LLM context stuffing.
 * Shows the answer, nodes traversed, and token cost vs naive approach.
 */

import { useState } from 'react';
import {
  Paper,
  Stack,
  Group,
  Text,
  Title,
  Textarea,
  Button,
  SegmentedControl,
  Badge,
  Divider,
  Loader,
  Alert,
  ThemeIcon,
  Code,
  NumberInput,
} from '@mantine/core';
import {
  IconSearch,
  IconGitBranch,
  IconBolt,
  IconAlertTriangle,
  IconCheck,
} from '@tabler/icons-react';
import { api } from '../../api/client';
import type { KGQueryResult } from '../../types/api';

type KGQueryPanelProps = {
  runId: string;
};

export function KGQueryPanel({ runId }: KGQueryPanelProps) {
  const [question, setQuestion] = useState('');
  const [mode, setMode] = useState<'bfs' | 'dfs'>('bfs');
  const [budget, setBudget] = useState<number>(2000);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<KGQueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleQuery = async () => {
    if (!question.trim()) return;
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.queryKnowledgeGraph(runId, {
        question: question.trim(),
        mode,
        budget,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Paper p="md" withBorder radius="md">
      <Title order={5} mb="md">
        <Group gap="xs">
          <ThemeIcon size="sm" variant="light" color="indigo">
            <IconSearch size={14} />
          </ThemeIcon>
          Graph Query (MCP Bridge)
        </Group>
      </Title>

      <Stack gap="sm">
        <Textarea
          placeholder="What connects topic A to topic B? What are the central concepts? How does X relate to Y?"
          description="Ask a natural language question — the graph traversal engine answers using indexed relationships instead of raw text."
          minRows={2}
          autosize
          maxRows={5}
          value={question}
          onChange={(e) => setQuestion(e.currentTarget.value)}
        />

        <Group gap="md" align="flex-end">
          <div>
            <Text size="xs" fw={500} mb={4} c="dimmed">
              Traversal Mode
            </Text>
            <SegmentedControl
              size="xs"
              value={mode}
              onChange={(val) => setMode(val as 'bfs' | 'dfs')}
              data={[
                { label: 'BFS (breadth-first)', value: 'bfs' },
                { label: 'DFS (depth-first)', value: 'dfs' },
              ]}
            />
          </div>

          <NumberInput
            label="Token Budget"
            description="Max tokens for answer"
            size="xs"
            min={500}
            max={8000}
            step={500}
            value={budget}
            onChange={(val) => setBudget(Number(val) || 2000)}
            style={{ width: 140 }}
          />

          <Button
            size="sm"
            variant="gradient"
            gradient={{ from: 'indigo', to: 'violet', deg: 135 }}
            leftSection={isLoading ? <Loader size="xs" color="white" /> : <IconSearch size={14} />}
            onClick={handleQuery}
            disabled={!question.trim() || isLoading}
          >
            Query Graph
          </Button>
        </Group>

        {/* Mode hints */}
        <Group gap="xs">
          <Badge size="xs" variant="dot" color="indigo">
            BFS — best for concept exploration, "what relates to X"
          </Badge>
          <Badge size="xs" variant="dot" color="violet">
            DFS — best for path tracing, "how does X connect to Y"
          </Badge>
        </Group>

        {/* Error */}
        {error && (
          <Alert
            icon={<IconAlertTriangle size={16} />}
            color="red"
            title="Query Failed"
            onClose={() => setError(null)}
            withCloseButton
          >
            {error}
          </Alert>
        )}

        {/* Result */}
        {result && (
          <>
            <Divider />
            <Stack gap="xs">
              {/* Answer */}
              <Paper p="sm" bg="var(--mantine-color-dark-7)" radius="md">
                <Text size="sm" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                  {result.answer}
                </Text>
              </Paper>

              {/* Metadata */}
              <Group gap="xs">
                <Badge
                  size="sm"
                  variant="light"
                  color="teal"
                  leftSection={<IconCheck size={10} />}
                >
                  {result.query_mode.toUpperCase()} traversal
                </Badge>

                {result.nodes_traversed.length > 0 && (
                  <Badge
                    size="sm"
                    variant="light"
                    color="indigo"
                    leftSection={<IconGitBranch size={10} />}
                  >
                    {result.nodes_traversed.length} nodes traversed
                  </Badge>
                )}

                {result.token_cost > 0 && (
                  <Badge
                    size="sm"
                    variant="light"
                    color="orange"
                    leftSection={<IconBolt size={10} />}
                  >
                    {result.token_cost.toLocaleString()} tokens
                  </Badge>
                )}
              </Group>

              {/* Traversal path */}
              {result.nodes_traversed.length > 0 && (
                <details>
                  <summary>
                    <Text size="xs" c="dimmed" style={{ cursor: 'pointer', display: 'inline' }}>
                      Show traversal path ({result.nodes_traversed.length} nodes)
                    </Text>
                  </summary>
                  <Code block mt={4} style={{ fontSize: 11, maxHeight: 120, overflow: 'auto' }}>
                    {result.nodes_traversed.join(' → ')}
                  </Code>
                </details>
              )}
            </Stack>
          </>
        )}
      </Stack>
    </Paper>
  );
}
