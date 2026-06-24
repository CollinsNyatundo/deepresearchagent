/**
 * CommunityLegend — Color-coded chips per Leiden community.
 */

import { Eye, EyeOff } from 'lucide-react';
import type { KGCommunity } from '../../types/api';

const COMMUNITY_COLORS = [
  '#4F46E5', '#059669', '#DC2626', '#D97706', '#7C3AED',
  '#0891B2', '#BE185D', '#65A30D', '#EA580C', '#0369A1',
];

export function getCommunityColor(communityId: number): string {
  return COMMUNITY_COLORS[communityId % COMMUNITY_COLORS.length];
}

interface CommunityLegendProps {
  communities: KGCommunity[];
  hiddenCommunities: Set<number>;
  onToggleCommunity: (id: number) => void;
}

export function CommunityLegend({
  communities, hiddenCommunities, onToggleCommunity,
}: CommunityLegendProps) {
  if (communities.length === 0) return null;

  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
      <h6 className="text-[10px] uppercase tracking-wider text-[#555] font-semibold mb-2">Communities</h6>
      <div className="flex flex-col gap-1.5">
        {communities.map((community) => {
          const color = getCommunityColor(community.id);
          const isHidden = hiddenCommunities.has(community.id);

          return (
            <div key={community.id} className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <div
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: color, opacity: isHidden ? 0.3 : 1 }}
                />
                <span className={`text-xs truncate ${isHidden ? 'text-[#555] line-through' : 'text-[#999]'}`}>
                  {community.label}
                </span>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <span
                  className="px-1.5 py-0.5 text-[10px] rounded-full bg-white/[0.03] text-[#555] border border-white/[0.06] cursor-default"
                  title={`${community.node_count} nodes`}
                >
                  {community.node_count}
                </span>
                <button
                  onClick={() => onToggleCommunity(community.id)}
                  className={`p-1 rounded-lg transition-colors duration-150 cursor-pointer border-none ${
                    isHidden ? 'text-[#555] hover:text-[#999]' : 'text-[#4F46E5] hover:text-[#c8956c]'
                  }`}
                  title={isHidden ? 'Show community' : 'Hide community'}
                >
                  {isHidden ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
