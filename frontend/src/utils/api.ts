import request from './request'

// 登录接口
export interface LoginParams {
  cookie: string
}

export const login = async (data: LoginParams) => {
  const res = await request.post('/login', data)
  return res.data
}

// 获取所有存储的视频数据
export const getAllStoreVideos = async () => {
  const res = await request.get('/all_store_videos')
  return res.data
}

// 获取单个视频信息，需要传递 video_id 参数
export const getVideoInfo = async (videoId: string) => {
  const res = await request.get('/video_info', {
    params: { video_id: videoId },
  })
  return res.data
}

// 获取视频评论（返回 NDJSON 流数据），需要传递 video_id 参数
export const fetchComments = async (videoId: string) => {
  const res = await request.get('/fetch_comments', {
    params: { video_id: videoId },
    responseType: 'text',
  })
  return res.data
}

// 获取视频评论回复（返回 NDJSON 流数据），需要传递 video_id 参数
export const fetchCommentsReplies = async (videoId: string) => {
  const res = await request.get('/fetch_comments_replies', {
    params: { video_id: videoId },
    responseType: 'text',
  })
  return res.data
}

// 情感分析管道（返回 NDJSON 流数据），需要传递 video_id 参数，start 参数默认为 0
export async function* sentimentPipeline(
  videoId: string,
  start: number = 0,
  signal?: AbortSignal,
): AsyncGenerator<unknown, void, unknown> {
  const url = `/api/sentiment_pipeline?video_id=${videoId}&start=${start}`
  const response = await fetch(url, { signal })
  if (!response.ok || !response.body) {
    throw new Error('网络请求失败或响应体为空')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.trim()) {
          try {
            const data = JSON.parse(line)
            yield data
          } catch (e) {
            console.error('解析 JSON 出错：', e)
          }
        }
      }
    }

    if (buffer.trim()) {
      try {
        yield JSON.parse(buffer)
      } catch (e) {
        console.error('解析最后 JSON 出错：', e)
      }
    }
  } catch (error: unknown) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.log('Fetch aborted')
    }
    throw error
  }
}

// 文本推理接口，需要在请求体中传入 text 字段
export const inferText = async (text: string) => {
  const res = await request.post('/infer_text', { text })
  return res.data
}

// 取消抓取评论任务接口，需要传入 video_id 参数
export const cancelFetchComments = async (videoId: string) => {
  const res = await request.get('/cancel_fetch_comments', {
    params: { video_id: videoId },
  })
  return res.data
}

// 查询任务进度接口，可选传入 video_id 参数
export const getTaskProgress = async (videoId?: string) => {
  const res = await request.get('/task_progress', {
    params: videoId ? { video_id: videoId } : {},
  })
  return res.data
}
