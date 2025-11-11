export const API_BASE = 'http://localhost:8001/api';

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