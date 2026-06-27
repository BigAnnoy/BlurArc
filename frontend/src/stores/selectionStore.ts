import { api } from '../services/api';

export interface SelectionState {
  selectedIds: Set<string>;
  totalMatching: number | null;
  isLoadingAllIds: boolean;
}

export function createSelectionStore() {
  let state: SelectionState = {
    selectedIds: new Set(),
    totalMatching: null,
    isLoadingAllIds: false,
  };

  const listeners = new Set<() => void>();

  const subscribe = (listener: () => void) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  };

  const notify = () => listeners.forEach(l => l());

  const toggle = (id: string) => {
    const next = new Set(state.selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      if (next.size >= 1000) {
        return; // 限制最多 1000 张
      }
      next.add(id);
    }
    state = { ...state, selectedIds: next };
    notify();
  };

  const selectAll = (ids: string[]) => {
    state = { ...state, selectedIds: new Set(ids) };
    notify();
  };

  const clearAll = () => {
    state = { ...state, selectedIds: new Set(), totalMatching: null };
    notify();
  };

  const loadAllMatchingIds = async (params?: {
    favorite?: boolean;
    type?: string;
    path?: string;
    not_in_album?: boolean;
    album_id?: number;
    from?: string;
    to?: string;
  }) => {
    state = { ...state, isLoadingAllIds: true };
    notify();
    
    try {
      const res = await api.getPhotoIds(params);
      state = {
        ...state,
        selectedIds: new Set(res.ids.map(String)),
        totalMatching: res.total,
        isLoadingAllIds: false,
      };
    } catch (error) {
      state = { ...state, isLoadingAllIds: false };
    }
    notify();
  };

  return {
    get state() { return state; },
    subscribe,
    toggle,
    selectAll,
    clearAll,
    loadAllMatchingIds,
  };
}
