// =============================================================================
// Khan Parcel — Frontend API Client
// =============================================================================

const API_BASE = '/api/v1';

export const tokenStorage = {
  getAccess: () => localStorage.getItem('kp_access_token'),
  getRefresh: () => localStorage.getItem('kp_refresh_token'),
  getUser: () => {
    try {
      return JSON.parse(localStorage.getItem('kp_user') || 'null');
    } catch {
      return null;
    }
  },
  setTokens: (access, refresh, user) => {
    localStorage.setItem('kp_access_token', access);
    localStorage.setItem('kp_refresh_token', refresh);
    if (user) localStorage.setItem('kp_user', JSON.stringify(user));
  },
  clear: () => {
    localStorage.removeItem('kp_access_token');
    localStorage.removeItem('kp_refresh_token');
    localStorage.removeItem('kp_user');
  },
};

export async function apiFetch(endpoint, options = {}) {
  const token = tokenStorage.getAccess();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401 && tokenStorage.getRefresh()) {
    // Try to refresh token
    const refreshed = await refreshToken();
    if (refreshed) {
      headers.Authorization = `Bearer ${tokenStorage.getAccess()}`;
      return fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    }
  }

  return res;
}

export async function refreshToken() {
  const refresh = tokenStorage.getRefresh();
  if (!refresh) return false;

  try {
    const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });

    if (res.ok) {
      const data = await res.json();
      tokenStorage.setTokens(data.access, refresh, tokenStorage.getUser());
      return true;
    }
  } catch (e) {
    console.error('Refresh token failed', e);
  }

  tokenStorage.clear();
  return false;
}
