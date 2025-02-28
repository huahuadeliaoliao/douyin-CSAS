<template>
  <div v-if="!showImportModal">
    <div
      ref="carouselRef"
      class="carousel flex flex-col justify-center"
      tabindex="0"
      @wheel.prevent="handleWheel"
      style="min-height: calc(100vh - 4rem)"
    >
      <!-- Header 容器 -->
      <div
        class="header-container absolute top-4 left-0 w-full px-4 flex flex-col md:flex-row justify-between items-center z-20"
      >
        <!-- 搜索和导入区域 -->
        <div class="search-import flex items-center mb-4 md:mb-0">
          <div class="relative">
            <input
              type="text"
              placeholder="搜索或导入视频id"
              class="input input-bordered w-full max-w-xs"
              v-model="searchQuery"
              @focus="dropdownOpen = true"
              @input="dropdownOpen = true"
              @blur="onBlurDropdown"
            />
            <div
              v-if="dropdownOpen && filteredVideos.length > 0"
              class="absolute mt-1 w-full bg-white border border-gray-300 rounded shadow-lg z-10"
            >
              <ul>
                <li
                  v-for="video in filteredVideos"
                  :key="video.video_id"
                  class="px-4 py-2 hover:bg-gray-100 cursor-pointer"
                  @mousedown.prevent="jumpToVideo(video)"
                >
                  {{ video.video_id }}
                </li>
              </ul>
            </div>
          </div>
          <!-- 导入按钮 -->
          <button class="btn btn-neutral ml-2" @click="handleImport">导入</button>
        </div>

        <!-- 进度条区域 -->
        <div class="progress-container flex flex-col items-center">
          <div class="progress-info mb-2 text-sm text-neutral-600">
            卡片位置：
            <input
              type="number"
              v-model.number="currentCardInput"
              @keyup.enter="jumpToCard"
              @blur="jumpToCard"
              @change="jumpToCard"
              min="1"
              :max="videos.length"
              class="card-input"
            />
            / {{ videos.length }}
          </div>
          <div
            class="radial-progress"
            :style="{ '--value': progressPercentage }"
            role="progressbar"
          >
            {{ progressPercentage }}%
          </div>
        </div>
      </div>

      <!-- 左右切换按钮 -->
      <button class="arrow left text-2xl md:text-3xl" v-if="activeIndex > 0" @click="scrollLeft">
        ←
      </button>
      <button
        class="arrow right text-2xl md:text-3xl"
        v-if="activeIndex < videos.length - 1"
        @click="scrollRight"
      >
        →
      </button>

      <!-- 卡片区域 -->
      <div v-if="videos.length > 0" class="cards-wrapper">
        <CardContainer
          v-for="(video, index) in videos"
          :key="video.video_id"
          class="card"
          :style="cardStyle(index)"
        >
          <CardBody
            class="group/card relative size-auto rounded-xl border border-black/[0.1] bg-gray-50 p-6 sm:w-[30rem] dark:border-white/[0.2] dark:bg-black dark:hover:shadow-2xl dark:hover:shadow-emerald-500/[0.1]"
          >
            <CardItem :translate-z="50" class="text-xl font-bold text-neutral-600 dark:text-white">
              视频ID：{{ video.video_id }}
            </CardItem>
            <CardItem
              as="p"
              translate-z="60"
              class="mt-2 max-w-sm text-sm text-neutral-500 dark:text-neutral-300"
            >
              已存储评论数：{{ video.comment_count }}
            </CardItem>
            <CardItem :translate-z="100" class="mt-4 w-full">
              <template v-if="videoInfos[video.video_id]">
                <img
                  :src="videoInfos[video.video_id].cover_url"
                  class="h-60 w-full rounded-xl object-cover group-hover/card:shadow-xl"
                  alt="thumbnail"
                />
              </template>
              <template v-else>
                <div class="flex w-52 flex-col gap-4">
                  <div class="skeleton h-32 w-full"></div>
                  <div class="skeleton h-4 w-28"></div>
                  <div class="skeleton h-4 w-full"></div>
                  <div class="skeleton h-4 w-full"></div>
                </div>
              </template>
            </CardItem>
            <!-- 视频详情 -->
            <div v-if="videoInfos[video.video_id]" class="mt-4 space-y-2">
              <CardItem
                as="p"
                translate-z="70"
                class="text-sm text-neutral-500 dark:text-neutral-300"
              >
                描述：{{ videoInfos[video.video_id].description }}
              </CardItem>
              <CardItem
                as="p"
                translate-z="70"
                class="text-sm text-neutral-500 dark:text-neutral-300"
              >
                视频时长：{{ videoInfos[video.video_id].duration }} 秒
              </CardItem>
              <CardItem
                as="p"
                translate-z="70"
                class="text-sm text-neutral-500 dark:text-neutral-300"
              >
                视频总评论数：{{ videoInfos[video.video_id].stats.comment_count }}
              </CardItem>
              <CardItem
                as="p"
                translate-z="70"
                class="text-sm text-neutral-500 dark:text-neutral-300"
              >
                视频点赞数：{{ videoInfos[video.video_id].stats.like_count }}
              </CardItem>
              <CardItem
                as="p"
                translate-z="70"
                class="text-sm text-neutral-500 dark:text-neutral-300"
              >
                视频收藏数：{{ videoInfos[video.video_id].stats.favorite_count }}
              </CardItem>
              <CardItem
                as="p"
                translate-z="70"
                class="text-sm text-neutral-500 dark:text-neutral-300"
              >
                视频分享数：{{ videoInfos[video.video_id].stats.share_count }}
              </CardItem>
            </div>
            <div class="mt-20 flex items-center justify-between">
              <CardItem
                :translate-z="120"
                as="a"
                :href="`https://www.douyin.com/video/${video.video_id}`"
                target="_blank"
                class="rounded-xl px-4 py-2 text-xs font-normal dark:text-white"
              >
                查看原视频 →
              </CardItem>
              <CardItem
                :translate-z="120"
                as="button"
                class="rounded-xl bg-black px-4 py-2 text-xs font-bold text-white dark:bg-white dark:text-black"
                @click="openModalWithVideo(video)"
              >
                导入与可视化
              </CardItem>
            </div>
          </CardBody>
        </CardContainer>
      </div>
      <div
        v-else
        class="no-videos-message"
        style="color: grey; font-size: 1.5rem; text-align: center; margin-top: 2rem"
      >
        请先导入视频id
      </div>
    </div>
  </div>

  <!-- 导入子组件页面（弹窗） -->
  <transition name="fade">
    <ImportVideoModal v-if="showImportModal" :videoId="searchQuery" @close="handleModalClose" />
  </transition>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { getAllStoreVideos, getVideoInfo } from '@/utils/api'
import CardContainer from '@/components/CardContainer.vue'
import CardBody from '@/components/CardBody.vue'
import CardItem from '@/components/CardItem.vue'
import ImportVideoModal from '@/components/ImportVideoModal.vue'

interface Video {
  video_id: string
  comment_count: number
}

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

const videos = ref<Video[]>([])
const activeIndex = ref(0)
const carouselRef = ref<HTMLElement | null>(null)
const videoInfos = ref<Record<string, VideoInfo>>({})
const loadedVideos = ref<Record<string, boolean>>({})

const currentCardInput = ref(1)
const searchQuery = ref('')
const dropdownOpen = ref(false)
const showImportModal = ref(false)

const filteredVideos = computed(() => {
  if (!searchQuery.value) return []
  return videos.value.filter((video) => video.video_id.includes(searchQuery.value))
})

const jumpToVideo = (video: Video): void => {
  const index = videos.value.findIndex((v) => v.video_id === video.video_id)
  if (index !== -1) {
    activeIndex.value = index
    searchQuery.value = ''
    dropdownOpen.value = false
  }
}

const onBlurDropdown = (): void => {
  setTimeout(() => {
    dropdownOpen.value = false
  }, 200)
}

const fetchVideos = async (): Promise<void> => {
  try {
    const res = await getAllStoreVideos()
    videos.value = res.video_data
  } catch (error) {
    console.error('获取视频列表失败：', error)
  }
}

const handleWheel = (event: WheelEvent): void => {
  event.preventDefault()
  if (event.deltaY > 0 && activeIndex.value < videos.value.length - 1) {
    activeIndex.value++
  } else if (event.deltaY < 0 && activeIndex.value > 0) {
    activeIndex.value--
  }
}

const scrollLeft = (): void => {
  if (activeIndex.value > 0) {
    activeIndex.value--
  }
}
const scrollRight = (): void => {
  if (activeIndex.value < videos.value.length - 1) {
    activeIndex.value++
  }
}

const cardStyle = (index: number): Record<string, string | number> => {
  const offset = index - activeIndex.value
  const isMobile = window.innerWidth < 640
  const translateX = offset * (isMobile ? 100 : 120)
  const rotateY = offset * (isMobile ? -15 : -30)
  const opacity = Math.abs(offset) > 2 ? 0 : 1
  return {
    transform: `perspective(1000px) translateX(${translateX}%) rotateY(${rotateY}deg)`,
    transformStyle: 'preserve-3d',
    transition: 'transform 0.5s ease',
    opacity,
    pointerEvents: index === activeIndex.value ? 'auto' : 'none',
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
    margin: 'auto',
  }
}

const loadVideoInfo = async (videoId: string): Promise<void> => {
  try {
    const info: VideoInfo = await getVideoInfo(videoId)
    videoInfos.value[videoId] = info
  } catch (error) {
    console.error(`获取视频 ${videoId} 详情失败：`, error)
  }
}

watch([videos, activeIndex], ([videosVal, activeIndexVal]) => {
  currentCardInput.value = activeIndexVal + 1
  const start = Math.max(0, activeIndexVal - 2)
  const end = Math.min(videosVal.length, activeIndexVal + 3)
  for (let i = start; i < end; i++) {
    const video = videosVal[i]
    if (!loadedVideos.value[video.video_id]) {
      loadVideoInfo(video.video_id)
      loadedVideos.value[video.video_id] = true
    }
  }
})

const jumpToCard = (): void => {
  let target = currentCardInput.value - 1
  if (target < 0) target = 0
  if (target >= videos.value.length) target = videos.value.length - 1
  activeIndex.value = target
}

const handleImport = (): void => {
  const exists = videos.value.some((video) => video.video_id === searchQuery.value)
  if (exists) {
    const video = videos.value.find((v) => v.video_id === searchQuery.value)!
    jumpToVideo(video)
  } else {
    showImportModal.value = true
  }
}

const openModalWithVideo = (video: Video): void => {
  searchQuery.value = video.video_id
  showImportModal.value = true
}

const handleModalClose = (): void => {
  showImportModal.value = false
}

const progressPercentage = computed((): number => {
  if (videos.value.length === 0) return 0
  return Math.round(((activeIndex.value + 1) / videos.value.length) * 100)
})

// 定时器管理：用于调用 fetchVideos
const fetchInterval = ref<number | null>(null)
const startFetchInterval = () => {
  if (fetchInterval.value === null) {
    fetchInterval.value = window.setInterval(fetchVideos, 5000)
  }
}
const stopFetchInterval = () => {
  if (fetchInterval.value !== null) {
    clearInterval(fetchInterval.value)
    fetchInterval.value = null
  }
}

onMounted((): void => {
  fetchVideos()
  carouselRef.value?.focus()
  startFetchInterval()
})

// 监听弹窗状态：子组件打开时暂停更新，关闭时立即更新一次并恢复定时器
watch(showImportModal, (newVal) => {
  if (newVal) {
    stopFetchInterval()
  } else {
    fetchVideos()
    startFetchInterval()
  }
})

onBeforeUnmount((): void => {
  stopFetchInterval()
  carouselRef.value?.removeEventListener('wheel', handleWheel)
})
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

<style scoped>
.carousel {
  perspective: 1000px;
  position: relative;
  padding-bottom: 2rem;
}

.carousel:focus {
  outline: none;
}

.cards-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}

.arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background-color: transparent;
  border: none;
  padding: 1rem;
  cursor: pointer;
  font-size: 2.5rem;
  opacity: 0.7;
  z-index: 10;
}

.arrow:hover {
  opacity: 1;
}

.arrow.left {
  left: 20px;
}

.arrow.right {
  right: 20px;
}

.progress-container {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.progress-info {
  font-size: 1rem;
  color: #333;
}

.card-input {
  width: 3rem;
  text-align: center;
  margin: 0 0.5rem;
}

.radial-progress {
  --size: 80px;
  width: var(--size);
  height: var(--size);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: #111;
}

.skeleton {
  background-color: #e0e0e0;
  animation: pulse 1.5s infinite;
  border-radius: 4px;
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
  100% {
    opacity: 1;
  }
}

@media (max-width: 640px) {
  .carousel {
    padding: 1rem;
  }
  .arrow {
    font-size: 2rem;
    padding: 0.5rem;
  }
  .card-input {
    width: 2.5rem;
    font-size: 0.9rem;
  }
  .radial-progress {
    --size: 60px;
    font-size: 0.8rem;
  }
  .header-container {
    flex-direction: column;
  }
}
</style>
