// Persistence: IndexedDB key-value store, falling back to localStorage, then to memory.
const DB = "flashcards-web", STORE = "kv";
let dbp: Promise<IDBDatabase | null> | null = null;
const mem = new Map<string, unknown>();

function open(): Promise<IDBDatabase | null> {
  dbp ??= new Promise((resolve) => {
    try {
      const req = indexedDB.open(DB, 1);
      req.onupgradeneeded = () => req.result.createObjectStore(STORE);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
      req.onblocked = () => resolve(null);
    } catch { resolve(null); }
  });
  return dbp;
}

function tx<T>(db: IDBDatabase, mode: IDBTransactionMode, run: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    const t = db.transaction(STORE, mode);
    const req = run(t.objectStore(STORE));
    t.oncomplete = () => resolve(req.result);
    t.onerror = t.onabort = () => reject(t.error);
  });
}

export async function kvGet<T>(key: string): Promise<T | undefined> {
  const db = await open();
  if (db) { try { return (await tx(db, "readonly", (s) => s.get(key))) as T | undefined; } catch { /* fall through */ } }
  try { const raw = localStorage.getItem("fc:" + key); if (raw !== null) return JSON.parse(raw) as T; } catch { /* ignore */ }
  return mem.get(key) as T | undefined;
}

export async function kvSet(key: string, value: unknown): Promise<void> {
  mem.set(key, value);
  const db = await open();
  if (db) { try { await tx(db, "readwrite", (s) => s.put(value, key)); return; } catch { /* fall through */ } }
  try { localStorage.setItem("fc:" + key, JSON.stringify(value)); } catch { /* memory only */ }
}

export async function kvClearAll(): Promise<void> {
  mem.clear();
  const db = await open();
  if (db) { try { await tx(db, "readwrite", (s) => s.clear()); } catch { /* ignore */ } }
  try { Object.keys(localStorage).filter((k) => k.startsWith("fc:")).forEach((k) => localStorage.removeItem(k)); } catch { /* ignore */ }
}

export async function requestPersistence(): Promise<boolean> {
  try { return (await navigator.storage?.persist?.()) ?? false; } catch { return false; }
}
