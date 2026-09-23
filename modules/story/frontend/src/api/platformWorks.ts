import { getStory, getStoryMessages } from './endpoints';
import { buildCompleteStoryText } from '../utils/storyPresentation';

const PLATFORM_CORE_URL = import.meta.env.VITE_PLATFORM_CORE_URL || 'http://localhost:8020';
const SOURCE_PREFIX = 'story:';

type ArtifactCollection = {
  artifacts?: Array<{ moduleId?: string; kind?: string; sourceResourceId?: string | null }>;
};
export type CollectedStoryKind = 'highlight' | 'manual_work';

async function responseError(response: Response): Promise<string> {
  try {
    const body = await response.json() as { detail?: string };
    if (body.detail) return body.detail;
  } catch {
    // Use a stable child-friendly fallback below.
  }
  if (response.status === 401) return '请先从探索星球登录学生账号，再添加到“我的作品”。';
  return '暂时没有添加成功，请稍后再试。';
}

export async function addStoryToMyWorks(storyId: number): Promise<void> {
  const [story, messages] = await Promise.all([getStory(storyId), getStoryMessages(storyId)]);
  const content = buildCompleteStoryText(messages);
  if (!content) throw new Error('这个故事还没有可保存的正文。');

  const response = await fetch(`${PLATFORM_CORE_URL}/api/explorer/works`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      module: 'story',
      work_type: 'full_story',
      title: (story.title || story.theme || '故事共创').trim().slice(0, 60),
      description: content.slice(0, 20000),
      source_id: `${SOURCE_PREFIX}${storyId}`,
    }),
  });
  if (!response.ok) throw new Error(await responseError(response));
}

export async function listCollectedStoryKinds(): Promise<Map<number, CollectedStoryKind>> {
  const response = await fetch(`${PLATFORM_CORE_URL}/api/v1/artifacts`, {
    credentials: 'include',
  });
  if (!response.ok) throw new Error(await responseError(response));
  const data = await response.json() as ArtifactCollection;
  const entries = (data.artifacts || []).flatMap((artifact) => {
    if (artifact.moduleId !== 'story'
      || !artifact.sourceResourceId?.startsWith(SOURCE_PREFIX)) return [];
    const id = Number(artifact.sourceResourceId.slice(SOURCE_PREFIX.length));
    const kind: CollectedStoryKind = artifact.kind === 'highlight' ? 'highlight' : 'manual_work';
    return Number.isFinite(id) ? [[id, kind] as const] : [];
  });
  return new Map(entries);
}

export async function listCollectedStoryIds(): Promise<Set<number>> {
  return new Set((await listCollectedStoryKinds()).keys());
}
