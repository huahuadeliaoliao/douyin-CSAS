<template>
  <div>
    <!-- 加载状态：显示旋转的 loading 指示器 -->
    <div v-if="loading" class="flex justify-center items-center py-4">
      <svg class="animate-spin h-6 w-6 text-gray-500" viewBox="0 0 24 24">
        <circle
          class="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          stroke-width="4"
        ></circle>
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        ></path>
      </svg>
    </div>

    <!-- 数据加载完毕且有数据时显示条形图，利用 transition-group 增加动画效果 -->
    <transition-group name="fade" tag="div" class="space-y-4" v-if="!loading && hasData">
      <div v-for="(score, emotion) in emotionData" :key="emotion" class="flex flex-col">
        <div class="flex items-center justify-between mb-1">
          <div class="flex items-center space-x-2">
            <span class="text-sm" :class="{ 'text-gray-900': !isDark, 'text-white': isDark }">
              {{ emotionMap[emotion]?.icon }}
            </span>
            <span
              class="text-sm font-medium"
              :class="{ 'text-gray-900': !isDark, 'text-white': isDark }"
            >
              {{ emotion }}
            </span>
          </div>
          <span
            class="text-sm font-medium"
            :class="{ 'text-gray-900': !isDark, 'text-white': isDark }"
          >
            {{ (score * 100).toFixed(1) }}%
          </span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-4 dark:bg-gray-700">
          <div
            class="h-4 rounded-full transition-all duration-500"
            :class="emotionMap[emotion]?.color"
            :style="{ width: score * 100 + '%' }"
          ></div>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useColorMode } from '@vueuse/core'

// 定义 props 类型
interface Props {
  emotionData: Record<string, number>
  loading: boolean
}

const props = defineProps<Props>()

// 判断是否有数据
const hasData = computed(() => Object.keys(props.emotionData).length > 0)

// 定义情绪对应的颜色和图标
const emotionMap: Record<string, { color: string; icon: string }> = {
  厌恶: { color: 'bg-green-500', icon: '🤮' },
  喜好: { color: 'bg-pink-500', icon: '😍' },
  恐惧: { color: 'bg-purple-500', icon: '😱' },
  悲伤: { color: 'bg-blue-500', icon: '😢' },
  惊讶: { color: 'bg-yellow-500', icon: '😲' },
  愤怒: { color: 'bg-red-500', icon: '😡' },
  高兴: { color: 'bg-teal-500', icon: '😊' },
}

// 判断当前是否为暗黑模式
const isDark = computed(() => useColorMode().value === 'dark')
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
