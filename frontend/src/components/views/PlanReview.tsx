import { useState } from 'react';
import {
  Stack,
  Paper,
  Title,
  Text,
  Group,
  Button,
  Badge,
  ActionIcon,
  TextInput,
  Checkbox,
  ThemeIcon,
  Alert,
} from '@mantine/core';
import {
  IconPlus,
  IconTrash,
  IconEdit,
  IconCheck,
  IconX,
  IconPlayerPlay,
  IconRefresh,
  IconClock,
  IconRouteSquare,
} from '@tabler/icons-react';
import type { PlanPreview } from '../../types/api';

type Props = {
  preview: PlanPreview;
  query: string;
  onApprove: (
    steps: string[],
    subQueries: string[],
    exportFormats: string[],
  ) => void;
  onRegenerate: () => void;
  isLoading?: boolean;
};

export function PlanReview({
  preview,
  query,
  onApprove,
  onRegenerate,
  isLoading = false,
}: Props) {
  const [steps, setSteps] = useState<string[]>([...preview.plan.steps]);
  const [subQueries, setSubQueries] = useState<string[]>([
    ...preview.sub_queries,
  ]);
  const [exportFormats, setExportFormats] = useState<string[]>([
    'markdown',
    'pdf',
  ]);
  const [editingStep, setEditingStep] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');
  const [editingQuery, setEditingQuery] = useState<number | null>(null);
  const [queryEditValue, setQueryEditValue] = useState('');
  const [newStepValue, setNewStepValue] = useState('');

  const handleEditStep = (idx: number) => {
    setEditingStep(idx);
    setEditValue(steps[idx]);
  };

  const handleSaveStep = () => {
    if (editingStep !== null && editValue.trim()) {
      const newSteps = [...steps];
      newSteps[editingStep] = editValue.trim();
      setSteps(newSteps);
    }
    setEditingStep(null);
    setEditValue('');
  };

  const handleDeleteStep = (idx: number) => {
    setSteps(steps.filter((_, i) => i !== idx));
  };

  const handleAddStep = () => {
    if (newStepValue.trim()) {
      setSteps([...steps, newStepValue.trim()]);
      setNewStepValue('');
    }
  };

  const handleEditQuery = (idx: number) => {
    setEditingQuery(idx);
    setQueryEditValue(subQueries[idx]);
  };

  const handleSaveQuery = () => {
    if (editingQuery !== null && queryEditValue.trim()) {
      const newQueries = [...subQueries];
      newQueries[editingQuery] = queryEditValue.trim();
      setSubQueries(newQueries);
    }
    setEditingQuery(null);
    setQueryEditValue('');
  };

  const handleDeleteQuery = (idx: number) => {
    setSubQueries(subQueries.filter((_, i) => i !== idx));
  };

  const toggleFormat = (format: string) => {
    setExportFormats((prev) =>
      prev.includes(format)
        ? prev.filter((f) => f !== format)
        : [...prev, format],
    );
  };

  const allFormats = [
    { id: 'markdown', label: 'Markdown (.md)', emoji: '📝' },
    { id: 'pdf', label: 'PDF (.pdf)', emoji: '📕' },
    { id: 'docx', label: 'Word (.docx)', emoji: '📘' },
    { id: 'xlsx', label: 'Excel (.xlsx)', emoji: '📊' },
    { id: 'mindmap_json', label: 'Mindmap (.json)', emoji: '🧠' },
  ];

  return (
    <Stack gap="lg">
      {/* ─── Header ──────────────────────────────────────────── */}
      <Paper p="lg" radius="md" withBorder>
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={4}>Research Plan Review</Title>
            <Text size="sm" c="dimmed" mt={4}>
              Review and customize the research plan before execution.
            </Text>
          </div>
          <Group gap="xs">
            <Badge
              leftSection={<IconClock size={12} />}
              variant="light"
              color="blue"
              size="lg"
            >
              ~{Math.round(preview.estimated_duration_minutes)} min
            </Badge>
            <Badge
              leftSection={<IconRouteSquare size={12} />}
              variant="light"
              color="violet"
              size="lg"
            >
              {preview.estimated_cycles} cycles
            </Badge>
          </Group>
        </Group>

        <Alert color="blue" variant="light" mt="md">
          <Text size="sm">
            <strong>Query:</strong> {query}
          </Text>
        </Alert>
      </Paper>

      {/* ─── Research Steps ──────────────────────────────────── */}
      <Paper p="lg" radius="md" withBorder>
        <Title order={5} mb="md">
          📋 Research Steps ({steps.length})
        </Title>

        <Stack gap="xs">
          {steps.map((step, idx) => (
            <Paper
              key={idx}
              p="sm"
              radius="sm"
              withBorder
              style={{
                borderColor:
                  editingStep === idx
                    ? 'var(--mantine-color-indigo-5)'
                    : undefined,
              }}
            >
              {editingStep === idx ? (
                <Group gap="xs">
                  <TextInput
                    value={editValue}
                    onChange={(e) => setEditValue(e.currentTarget.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSaveStep()}
                    style={{ flex: 1 }}
                    size="sm"
                    autoFocus
                  />
                  <ActionIcon
                    color="green"
                    variant="light"
                    onClick={handleSaveStep}
                  >
                    <IconCheck size={16} />
                  </ActionIcon>
                  <ActionIcon
                    color="gray"
                    variant="light"
                    onClick={() => setEditingStep(null)}
                  >
                    <IconX size={16} />
                  </ActionIcon>
                </Group>
              ) : (
                <Group justify="space-between">
                  <Group gap="sm">
                    <ThemeIcon
                      size="sm"
                      variant="light"
                      color="indigo"
                      radius="xl"
                    >
                      <Text size="xs" fw={700}>
                        {idx + 1}
                      </Text>
                    </ThemeIcon>
                    <Text size="sm">{step}</Text>
                  </Group>
                  <Group gap={4}>
                    <ActionIcon
                      size="sm"
                      variant="subtle"
                      color="blue"
                      onClick={() => handleEditStep(idx)}
                    >
                      <IconEdit size={14} />
                    </ActionIcon>
                    <ActionIcon
                      size="sm"
                      variant="subtle"
                      color="red"
                      onClick={() => handleDeleteStep(idx)}
                      disabled={steps.length <= 1}
                    >
                      <IconTrash size={14} />
                    </ActionIcon>
                  </Group>
                </Group>
              )}
            </Paper>
          ))}

          {/* Add new step */}
          <Group gap="xs">
            <TextInput
              placeholder="Add a new research step..."
              value={newStepValue}
              onChange={(e) => setNewStepValue(e.currentTarget.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddStep()}
              style={{ flex: 1 }}
              size="sm"
            />
            <Button
              size="sm"
              variant="light"
              leftSection={<IconPlus size={14} />}
              onClick={handleAddStep}
              disabled={!newStepValue.trim()}
            >
              Add
            </Button>
          </Group>
        </Stack>
      </Paper>

      {/* ─── Sub-Queries ─────────────────────────────────────── */}
      {subQueries.length > 0 && (
        <Paper p="lg" radius="md" withBorder>
          <Title order={5} mb="md">
            🔍 Search Sub-Queries ({subQueries.length})
          </Title>

          <Stack gap="xs">
            {subQueries.map((sq, idx) => (
              <Paper key={idx} p="sm" radius="sm" withBorder>
                {editingQuery === idx ? (
                  <Group gap="xs">
                    <TextInput
                      value={queryEditValue}
                      onChange={(e) =>
                        setQueryEditValue(e.currentTarget.value)
                      }
                      onKeyDown={(e) =>
                        e.key === 'Enter' && handleSaveQuery()
                      }
                      style={{ flex: 1 }}
                      size="sm"
                      autoFocus
                    />
                    <ActionIcon
                      color="green"
                      variant="light"
                      onClick={handleSaveQuery}
                    >
                      <IconCheck size={16} />
                    </ActionIcon>
                    <ActionIcon
                      color="gray"
                      variant="light"
                      onClick={() => setEditingQuery(null)}
                    >
                      <IconX size={16} />
                    </ActionIcon>
                  </Group>
                ) : (
                  <Group justify="space-between">
                    <Text size="sm">{sq}</Text>
                    <Group gap={4}>
                      <ActionIcon
                        size="sm"
                        variant="subtle"
                        color="blue"
                        onClick={() => handleEditQuery(idx)}
                      >
                        <IconEdit size={14} />
                      </ActionIcon>
                      <ActionIcon
                        size="sm"
                        variant="subtle"
                        color="red"
                        onClick={() => handleDeleteQuery(idx)}
                        disabled={subQueries.length <= 1}
                      >
                        <IconTrash size={14} />
                      </ActionIcon>
                    </Group>
                  </Group>
                )}
              </Paper>
            ))}
          </Stack>
        </Paper>
      )}

      {/* ─── Export Formats ───────────────────────────────────── */}
      <Paper p="lg" radius="md" withBorder>
        <Title order={5} mb="md">
          📦 Export Formats
        </Title>

        <Group gap="sm">
          {allFormats.map((fmt) => (
            <Checkbox
              key={fmt.id}
              label={`${fmt.emoji} ${fmt.label}`}
              checked={exportFormats.includes(fmt.id)}
              onChange={() => toggleFormat(fmt.id)}
              size="sm"
            />
          ))}
        </Group>
      </Paper>

      {/* ─── Actions ─────────────────────────────────────────── */}
      <Group justify="space-between">
        <Button
          variant="subtle"
          color="gray"
          leftSection={<IconRefresh size={16} />}
          onClick={onRegenerate}
          loading={isLoading}
        >
          Regenerate Plan
        </Button>

        <Button
          size="lg"
          variant="gradient"
          gradient={{ from: 'indigo', to: 'violet', deg: 135 }}
          leftSection={<IconPlayerPlay size={20} />}
          onClick={() => onApprove(steps, subQueries, exportFormats)}
          loading={isLoading}
          disabled={steps.length === 0}
        >
          Approve & Start Research
        </Button>
      </Group>
    </Stack>
  );
}
