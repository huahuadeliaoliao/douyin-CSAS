<template>
  <div class="import-modal">
    <!-- 返回按钮 -->
    <div class="modal-header">
      <button class="back-button" @click="$emit('close')">← 返回</button>
    </div>

    <!-- grid布局：两列，items-stretch使两列在垂直方向拉伸 -->
    <div class="modal-content grid grid-cols-2 gap-4 items-stretch">
      <!-- 左侧：卡片及进度 -->
      <div class="card-container flex flex-col p-4">
        <div class="card bg-base-100 w-full shadow-xl">
          <figure>
            <img :src="videoInfo?.cover_url || placeholderImg" alt="视频缩略图" />
          </figure>
          <div class="card-body">
            <h2 class="card-title">视频ID：{{ videoId }}</h2>
            <p>描述：{{ videoInfo?.description || '暂无描述' }}</p>
            <p>视频时长：{{ videoInfo?.duration || '-' }} 秒</p>
            <p>已存储评论数：{{ storedCommentCount }}</p>
            <p>已进行情绪分析评论数：{{ analyzedCommentCount }}</p>
            <p>视频评论数：{{ videoInfo?.stats.comment_count || '-' }}</p>
            <p>视频点赞数：{{ videoInfo?.stats.like_count || '-' }}</p>
            <p>视频收藏数：{{ videoInfo?.stats.favorite_count || '-' }}</p>
            <p>视频分享数：{{ videoInfo?.stats.share_count || '-' }}</p>
            <div class="card-actions justify-end">
              <!-- 新增情绪分析按钮 -->
              <button
                v-if="storedCommentCount > 0"
                class="btn btn-neutral ml-2"
                @click="handleSentimentAnalysis"
              >
                {{ isAnalyzing ? '停止分析' : '情绪分析' }}
              </button>
              <button class="btn btn-neutral ml-2" @click="handleImport">
                {{ taskProgress ? '停止导入' : '开始导入' }}
              </button>
            </div>
          </div>
        </div>
        <!-- 导入任务进度信息 -->
        <div v-if="taskProgress && taskProgress.progress" class="progress-info mt-4">
          <p>导入任务获取的评论数量：{{ taskProgress.progress.fetched || 0 }}</p>
          <p>导入任务存储的评论数量：{{ taskProgress.progress.stored || 0 }}</p>
        </div>
      </div>

      <!-- 右侧：情绪数据图表区域（始终渲染） -->
      <div class="flex flex-col flex-1 border">
        <!-- 两个图表上下排列，各自 flex-1 -->
        <div ref="chartOverall" class="w-full flex-1"></div>
        <div ref="chartTrend" class="w-full flex-1 mt-4"></div>

        <!-- 如果还没有情绪分析数据，就显示提示。否则正常绘制图表 -->
        <div v-if="sentimentData.length === 0" class="no-data-message">
          暂无情绪分析数据，请先获取评论并进行情绪分析
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import {
  getVideoInfo,
  getTaskProgress,
  fetchComments,
  cancelFetchComments,
  getAllStoreVideos,
  sentimentPipeline,
} from '@/utils/api'
import { addSentimentData, getAllSentimentData } from '@/stores/indexedDB'

interface VideoInfo {
  cover_url: string
  create_time: string
  description: string
  duration: number
  stats: {
    comment_count: number
    favorite_count: number
    like_count: number
    play_count: number
    share_count: number
  }
  video_id: string
}

interface TaskProgress {
  video_id: string
  progress: {
    fetched: number
    stored: number
  }
  status: 'running' | 'completed' | 'cancelled' | 'error'
  error?: string
}

interface GetTaskProgressResponse {
  fetch_comments?: TaskProgress
}

interface Video {
  video_id: string
  comment_count: number
}

export interface SentimentData {
  seq: number
  cid: string
  text: string
  create_time: string
  predicted_emotion: '厌恶' | '喜好' | '恐惧' | '悲伤' | '惊讶' | '愤怒' | '高兴'
}

const props = defineProps<{ videoId: string }>()

const videoInfo = ref<VideoInfo | null>(null)
const placeholderImg = 'https://via.placeholder.com/400x300?text=No+Image'
const taskProgress = ref<TaskProgress | null>(null)
const storedCommentCount = ref(0)
const analyzedCommentCount = ref(0)

// 情绪分析相关状态
const isAnalyzing = ref(false)
const sentimentAbortController = ref<AbortController | null>(null)
const sentimentData = ref<SentimentData[]>([])

// ECharts 容器引用
const chartOverall = ref<HTMLDivElement | null>(null)
const chartTrend = ref<HTMLDivElement | null>(null)
let overallChartInstance: echarts.ECharts | null = null
let trendChartInstance: echarts.ECharts | null = null

function initCharts(): void {
  if (chartOverall.value) {
    overallChartInstance = echarts.init(chartOverall.value)
  }
  if (chartTrend.value) {
    trendChartInstance = echarts.init(chartTrend.value)
  }
  updateCharts()
}

function updateCharts(): void {
  if (!overallChartInstance || !trendChartInstance) return

  const emotionCategories: SentimentData['predicted_emotion'][] = [
    '厌恶',
    '喜好',
    '恐惧',
    '悲伤',
    '惊讶',
    '愤怒',
    '高兴',
  ]
  const overallCounts: Record<SentimentData['predicted_emotion'], number> = {
    厌恶: 0,
    喜好: 0,
    恐惧: 0,
    悲伤: 0,
    惊讶: 0,
    愤怒: 0,
    高兴: 0,
  }
  sentimentData.value.forEach((item: SentimentData) => {
    overallCounts[item.predicted_emotion]++
  })
  const pieData = emotionCategories.map((emotion) => ({
    name: emotion,
    value: overallCounts[emotion],
  }))

  overallChartInstance.setOption({
    title: {
      text: '评论情绪分布',
      left: 'center',
      top: 10,
    },
    tooltip: { trigger: 'item' },
    legend: {
      top: 40,
    },
    grid: {
      top: 80,
      bottom: 40,
    },
    series: [
      {
        type: 'pie',
        radius: '50%',
        data: pieData,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)',
          },
        },
      },
    ],
  })

  const dateMap: Record<string, Record<SentimentData['predicted_emotion'], number>> = {}
  sentimentData.value.forEach((item: SentimentData) => {
    const date: string = item.create_time.slice(0, 10)
    if (!dateMap[date]) {
      dateMap[date] = {
        厌恶: 0,
        喜好: 0,
        恐惧: 0,
        悲伤: 0,
        惊讶: 0,
        愤怒: 0,
        高兴: 0,
      }
    }
    dateMap[date][item.predicted_emotion]++
  })
  const sortedDates: string[] = Object.keys(dateMap).sort()
  const seriesData = emotionCategories.map((emotion) => ({
    name: emotion,
    type: 'line',
    data: sortedDates.map((date: string) => dateMap[date][emotion]),
  }))

  trendChartInstance.setOption({
    title: {
      text: '评论情绪随时间变化',
      left: 'center',
      top: 10,
    },
    tooltip: { trigger: 'axis' },
    legend: {
      top: 40,
    },
    grid: {
      top: 80,
      bottom: 50,
    },
    xAxis: {
      type: 'category',
      data: sortedDates,
    },
    yAxis: {
      type: 'value',
    },
    series: seriesData,
  })
}

const updateAnalyzedCommentCount = async (): Promise<void> => {
  try {
    const storedData: SentimentData[] = await getAllSentimentData(props.videoId)
    analyzedCommentCount.value = storedData.length
  } catch (error: unknown) {
    console.error('获取已进行情绪分析评论数失败：', error)
  }
}

onMounted(async (): Promise<void> => {
  try {
    const info: VideoInfo = await getVideoInfo(props.videoId)
    videoInfo.value = info
  } catch (error: unknown) {
    console.error('获取视频详情失败：', error)
  }

  await nextTick()
  initCharts()

  // 立即更新已存储评论数，确保第一时间判断情绪分析按钮显示
  await updateStoredCommentCount()

  try {
    const storedData: SentimentData[] = await getAllSentimentData(props.videoId)
    sentimentData.value = storedData
    analyzedCommentCount.value = storedData.length // 初始赋值
    if (sentimentData.value.length > 0) {
      updateCharts()
    }
  } catch (error: unknown) {
    console.error('读取情绪分析数据失败：', error)
  }

  window.addEventListener('resize', handleResize)
})

const pollTaskProgress = async (): Promise<void> => {
  try {
    const data = await getTaskProgress(props.videoId)
    taskProgress.value = data.fetch_comments || null
  } catch (error: unknown) {
    console.error('获取任务进度失败：', error)
  }
}
const intervalId = setInterval(pollTaskProgress, 1000)

const updateStoredCommentCount = async (): Promise<void> => {
  try {
    const res = await getAllStoreVideos()
    const video: Video | undefined = res.video_data.find((v: Video) => v.video_id === props.videoId)
    storedCommentCount.value = video ? video.comment_count : 0
  } catch (error: unknown) {
    console.error('获取已存储评论数失败：', error)
  }
}
const intervalId2 = setInterval(updateStoredCommentCount, 5000)
const intervalId3 = setInterval(updateAnalyzedCommentCount, 5000)

const handleImport = async (): Promise<void> => {
  if (taskProgress.value) {
    try {
      await cancelFetchComments(props.videoId)
      taskProgress.value = null
    } catch (error: unknown) {
      console.error('取消导入任务失败：', error)
    }
  } else {
    try {
      await fetchComments(props.videoId)
    } catch (error: unknown) {
      console.error('开始导入任务失败：', error)
    }
  }
}

const handleSentimentAnalysis = async (): Promise<void> => {
  if (isAnalyzing.value) {
    if (sentimentAbortController.value) {
      sentimentAbortController.value.abort()
      sentimentAbortController.value = null
    }
    isAnalyzing.value = false
    console.log('停止情绪分析')
    return
  }
  isAnalyzing.value = true
  sentimentAbortController.value = new AbortController()
  console.log('开始情绪分析')
  try {
    for await (const rawData of sentimentPipeline(
      props.videoId,
      0,
      sentimentAbortController.value.signal,
    )) {
      const data = rawData as SentimentData
      const sentiment: SentimentData = {
        seq: data.seq,
        cid: data.cid,
        text: data.text,
        create_time: data.create_time,
        predicted_emotion: data.predicted_emotion,
      }
      await addSentimentData(props.videoId, sentiment)
      sentimentData.value.push(sentiment)
      updateCharts()

      if (!isAnalyzing.value) {
        console.log('情绪分析已被取消')
        break
      }
    }
  } catch (error: unknown) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.log('情绪分析请求已被中止')
    } else {
      console.error('情绪分析过程中出错：', error)
    }
  } finally {
    isAnalyzing.value = false
    sentimentAbortController.value = null
  }
}

function handleResize(): void {
  overallChartInstance?.resize()
  trendChartInstance?.resize()
}

onUnmounted((): void => {
  clearInterval(intervalId)
  clearInterval(intervalId2)
  clearInterval(intervalId3)
  window.removeEventListener('resize', handleResize)
  if (isAnalyzing.value && sentimentAbortController.value) {
    sentimentAbortController.value.abort()
    sentimentAbortController.value = null
  }
})
</script>

<style scoped>
.import-modal {
  position: fixed;
  top: 4rem;
  left: 0;
  width: 100%;
  height: calc(100% - 4rem);
  background: #fff;
  z-index: 100;
  padding: 1rem;
  overflow-y: auto;
}

.modal-header {
  position: absolute;
  top: 1rem;
  left: 1rem;
  z-index: 101;
}

.back-button {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: #333;
}

.modal-content {
  height: 100%;
}

.no-data-message {
  text-align: center;
  font-size: 1.2rem;
  color: #666;
  margin-top: 1rem;
}
</style>
