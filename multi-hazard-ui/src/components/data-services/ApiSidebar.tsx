import { useState } from 'react';
import { ChevronDown, ChevronRight, Wrench, Book } from 'lucide-react';
import type { OpenApiGroup } from '../../types/openApiSchema';
import type { Selection } from '../../types/dataServices';

const METHOD_COLORS: Record<string, string> = {
  GET: 'text-hub-400',
  POST: 'text-amber-500',
  PUT: 'text-purple-500',
  PATCH: 'text-purple-500',
  DELETE: 'text-red-500',
};

export function ApiSidebar({
  groups,
  selected,
  onSelect,
}: {
  groups: OpenApiGroup[];
  selected: Selection;
  onSelect: (s: Selection) => void;
}) {
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set(groups.map((g) => g.key)));

  function toggleGroup(key: string) {
    setOpenGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  return (
    <nav className="text-sm">
      <button
        type="button"
        onClick={() => onSelect({ type: 'overview' })}
        className={`w-full flex items-center gap-2 px-3 py-2 rounded-md mb-1 text-left font-medium transition-colors ${
          selected.type === 'overview' ? 'bg-hub-100 text-hub-800' : 'text-gray-600 hover:bg-gray-50'
        }`}
      >
        <Book className="size-4 shrink-0" />
        Overview
      </button>

      <button
        type="button"
        onClick={() => onSelect({ type: 'builder' })}
        className={`w-full flex items-center gap-2 px-3 py-2 rounded-md mb-3 text-left font-medium transition-colors ${
          selected.type === 'builder' ? 'bg-hub-100 text-hub-800' : 'text-gray-600 hover:bg-gray-50'
        }`}
      >
        <Wrench className="size-4 shrink-0" />
        Dataset URL builder
      </button>

      <div className="border-t border-gray-200 pt-3">
        {groups.map((group) => (
          <div key={group.key} className="mb-1">
            <button
              type="button"
              onClick={() => toggleGroup(group.key)}
              className="w-full flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-gray-500 uppercase tracking-wide"
            >
              {openGroups.has(group.key) ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
              {group.label}
            </button>
            {openGroups.has(group.key) && (
              <div className="ml-2">
                {group.subgroups.map((subgroup) => (
                  <div key={subgroup.key} className="mb-1">
                    {subgroup.label !== 'General' && (
                      <p className="px-3 py-1 text-[11px] font-semibold text-gray-400">{subgroup.label}</p>
                    )}
                    {subgroup.operations.map((op) => (
                      <button
                        key={op.operationId}
                        type="button"
                        onClick={() => onSelect({ type: 'operation', operationId: op.operationId })}
                        className={`w-full flex items-center gap-2 px-3 py-1.5 rounded-md text-left transition-colors ${
                          selected.type === 'operation' && selected.operationId === op.operationId
                            ? 'bg-hub-100 text-hub-800'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        <span className={`text-[10px] font-bold w-9 shrink-0 ${METHOD_COLORS[op.method] ?? 'text-gray-400'}`}>
                          {op.method}
                        </span>
                        <span className="truncate text-[13px]">{op.summary || op.path}</span>
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </nav>
  );
}
