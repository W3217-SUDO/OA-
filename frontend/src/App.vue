<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

type MenuNode = {
  MenuId: number;
  MenuCode: string;
  MenuName: string;
  ParentMenuId: string;
  OrderId: number;
  ImageUrl: string;
  LinkUrl: string;
  MenuTypeId: number;
  IsActived: string;
  Children: MenuNode[];
};

const menus = ref<MenuNode[]>([]);
const search = ref("");
const activeMenuCode = ref("");
const openCodes = ref<string[]>([]);
const loading = ref(true);
const error = ref("");

const filteredMenus = computed(() => {
  const keyword = search.value.trim().toLowerCase();
  if (!keyword) return menus.value;
  const filter = (node: MenuNode): MenuNode | null => {
    const children = node.Children.map(filter).filter((item): item is MenuNode => item !== null);
    return node.MenuName.toLowerCase().includes(keyword) || children.length ? { ...node, Children: children } : null;
  };
  return menus.value.map(filter).filter((item): item is MenuNode => item !== null);
});

function toggleMenu(menu: MenuNode) {
  if (menu.Children.length === 0) {
    activeMenuCode.value = menu.MenuCode;
    return;
  }
  openCodes.value = openCodes.value.includes(menu.MenuCode)
    ? openCodes.value.filter((code) => code !== menu.MenuCode)
    : [...openCodes.value, menu.MenuCode];
}

function activate(menu: MenuNode) {
  activeMenuCode.value = menu.MenuCode;
}

onMounted(async () => {
  try {
    const response = await fetch("/api/v1/legacy/authorization/staff/1/menu-tree");
    if (!response.ok) throw new Error(`菜单加载失败: ${response.status}`);
    menus.value = await response.json();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "菜单加载失败";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <main class="legacy-shell">
    <header class="legacy-header">
      <div class="legacy-brand">Sunhold</div>
      <button class="header-icon" aria-label="切换菜单">☰</button>
      <div class="header-search"><input placeholder="搜索菜单、案号、法院号、案件名、客户名" /></div>
      <div class="header-search compact"><input placeholder="案号、法院号、案件名、客户名" /></div>
      <div class="header-actions"><span>⌂</span><span>☰ 系统导航⌄</span><span>♧</span><span>Admin 管理员⌄</span></div>
    </header>
    <aside class="legacy-sidebar">
      <div class="profile"><strong>管理员</strong><small>● 在线</small></div>
      <label class="menu-search"><input v-model="search" placeholder="搜索菜单" /><span>⌕</span></label>
      <div class="nav-caption">系统导航</div>
      <div v-if="loading" class="menu-status">正在加载菜单...</div>
      <div v-else-if="error" class="menu-status error">{{ error }}</div>
      <nav v-else class="menu-tree" aria-label="旧系统菜单">
        <MenuBranch
          v-for="menu in filteredMenus"
          :key="menu.MenuCode"
          :menu="menu"
          :open-codes="openCodes"
          :active-menu-code="activeMenuCode"
          @toggle="toggleMenu"
          @activate="activate"
        />
      </nav>
    </aside>
    <section class="legacy-workspace">
      <div class="legacy-tabs"><span class="active">控制台</span></div>
      <div class="workspace-heading"><h1>控制台</h1><span>首页 / 控制台</span></div>
      <div class="baseline-grid">
        <article><b>旧系统等价重建</b><p>菜单、字段、权限和流程均以 8091 为基准。</p></article>
        <article><b>旧库只读</b><p>FastAPI 当前只读映射旧库，不会写入历史数据。</p></article>
        <article><b>扩展能力</b><p>钉钉与智能体将用扩展表接入，不改变旧表语义。</p></article>
      </div>
    </section>
  </main>
</template>
