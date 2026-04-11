import { useState } from 'react';
import {
  SimpleGrid,
  Paper,
  Title,
  Text,
  Group,
  Button,
  ThemeIcon,
  Stack,
  Badge,
  Loader,
} from '@mantine/core';
import {
  IconFileText,
  IconFileTypePdf,
  IconFileSpreadsheet,
  IconBrain,
  IconDownload,
  IconFileDescription,
} from '@tabler/icons-react';
import { api } from '../../api/client';

type Props = {
  runId: string;
};

type ExportFormat = {
  id: string;
  label: string;
  description: string;
  icon: typeof IconFileText;
  color: string;
  extension: string;
};

const FORMATS: ExportFormat[] = [
  {
    id: 'markdown',
    label: 'Markdown',
    description: 'Clean, portable research report',
    icon: IconFileText,
    color: 'gray',
    extension: '.md',
  },
  {
    id: 'pdf',
    label: 'PDF Document',
    description: 'Print-ready styled report',
    icon: IconFileTypePdf,
    color: 'red',
    extension: '.pdf',
  },
  {
    id: 'docx',
    label: 'Word Document',
    description: 'Editable document with formatting',
    icon: IconFileDescription,
    color: 'blue',
    extension: '.docx',
  },
  {
    id: 'xlsx',
    label: 'Excel Spreadsheet',
    description: 'Citations + research steps data',
    icon: IconFileSpreadsheet,
    color: 'green',
    extension: '.xlsx',
  },
  {
    id: 'mindmap_json',
    label: 'Mindmap JSON',
    description: 'G6-compatible graph for re-import',
    icon: IconBrain,
    color: 'violet',
    extension: '.json',
  },
];

export function ExportPanel({ runId }: Props) {
  const [loadingFormats, setLoadingFormats] = useState<Set<string>>(new Set());
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleDownload = async (format: ExportFormat) => {
    setLoadingFormats((prev) => new Set(prev).add(format.id));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[format.id];
      return next;
    });

    try {
      const blob = await api.exportRun(runId, format.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `research_${runId}${format.extension}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setErrors((prev) => ({
        ...prev,
        [format.id]: err instanceof Error ? err.message : 'Download failed',
      }));
    } finally {
      setLoadingFormats((prev) => {
        const next = new Set(prev);
        next.delete(format.id);
        return next;
      });
    }
  };

  return (
    <Stack gap="lg">
      <div>
        <Title order={4}>Export Research</Title>
        <Text size="sm" c="dimmed" mt={4}>
          Download your research in different formats for sharing and archival.
        </Text>
      </div>

      <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
        {FORMATS.map((fmt) => {
          const isLoading = loadingFormats.has(fmt.id);
          const error = errors[fmt.id];

          return (
            <Paper
              key={fmt.id}
              p="lg"
              radius="md"
              withBorder
              style={{
                cursor: 'pointer',
                transition: 'border-color 150ms, transform 150ms',
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = `var(--mantine-color-${fmt.color}-5)`;
                (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = '';
                (e.currentTarget as HTMLElement).style.transform = '';
              }}
            >
              <Stack gap="sm">
                <Group justify="space-between">
                  <ThemeIcon
                    size="lg"
                    radius="md"
                    color={fmt.color}
                    variant="light"
                  >
                    <fmt.icon size={20} />
                  </ThemeIcon>
                  <Badge size="xs" variant="light" color="gray">
                    {fmt.extension}
                  </Badge>
                </Group>

                <div>
                  <Text fw={600} size="sm">
                    {fmt.label}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {fmt.description}
                  </Text>
                </div>

                {error && (
                  <Text size="xs" c="red">
                    {error}
                  </Text>
                )}

                <Button
                  variant="light"
                  color={fmt.color}
                  size="sm"
                  fullWidth
                  leftSection={
                    isLoading ? (
                      <Loader size={14} />
                    ) : (
                      <IconDownload size={14} />
                    )
                  }
                  onClick={() => handleDownload(fmt)}
                  loading={isLoading}
                >
                  Download
                </Button>
              </Stack>
            </Paper>
          );
        })}
      </SimpleGrid>
    </Stack>
  );
}
