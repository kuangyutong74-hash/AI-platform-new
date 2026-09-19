// Dev: Vite proxy handles /api → localhost:8010
// Prod: set VITE_API_URL to your backend URL, e.g. https://your-backend.onrender.com
const BASE_URL = (import.meta.env.VITE_API_URL || '') + '/api/v1';

type LaunchContext = { sessionId?: string; launchCode?: string; coreApiUrl?: string };
let moduleTokenPromise: Promise<string | null> | null = null;

function readLaunchContext(): LaunchContext | null {
  try {
    const launch = JSON.parse(window.name || '');
    if (launch?.namespace !== 'ai-bole.launch-context.v1') return null;
    sessionStorage.setItem('ai-bole.story.launch-context', JSON.stringify(launch.context));
    return launch.context;
  } catch {
    try { return JSON.parse(sessionStorage.getItem('ai-bole.story.launch-context') || 'null'); }
    catch { return null; }
  }
}

async function getModuleToken(): Promise<string | null> {
  if (moduleTokenPromise) return moduleTokenPromise;
  moduleTokenPromise = (async () => {
    const context = readLaunchContext();
    if (!context?.sessionId || !context.launchCode) return null;
    const storageKey = `ai-bole.story.module-token.${context.sessionId}`;
    const existing = sessionStorage.getItem(storageKey);
    if (existing) return existing;
    const coreApiUrl = (context.coreApiUrl || 'http://localhost:8020').replace(/\/$/, '');
    const response = await fetch(`${coreApiUrl}/api/v1/module-authorizations:exchange`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ launchCode: context.launchCode }),
    });
    if (!response.ok) throw new ApiError('启动授权已失效，请返回探索星球重新进入', response.status);
    const payload = await response.json() as { token: string };
    sessionStorage.setItem(storageKey, payload.token);
    return payload.token;
  })();
  return moduleTokenPromise;
}

export async function authorizedFetch(url: string, options: RequestInit = {}) {
  const token = await getModuleToken();
  const headers = new Headers(options.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(url, {...options, headers, credentials: 'include'});
}

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  const token = await getModuleToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (response.status === 204) {
    return undefined as T;
  }

  // Safe JSON parse — backend may return plain text on unhandled errors
  let data: any;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    data = await response.json();
  } else {
    const text = await response.text();
    throw new ApiError(text.slice(0, 200) || `服务器错误 (HTTP ${response.status})`, response.status);
  }

  if (!response.ok) {
    throw new ApiError(data?.detail || `请求失败 (HTTP ${response.status})`, response.status);
  }

  return data as T;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export { BASE_URL };
