<script setup lang="ts">
import { onMounted, ref, watch } from "vue";

type OfficialDocument = {
  Basic: {
    OfficialDocumentNo: string | null;
    BusinessOwnerName: string | null;
    ApplicationDate: string | null;
    OfficialDocumentStatusName: string;
    OfficialDocumentTypeName: string;
    SealTypeName: string;
    CaseNo: string | null;
    ContractNo: string | null;
    CustomerName: string | null;
    AuditorName: string | null;
    AuditTime: string | null;
    AuditRemark: string | null;
  };
  OfficialDocumentFileList: unknown[];
};

const rows = ref<OfficialDocument[]>([]);
const total = ref(0);
const loading = ref(true);
const requestNo = ref("");
const applicant = ref("");
const caseNo = ref("");
const contractNo = ref("");
const customerName = ref("");
const status = ref("");
const documentType = ref("");
const fileName = ref("");
const props = defineProps<{ statusFilter: number | null }>();

async function search() {
  loading.value = true;
  const params = new URLSearchParams({ page_no: "1", page_size: "15" });
  const filters: Record<string, string> = {
    official_document_no: requestNo.value,
    business_owner: applicant.value,
    case_no: caseNo.value,
    contract_no: contractNo.value,
    customer_name: customerName.value,
    official_document_status: status.value,
    official_document_type: documentType.value,
    file_name: fileName.value,
  };
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value);
  const response = await fetch(`/api/v1/legacy/official-documents?${params}`);
  const payload = await response.json();
  rows.value = payload.Data.OfficialDocuments;
  total.value = payload.Data.TotalItemCount;
  loading.value = false;
}

function date(value: string | null) {
  return value ? value.slice(0, 10) : "";
}

onMounted(search);
watch(() => props.statusFilter, (value) => {
  status.value = value === null ? "" : String(value);
  search();
}, { immediate: true });
</script>

<template>
  <section class="official-document-page">
    <h5>用印申请列表</h5>
    <form class="legacy-filter" @submit.prevent="search">
      <label>申请编号：<input v-model="requestNo" /></label>
      <label>申请人：<input v-model="applicant" /></label>
      <label>申请日期：<span class="date-range"><input type="date" /><i>-</i><input type="date" /></span></label>
      <label>案件编号：<input v-model="caseNo" /></label>
      <label>合同编号：<input v-model="contractNo" /></label>
      <label>客户名称：<input v-model="customerName" /></label>
      <label>用印状态：<select v-model="status"><option value="">请选择</option><option value="10">待审核</option><option value="20">已审待用印</option><option value="30">审核拒绝</option><option value="40">已撤回</option><option value="60">已用印</option></select></label>
      <label>用印类型：<select v-model="documentType"><option value="">请选择</option><option value="10">合同用印</option><option value="20">案件用印</option><option value="30">行政用印</option></select></label>
      <label>文件名称：<input v-model="fileName" /></label>
      <div class="filter-action"><button type="submit">查询</button></div>
    </form>
    <div class="legacy-list-tools"><button type="button" disabled>申请用印</button><button type="button" disabled>修改</button><button type="button" disabled>撤回</button></div>
    <table class="legacy-grid">
      <thead><tr><th><input type="checkbox" disabled /></th><th>编号</th><th>申请人</th><th>申请时间</th><th>用印状态</th><th>用印类型</th><th>印章类型</th><th>文件数</th><th>案号</th><th>合同号</th><th>客户</th><th>审核人</th><th>审核时间</th><th>审核意见</th></tr></thead>
      <tbody v-if="rows.length"><tr v-for="row in rows" :key="row.Basic.OfficialDocumentNo || ''"><td><input type="checkbox" /></td><td>{{ row.Basic.OfficialDocumentNo }}</td><td>{{ row.Basic.BusinessOwnerName }}</td><td>{{ date(row.Basic.ApplicationDate) }}</td><td>{{ row.Basic.OfficialDocumentStatusName }}</td><td>{{ row.Basic.OfficialDocumentTypeName }}</td><td>{{ row.Basic.SealTypeName }}</td><td>{{ row.OfficialDocumentFileList.length }}</td><td>{{ row.Basic.CaseNo }}</td><td>{{ row.Basic.ContractNo }}</td><td>{{ row.Basic.CustomerName }}</td><td>{{ row.Basic.AuditorName }}</td><td>{{ date(row.Basic.AuditTime) }}</td><td>{{ row.Basic.AuditRemark }}</td></tr></tbody>
    </table>
    <div v-if="loading" class="legacy-empty">正在查询...</div>
    <div v-else-if="!rows.length" class="legacy-empty">没有查询到符合条件的记录 。</div>
    <footer v-else class="legacy-pagination">共 {{ total }} 条</footer>
  </section>
</template>
