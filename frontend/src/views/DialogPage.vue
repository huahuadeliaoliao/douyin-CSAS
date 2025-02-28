<template>
  <div class="relative h-full overflow-hidden flex flex-col">
    <!-- 粒子背景 -->
    <ParticlesBg
      class="absolute inset-0 h-full w-full"
      :quantity="100"
      :ease="100"
      :color="isDark ? '#FFF' : '#000'"
      :staticity="10"
      refresh
    />

    <div
      class="relative flex flex-col items-center px-4 py-20"
      :class="{ 'min-h-[calc(100vh-4rem-10rem)] justify-center': !hasSubmitted }"
    >
      <BlurReveal :delay="0.2" :duration="0.75">
        <h2 class="mb-10 text-center text-xl text-black sm:mb-20 sm:text-5xl dark:text-white">
          字有千重意，屏开七情谱
        </h2>

        <p class="mb-4 text-center text-gray-500 text-sm">
          请输入您的语句，我将解读其中蕴含的情绪。
        </p>
      </BlurReveal>
      <VanishingInput v-model="text" :placeholders="placeholders" @submit="handleSubmit" />

      <!-- EmotionChart：仅在 hasSubmitted 为 true 时显示 -->
      <div class="mt-24 w-full max-w-md" v-if="hasSubmitted">
        <EmotionChart :emotionData="emotionData" :loading="loading" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useColorMode } from '@vueuse/core'
import VanishingInput from '@/components/VanishingInput.vue'
import BlurReveal from '@/components/BlurReveal.vue'
import ParticlesBg from '@/components/ParticlesBg.vue'
import EmotionChart from '@/components/EmotionChart.vue'
import { inferText } from '@/utils/api'

// 定义接口返回的数据结构
interface EmotionAPIResponse {
  result: Record<string, number>
}

const placeholders: string[] = [
  '我今天很开心！',
  '这个应用很好用，我会向朋友推荐',
  '你的态度让我觉得很不舒服',
  '我需要跟你说声抱歉',
  '如果不是这个问题，现在就已经成功了！',
  '此去一别，难得一见',
  '情随字动，心语成诗。',
]

const text = ref<string>('')
// 保证 emotionData 始终为一个对象
const emotionData = ref<Record<string, number>>({})
const loading = ref<boolean>(false)
const hasSubmitted = ref<boolean>(false)

async function handleSubmit(submittedText: string): Promise<void> {
  hasSubmitted.value = true
  loading.value = true
  try {
    const response: EmotionAPIResponse = await inferText(submittedText)
    // 如果 response.result 为 undefined，则赋值为空对象
    emotionData.value = response.result ?? {}
  } catch (error) {
    // 出错时同样确保 emotionData 为对象
    emotionData.value = {}
  } finally {
    loading.value = false
  }
}

const isDark = computed(() => useColorMode().value === 'dark')
</script>
