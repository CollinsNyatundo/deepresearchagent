import { useEffect, useState } from 'react';
import {
  Paper,
  Loader,
  Center,
  Text,
  Stack,
  Group,
  Button,
  Tooltip,
} from '@mantine/core';
import {
  IconFileTypePdf,
  IconFileTypeDocx,
  IconFileSpreadsheet,
  IconMarkdown,
  IconDownload,
} from '@tabler/icons-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api } from '../../api/client';

type Props = {
  runId: string;
};

/** Download helper — triggers browser download from a Blob */
async function downloadExport(runId: string, format: string, filename: string) {
  const blob = await api.exportRun(runId, format);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const EXPORT_BUTTONS: {
  format: string;
  label: string;
  icon: React.ReactNode;
  ext: string;
  color: string;
}[] = [
  { format: 'pdf',      label: 'PDF',      icon: <IconFileTypePdf size={14} />,      ext: '.pdf',  color: 'red'    },
  { format: 'docx',     label: 'Word',     icon: <IconFileTypeDocx size={14} />,     ext: '.docx', color: 'blue'   },
  { format: 'xlsx',     label: 'Excel',    icon: <IconFileSpreadsheet size={14} />,  ext: '.xlsx', color: 'green'  },
  { format: 'markdown', label: 'Markdown', icon: <IconMarkdown size={14} />,         ext: '.md',   color: 'gray'   },
];

export function ReportView({ runId }: Props) {
  const [markdown, setMarkdown] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .getReport(runId)
      .then(setMarkdown)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [runId]);

  const handleDownload = async (format: string, ext: string) => {
    setDownloading(format);
    try {
      await downloadExport(runId, format, `research_${runId}${ext}`);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setDownloading(null);
    }
  };

  if (loading) {
    return (
      <Center py={100}>
        <Stack align="center" gap="xs">
          <Loader size="lg" />
          <Text size="sm" c="dimmed">Loading report…</Text>
        </Stack>
      </Center>
    );
  }

  if (error) {
    return (
      <Center py={100}>
        <Text c="red" size="sm">{error}</Text>
      </Center>
    );
  }

  return (
    <Stack gap="md">
      {/* Download header bar */}
      <Group justify="flex-end" gap="xs" px="xl" pt="md">
        <Text size="xs" c="dimmed" mr={4}>
          <IconDownload size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />
          Download as:
        </Text>
        {EXPORT_BUTTONS.map(({ format, label, icon, ext, color }) => (
          <Tooltip key={format} label={`Download ${label}`} withArrow>
            <Button
              size="xs"
              variant="light"
              color={color}
              leftSection={icon}
              loading={downloading === format}
              onClick={() => handleDownload(format, ext)}
            >
              {label}
            </Button>
          </Tooltip>
        ))}
      </Group>

      {/* Report content */}
      <Paper
        p="xl"
        shadow="xs"
        style={{ maxWidth: 900, margin: '0 auto', width: '100%' }}
      >
        <div className="report-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {markdown}
          </ReactMarkdown>
        </div>
      </Paper>
    </Stack>
  );
}
