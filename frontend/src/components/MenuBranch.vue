<script setup lang="ts">
defineOptions({ name: "MenuBranch" });

type MenuNode = {
  MenuCode: string;
  MenuName: string;
  LinkUrl: string;
  Children: MenuNode[];
};

const props = defineProps<{
  menu: MenuNode;
  openCodes: string[];
  activeMenuCode: string;
}>();

const emit = defineEmits<{
  toggle: [menu: MenuNode];
  activate: [menu: MenuNode];
}>();

function hasChildren(menu: MenuNode) {
  return menu.Children.length > 0;
}
</script>

<template>
  <div class="menu-branch" :class="{ active: activeMenuCode === menu.MenuCode }">
    <button class="menu-item" type="button" @click="hasChildren(menu) ? emit('toggle', menu) : emit('activate', menu)">
      <span class="menu-icon">{{ hasChildren(menu) ? '▣' : '○' }}</span>
      <span class="menu-name">{{ menu.MenuName }}</span>
      <span v-if="hasChildren(menu)" class="menu-arrow">{{ openCodes.includes(menu.MenuCode) ? '⌄' : '›' }}</span>
    </button>
    <div v-if="hasChildren(menu) && openCodes.includes(menu.MenuCode)" class="menu-children">
      <MenuBranch
        v-for="child in menu.Children"
        :key="child.MenuCode"
        :menu="child"
        :open-codes="openCodes"
        :active-menu-code="activeMenuCode"
        @toggle="emit('toggle', $event)"
        @activate="emit('activate', $event)"
      />
    </div>
  </div>
</template>
