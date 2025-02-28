<template>
  <div ref="container" :class="props.class">
    <Motion
      v-for="(child, index) in children"
      :key="index"
      ref="childElements"
      as="div"
      :initial="getInitial()"
      :in-view="getAnimate()"
      :transition="{
        duration: props.duration,
        easing: 'easeInOut',
        delay: props.delay * index,
      }"
    >
      <component :is="child" />
    </Motion>
  </div>
</template>

<script setup lang="ts">
import { Motion } from 'motion-v'
import { onMounted, ref, watchEffect, useSlots, type VNode } from 'vue'

interface Props {
  duration?: number
  delay?: number
  blur?: string
  yOffset?: number
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  duration: 1,
  delay: 2,
  blur: '20px',
  yOffset: 20,
})

// 显式声明 slots 类型
const slots = useSlots() as { default?: () => VNode[] }
const container = ref(null)
const childElements = ref([])
const children = ref<VNode[]>([])

onMounted(() => {
  // 响应式捕获默认插槽的所有内容
  watchEffect(() => {
    children.value = slots.default ? slots.default() : []
  })
})

function getInitial() {
  return {
    opacity: 0,
    filter: `blur(${props.blur})`,
    y: props.yOffset,
  }
}

function getAnimate() {
  return {
    opacity: 1,
    filter: 'blur(0px)',
    y: 0,
  }
}
</script>
