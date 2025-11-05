import os
import json
import threading
import time
from typing import Any, Dict, List, Optional

try:
    import xlrd
except Exception:
    xlrd = None


class Cache:
    def __init__(self):
        self._lock = threading.Lock()
        self.people: Optional[Dict[str, Any]] = None
        self.names: List[str] = []
        self.dirty: bool = False
        self._root: Optional[str] = None

    # -------- Preload --------
    def preload(self, root: str, doc_dir: str, fallback: Dict[str, Any]):
        self._root = root
        data = self._read_people_json(root)
        if data and not self._is_empty(data):
            self.people = data
        else:
            self.people = fallback

        excel_names = self._load_excel_names(doc_dir)
        json_names = []
        try:
            json_names = [p.get('name') for p in (self.people or {}).get('persons', []) if p.get('name')]
        except Exception:
            json_names = []
        merged = []
        seen = set()
        for n in (excel_names + json_names):
            if not n:
                continue
            low = str(n).lower()
            if low in seen:
                continue
            seen.add(low)
            merged.append(n)
        with self._lock:
            self.names = merged
            self.dirty = False

    def _read_people_json(self, root: str) -> Optional[Dict[str, Any]]:
        path = os.path.join(root, 'people.json')
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def _is_empty(self, data: Dict[str, Any]) -> bool:
        try:
            persons = (data or {}).get('persons')
            return not persons or len(persons) == 0
        except Exception:
            return True

    def _load_excel_names(self, doc_dir: str) -> List[str]:
        names: List[str] = []
        candidates: List[str] = []
        preferred = os.path.join(doc_dir, 'peoples.xls')
        if os.path.exists(preferred):
            candidates.append(preferred)
        if os.path.isdir(doc_dir):
            for f in os.listdir(doc_dir):
                if f.lower().endswith('.xls'):
                    p = os.path.join(doc_dir, f)
                    if p not in candidates:
                        candidates.append(p)
        if not candidates or not xlrd:
            return []
        path = candidates[0]
        try:
            wb = xlrd.open_workbook(path)
            sh = wb.sheet_by_index(0)
            name_col = 0
            if sh.nrows:
                header = [str(sh.cell_value(0, c)).strip().lower() for c in range(sh.ncols)]
                for i, h in enumerate(header):
                    if ('姓名' in h) or ('人物' in h) or ('人名' in h) or ('name' in h):
                        name_col = i
                        break
            for r in range(1, sh.nrows):
                val = sh.cell_value(r, name_col)
                if isinstance(val, str) and val.strip():
                    names.append(val.strip())
        except Exception:
            return []
        seen = set()
        uniq = []
        for n in names:
            low = n.lower()
            if low in seen:
                continue
            seen.add(low)
            uniq.append(n)
        return uniq

    # -------- Accessors --------
    def get_people_or_fallback(self, fallback: Dict[str, Any]) -> Dict[str, Any]:
        return self.people or fallback

    def get_names(self) -> List[str]:
        return self.names or []

    # -------- Mutators --------
    def upsert_person(self, person: Dict[str, Any], fallback: Dict[str, Any]):
        name = str(person.get('name', '')).strip()
        if not name:
            return
        with self._lock:
            base = self.people or fallback
            persons = (base or {}).get('persons') or []
            idx = None
            for i, p in enumerate(persons):
                if str(p.get('name', '')).strip().lower() == name.lower():
                    idx = i
                    break
            if idx is None:
                persons.append(person)
            else:
                persons[idx] = person
            if base is fallback:
                self.people = {'persons': persons}
            else:
                self.people['persons'] = persons
            # names 去重
            low_names = set([n.lower() for n in (self.names or [])])
            if name.lower() not in low_names:
                self.names.append(name)
            self.dirty = True

    # -------- Flush to disk --------
    def _save_people_json_atomic(self, data: Dict[str, Any]):
        if not self._root:
            return
        path = os.path.join(self._root, 'people.json')
        tmp = path + '.tmp'
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except Exception:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass

    def start_flush_thread(self, interval_sec: int = 30, logger=None):
        t = threading.Thread(target=self._periodic_flush, kwargs={'interval_sec': interval_sec, 'logger': logger}, daemon=True)
        t.start()

    def _periodic_flush(self, interval_sec: int = 30, logger=None):
        while True:
            time.sleep(interval_sec)
            try:
                do_write = False
                data: Dict[str, Any] = {'persons': []}
                with self._lock:
                    if self.dirty:
                        base = self.people or {'persons': []}
                        data = base if isinstance(base, dict) else {'persons': []}
                        self.dirty = False
                        do_write = True
                if do_write:
                    self._save_people_json_atomic(data)
                    if logger:
                        try:
                            logger.info("已将缓存写入 people.json（周期=%ss，persons=%d）", interval_sec, len((data or {}).get('persons', [])))
                        except Exception:
                            pass
            except Exception:
                if logger:
                    try:
                        logger.error("写入 people.json 失败，将在下次周期重试")
                    except Exception:
                        pass