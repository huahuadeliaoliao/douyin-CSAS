<template>
  <div class="h-screen overflow-hidden flex flex-col">
    <!-- 全局导航栏 -->
    <div class="navbar relative overflow-hidden">
      <!-- 动态水墨背景层 -->
      <div class="absolute inset-0 z-0 ink-wash-bg"></div>

      <div class="relative z-10 flex-1 flex items-center gap-4">
        <a class="btn btn-ghost text-xl">Emotique</a>
        <router-link :to="{ name: 'dialogpage' }" class="btn glass">Dialog</router-link>
        <router-link :to="{ name: 'dashboard' }" class="btn glass">Dashboard</router-link>
      </div>
      <div class="relative z-10 flex-none gap-2">
        <!-- 点击头像触发打开对话框 -->
        <div tabindex="0" role="button" class="btn btn-ghost btn-circle avatar" @click="openModal">
          <div class="w-10 rounded-full">
            <img alt="Emotique" src="/emotique.webp" />
          </div>
        </div>
      </div>
    </div>

    <!-- 页面主体 -->
    <div class="flex-1 overflow-auto">
      <router-view />
    </div>

    <!-- 对话框部分 -->
    <dialog ref="myModal" class="modal">
      <div class="modal-box relative">
        <form method="dialog">
          <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
        </form>
        <h3 class="text-lg font-bold">设置 Cookie</h3>
        <p class="py-4">获取抖音账号的Cookie后填入到下方输入框</p>
        <!-- 使用 v-model 绑定 cookie 变量 -->
        <input
          type="text"
          placeholder="填入Cookie"
          class="input input-bordered w-full"
          v-model="cookie"
        />
        <div class="flex justify-end mt-4">
          <!-- 点击导入按钮时调用 importCookie 方法 -->
          <button class="btn btn-neutral" @click="importCookie">导入</button>
        </div>
      </div>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { login } from '@/utils/api'
import { useRouter } from 'vue-router'

const router = useRouter()

// 定义对话框引用和 cookie 变量
const myModal = ref<HTMLDialogElement | null>(null)
const cookie = ref('')

// 定义打开对话框的函数
const openModal = () => {
  if (myModal.value) {
    myModal.value.showModal()
  }
}

// 定义导入方法，在点击导入后调用 login 方法
const importCookie = async () => {
  try {
    await login({ cookie: cookie.value })
    // 登录成功后关闭对话框
    myModal.value?.close()
    router.push({ name: 'dashboard' })
  } catch (error) {}
}
</script>

<style scoped>
/* 定义水墨流动的动画 */
@keyframes inkFlow {
  0% {
    transform: scale(1) translate(0, 0);
  }
  50% {
    transform: scale(1.05) translate(-3%, -3%);
  }
  100% {
    transform: scale(1) translate(0, 0);
  }
}

/* 背景层样式 */
.ink-wash-bg {
  background: url('/ink.webp') no-repeat center/cover;
  opacity: 0.25;
  filter: blur(15px);
  animation: inkFlow 3s ease-in-out infinite;
}
</style>
