const DB = "siesco-offline-v1",
  STORE = "private";
async function database() {
  return new Promise<IDBDatabase>((resolve, reject) => {
    const r = indexedDB.open(DB, 1);
    r.onupgradeneeded = () => r.result.createObjectStore(STORE);
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}
async function operation<T>(
  mode: IDBTransactionMode,
  callback: (store: IDBObjectStore) => IDBRequest<T>,
) {
  const db = await database();
  try {
    return await new Promise<T>((resolve, reject) => {
      const tx = db.transaction(STORE, mode),
        request = callback(tx.objectStore(STORE));
      let value: T;
      request.onsuccess = () => {
        value = request.result;
      };
      tx.oncomplete = () => resolve(value);
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
export async function clearOffline() {
  sessionStorage.removeItem("siesco_offline_user");
  sessionStorage.removeItem("siesco_offline_membership");
  sessionStorage.removeItem("siesco_offline_lock");
  await operation("readwrite", (s) => s.clear());
}
export async function offlineIdentity(user: string, membership: string) {
  const previous = sessionStorage.getItem("siesco_offline_user");
  if (previous && previous !== user) await clearOffline();
  sessionStorage.setItem("siesco_offline_user", user);
  sessionStorage.setItem("siesco_offline_membership", membership);
}
async function key() {
  let k = await operation<CryptoKey | undefined>("readonly", (s) =>
    s.get("key"),
  );
  if (!k) {
    k = await crypto.subtle.generateKey(
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt", "decrypt"],
    );
    await operation("readwrite", (s) => s.put(k, "key"));
  }
  return k;
}
export async function saveOffline(id: string, value: unknown) {
  const user = sessionStorage.getItem("siesco_offline_user");
  if (!user) throw new Error("Entre no portal para preparar o modo offline.");
  const iv = crypto.getRandomValues(new Uint8Array(12)),
    content = await crypto.subtle.encrypt(
      { name: "AES-GCM", iv },
      await key(),
      new TextEncoder().encode(JSON.stringify(value)),
    );
  await operation("readwrite", (s) => s.put({ iv, content }, user + "/" + id));
}
export async function readOffline<T>(): Promise<T[]> {
  const user = sessionStorage.getItem("siesco_offline_user");
  if (!user) return [];
  const ids = await operation<IDBValidKey[]>("readonly", (s) => s.getAllKeys());
  const k = await key(),
    result: T[] = [];
  for (const id of ids) {
    if (typeof id !== "string" || !id.startsWith(user + "/")) continue;
    const item = await operation<{ iv: Uint8Array; content: ArrayBuffer }>(
      "readonly",
      (s) => s.get(id),
    );
    const bytes = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: new Uint8Array(item.iv) },
      k,
      item.content,
    );
    result.push(JSON.parse(new TextDecoder().decode(bytes)));
  }
  return result;
}
export async function removeOffline(id: string) {
  const user = sessionStorage.getItem("siesco_offline_user");
  await operation("readwrite", (s) => s.delete(user + "/" + id));
}
