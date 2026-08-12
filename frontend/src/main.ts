import { createApp } from "vue";
import App from "./App.vue";
import MenuBranch from "./components/MenuBranch.vue";
import "./styles.css";

createApp(App).component("MenuBranch", MenuBranch).mount("#app");
