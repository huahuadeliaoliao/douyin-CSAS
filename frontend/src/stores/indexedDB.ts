const DB_NAME = 'SentimentAnalysisDB'

export interface SentimentData {
  seq: number
  cid: string
  text: string
  create_time: string
  predicted_emotion: '厌恶' | '喜好' | '恐惧' | '悲伤' | '惊讶' | '愤怒' | '高兴'
}

export function openDB(videoId: string): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request: IDBOpenDBRequest = indexedDB.open(DB_NAME)
    request.onerror = (): void => {
      reject(request.error)
    }
    request.onsuccess = (): void => {
      const db: IDBDatabase = request.result
      if (!db.objectStoreNames.contains(videoId)) {
        db.close()
        const newVersion: number = db.version + 1
        const req2: IDBOpenDBRequest = indexedDB.open(DB_NAME, newVersion)
        req2.onupgradeneeded = (): void => {
          const upgradeDb: IDBDatabase = req2.result
          if (!upgradeDb.objectStoreNames.contains(videoId)) {
            upgradeDb.createObjectStore(videoId, { keyPath: 'seq' })
          }
        }
        req2.onsuccess = (): void => {
          resolve(req2.result)
        }
        req2.onerror = (): void => {
          reject(req2.error)
        }
      } else {
        resolve(db)
      }
    }
  })
}

export async function addSentimentData(videoId: string, data: SentimentData): Promise<void> {
  const db = await openDB(videoId)
  return await new Promise<void>((resolve, reject) => {
    const transaction: IDBTransaction = db.transaction(videoId, 'readwrite')
    transaction.oncomplete = (): void => resolve()
    transaction.onerror = (): void => reject(transaction.error)
    const store: IDBObjectStore = transaction.objectStore(videoId)
    const request: IDBRequest = store.put(data)
    request.onerror = (): void => reject(request.error)
  })
}

export async function getAllSentimentData(videoId: string): Promise<SentimentData[]> {
  const db = await openDB(videoId)
  return await new Promise<SentimentData[]>((resolve, reject) => {
    const transaction: IDBTransaction = db.transaction(videoId, 'readonly')
    const store: IDBObjectStore = transaction.objectStore(videoId)
    const request: IDBRequest = store.getAll()
    request.onsuccess = (): void => {
      resolve(request.result as SentimentData[])
    }
    request.onerror = (): void => reject(request.error)
  })
}
