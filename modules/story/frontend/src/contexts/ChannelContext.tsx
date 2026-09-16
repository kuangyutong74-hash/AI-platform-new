import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

export type AgeGroup = '4-7' | '8-12';

export const AGE_GROUPS: AgeGroup[] = ['4-7', '8-12'];

export const AGE_GROUP_LABELS: Record<AgeGroup, string> = {
  '4-7': '4-7 岁',
  '8-12': '8-12 岁',
};

const STORAGE_KEY = 'story_create_age_group';

interface ChannelState {
  ageGroup: AgeGroup | null;
  setAgeGroup: (group: AgeGroup) => void;
}

const ChannelContext = createContext<ChannelState>({
  ageGroup: null,
  setAgeGroup: () => {},
});

function readStoredAgeGroup(): AgeGroup | null {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === '4-7' || stored === '8-12' ? stored : null;
}

export function ChannelProvider({ children }: { children: ReactNode }) {
  const [ageGroup, setAgeGroupState] = useState<AgeGroup>(() => readStoredAgeGroup() ?? '4-7');

  useEffect(() => {
    // 同步其它标签页对年龄段通道的修改
    function handleStorage(e: StorageEvent) {
      if (e.key === STORAGE_KEY) setAgeGroupState(readStoredAgeGroup() ?? '4-7');
    }
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  function setAgeGroup(group: AgeGroup) {
    localStorage.setItem(STORAGE_KEY, group);
    setAgeGroupState(group);
  }

  return (
    <ChannelContext.Provider value={{ ageGroup, setAgeGroup }}>
      {children}
    </ChannelContext.Provider>
  );
}

export function useChannel() {
  return useContext(ChannelContext);
}
