import { api } from "./api";

// 页面顺带读取其他中心的记录做下拉选项时用：账号没有那个中心的菜单时后端返回 403，
// 这里按空列表处理，不能让整页加载失败、也不弹“没有该业务模块的菜单权限”。其他错误照常抛出。
export async function optionalRecords(params: Record<string, unknown>): Promise<{ data: any }> {
  try {
    return await api.get("/records", { params });
  } catch (error: any) {
    if (error?.response?.status === 403) return { data: { items: [], total: 0 } };
    throw error;
  }
}
