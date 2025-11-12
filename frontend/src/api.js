export const API_BASE = (() => {
  const originBase = `${window.location.origin}/api`;
  const isLocalPreview = (location.hostname === 'localhost');
  const previewFallback = 'http://localhost:8001/api';
  return window.FETRACE_API_BASE || (isLocalPreview ? previewFallback : originBase);
})();

async function httpGetJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`接口返回错误：${resp.status}`);
  return await resp.json();
}

export async function fetchNames() {
  try {
    const list = await httpGetJSON(`${API_BASE}/names`);
    return Array.isArray(list) ? list : [];
  } catch (e) {
    console.error('加载姓名列表失败：', e);
    return [];
  }
}

export async function fetchPerson(name) {
  return await httpGetJSON(`${API_BASE}/person?name=${encodeURIComponent(name)}`);
}