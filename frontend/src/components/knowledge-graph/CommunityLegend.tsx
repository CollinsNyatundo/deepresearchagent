/**
 * CommunityLegend — Color-coded chips per Leiden community.
 *
 * Allows toggling visibility of each community cluster in the
 * KnowledgeGraphView. Provides a clear visual legend mapping
 * community IDs to labels.
 */

import {
  Group,
  Badge,
  Text,
  Stack,
  Tooltip,
  ActionIcon,
  Paper,
  Title,
} from '@mantine/core';

import { IconEye, IconEyeOff } from '@tabler/icons-react';
import type { KGCommunity } from '../../types/api';

// Curated community palette — vibrant, distinguishable colors
const COMMUNITY_COLORS = [
  '#4F46E5', // indigo
  '#059669', // emerald
  '#DC2626', // red
  '#D97706', // amber
  '#7C3AED', // violet
  '#0891B2', // cyan
  '#BE185D', // pink
  '#65A30D', // lime
  '#EA580C', // orange
  '#0369A1', // sky
];

export function getCommunityColor(communityId: number): string {
  return COMMUNITY_COLORS[communityId % COMMUNITY_COLORS.length];
}

type CommunityLegendProps = {
  communities: KGCommunity[];
  hiddenCommunities: Set<number>;
  onToggleCommunity: (id: number) => void;
};

export function CommunityLegend({
  communities,
  hiddenCommunities,
  onToggleCommunity,
}: CommunityLegendProps) {
  if (communities.length === 0) return null;

  return (
    <Paper p="sm" withBorder radius="md">
      <Title order={6} mb="xs" c="dimmed">
        Communities
      </Title>
      <Stack gap={6}>
        {communities.map((community) => {
          const color = getCommunityColor(community.id);
          const isHidden = hiddenCommunities.has(community.id);

          return (
            <Group key={community.id} justify="space-between" gap="xs">
              <Group gap="xs">
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    backgroundColor: color,
                    opacity: isHidden ? 0.3 : 1,
                    flexShrink: 0,
                  }}
                />
                <Text
                  size="xs"
                  c={isHidden ? 'dimmed' : undefined}
                  style={{ textDecoration: isHidden ? 'line-through' : 'none' }}
                >
                  {community.label}
                </Text>
              </Group>
              <Group gap={4}>
                <Tooltip label={`${community.node_count} nodes`} withArrow>
                  <Badge
                    size="xs"
                    variant="outline"
                    color="gray"
                    style={{ cursor: 'default' }}
                  >
                    {community.node_count}
                  </Badge>
                </Tooltip>
                <Tooltip
                  label={isHidden ? 'Show community' : 'Hide community'}
                  withArrow
                >
                  <ActionIcon
                    size="xs"
                    variant="subtle"
                    color={isHidden ? 'gray' : 'indigo'}
                    onClick={() => onToggleCommunity(community.id)}
                  >
                    {isHidden ? <IconEyeOff size={12} /> : <IconEye size={12} />}
                  </ActionIcon>
                </Tooltip>
              </Group>
            </Group>
          );
        })}
      </Stack>
    </Paper>
  );
}
