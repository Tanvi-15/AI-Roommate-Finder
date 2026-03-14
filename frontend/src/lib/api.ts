const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export { API_URL, WS_URL };

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

// Auth
export const authApi = {
  register: (data: { email: string; password: string; name: string; phone_number?: string | null }) =>
    request<{ user: any }>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  login: (data: { email: string; password: string }) =>
    request<{ user: any }>('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  googleUrl: () => request<{ url: string | null }>('/auth/google/url'),
  googleCallback: (code: string, state: string) =>
    request<{ user: any }>('/auth/google/callback', { method: 'POST', body: JSON.stringify({ code, state }) }),
  me: () => request<{ user: any }>('/auth/me'),
  updateProfile: (data: { name?: string; questionnaire?: Record<string, unknown> }) =>
    request<{ user: any }>('/auth/me', { method: 'PUT', body: JSON.stringify(data) }),
  logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST' }),
};

// Health
export const healthApi = {
  check: () => request<{ status: string }>('/health'),
  root: () => request<{ status: string; agents: number; rooms: number }>('/'),
};

// Agents
export const agentsApi = {
  create: (data: { user_id: string; name: string; questionnaire: any }) =>
    request<{ status: string; user_id: string; name: string }>('/agents', { method: 'POST', body: JSON.stringify(data) }),
  list: () => request<{ user_id: string; name: string }[]>('/agents'),
  validate: (userId: string) =>
    request<{ user_id: string; name: string; validated: boolean; results: any[] }>(`/agents/${encodeURIComponent(userId)}/validate`, { method: 'POST', body: JSON.stringify({}) }),
};

// Rooms
export const roomsApi = {
  create: (data: { user_a_id: string; user_b_id: string }) =>
    request<{ room_id: string; agent_a: string; agent_b: string; total_turns: number; phases: any[] }>('/rooms', { method: 'POST', body: JSON.stringify(data) }),
  get: (roomId: string) => request<any>(`/rooms/${roomId}`),
};

// Matches
export const matchesApi = {
  list: (userId: string, includeIncompatible = false) =>
    request<any[]>(`/matches?user_id=${encodeURIComponent(userId)}&include_incompatible=${includeIncompatible}`),
  counts: (userId: string) =>
    request<{ strong: number; conditional: number; incompatible: number; total: number }>(`/matches/counts?user_id=${encodeURIComponent(userId)}`),
  get: (matchId: string) => request<any>(`/matches/${matchId}`),
};

// Clone chat (talk to my clone)
export const cloneApi = {
  intro: () => request<{ intro: string }>('/clone/intro'),
  chat: (message: string, history: { role: string; content: string }[]) =>
    request<{ reply: string }>('/clone/chat', {
      method: 'POST',
      body: JSON.stringify({ message, history }),
    }),
};

// Users (candidate discovery for Setup Match)
export const usersApi = {
  candidates: (skip = 0, limit = 50) =>
    request<{
      candidates: {
        email: string;
        name: string;
        city: string;
        neighborhood: string;
        questionnaire: Record<string, unknown>;
        photos: string[];
        profile_picture_url?: string;
        same_location: boolean;
        location_match_score: number;
      }[];
      total: number;
      skip: number;
      limit: number;
    }>(`/users/candidates?skip=${skip}&limit=${limit}`),
};

// Photos
export const photosApi = {
  upload: async (files: File[]) => {
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    const res = await fetch(`${API_URL}/auth/me/photos`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(body.detail || `Upload failed: ${res.status}`);
    }
    return res.json() as Promise<{ photos: string[] }>;
  },
};

// Like / Pass
export const interactionsApi = {
  like: (targetEmail: string) =>
    request<{ status: string; message: string }>('/matches/like', {
      method: 'POST',
      body: JSON.stringify({ target_email: targetEmail }),
    }),
  pass: (targetEmail: string) =>
    request<{ status: string }>('/matches/pass', {
      method: 'POST',
      body: JSON.stringify({ target_email: targetEmail }),
    }),
};
