import { Button,Card,Form,Modal,Space,Tag,message } from "antd";
import dayjs from "dayjs";
import type { Key } from "react";
import { useEffect,useRef,useState } from "react";
import { api } from "../api";
import { buildCaseContractContext,rememberCaseContractContext } from "../caseContractPrefill";
import { confirmOperation } from "../components/common/confirmOperation";
import "../contract-center.css";
import { openContractCustomerCreation } from "../contractCenterCustomerNavigation";
import {
CONTRACT_CUSTOMER_ROUTE_SOURCE_KEY,
clearContractCustomerContext,
createContractCustomerContextConsumer,
createContractNumber,
type LinkedCustomerContext,
} from "../contractCreateContext";
import { buildContractDetailRoute,type ContractDetailNavigationContext } from "../contractDetailNavigation";
import { readContractListPagination,saveContractListPagination } from "../contractListPagination.mjs";
import { saveContractListQuery } from "../contractListQuery";
import { createContractMutationGate } from "../contractMutationGate.mjs";
import {
CONTRACT_OBJECT_DEFAULT_PAGE_SIZE,
paginateContractObjectRows
} from "../contractObjectListPolicy.mjs";
import {
contractObjectActionPolicy,
normalizeIncomingPaymentForContract,
normalizeInvoiceObject,
normalizePaidObject
} from "../contractObjectPresentation.mjs";
import { buildContractPaymentNavigation } from "../contractPaymentNavigation";
import { buildChinesePersonOptions,displayChinesePersonName,displayChinesePersonNames } from "../contractPeoplePresentation.mjs";
import { displayContractStatus } from "../contractStatusPresentation.mjs";
import * as contractWorkflowPolicyModule from "../contractWorkflowPolicy.mjs";
import {
buildContractDraftDefaults,
buildContractEventsRequest,
buildContractListRequestParams,
canAccessContractView,
contractAuditActionPolicy,
contractListActionPolicy,
contractListViewConfig,
contractSecondaryActionPolicy,
createContractEventRequestTracker,
createContractEventSubmitGate,
createContractListRequestGuard,
extractContractErrorMessage,
normalizeContractActionResponse,
normalizeContractQuery,
resolveContractCustomerSelection
} from "../contractWorkflowPolicy.mjs";
import { INVESTIGATION_REGION_GROUPS } from "../investigationRegionOptions.mjs";
import {
CONTRACT_CREATE_STEP_TITLES,
WIZARD_STORAGE_KEY,
consumeContractDetailReturnView,
initialProfile,
moneyKeys,
readContractQuery
} from "./constants";
import { ContractWizardContent } from "./ContractCreateWizard";
import { ContractDetailView } from "./ContractDetailView";
import { ContractInvestigationWizard } from "./ContractInvestigationWizard";
import { ContractList } from "./ContractList";
import {
ApproverSettingsModal,
AttachmentPreviewModal,
ContractChangeHistoryModal,
ContractChangeModal,
ContractEventModal,
ContractInvoiceModal,
ContractObjectEditModal,
ContractObjectLogModal,
ContractPaymentModal,
ContractReviewModal,
ContractSubmitModal,
InvestigationRegionPickerModal,
PaymentTypeCreateModal,
} from "./ContractModals";
import { useContractAttachmentPreview } from "./hooks/useContractAttachmentPreview";
import { createContractDocumentsActions } from "./services/documentsActions";
import { createContractFinanceActions } from "./services/financeActions";
import { createContractQueriesActions } from "./services/queriesActions";
import { createContractWorkflowActions } from "./services/workflowActions";
import type {
ApproverSetting,Attachment,
Change,
Contract,
ContractArchiveSubject,
ContractArchiveSummary,
ContractEvent,
ContractPaymentCandidate,
ContractWorkflowCapabilities,CustomerRef,DirectoryUser,
HistoryEvent,
LegacyHistoricalAttachment,
PaymentTypeOption,
Profile,
SealAsset,
Step
} from "./types";
const contractWorkflowActionPolicy = (contractWorkflowPolicyModule as unknown as {
  contractWorkflowActionPolicy: (profile: Profile, contract: Contract | Record<string, unknown>, options?: Record<string, unknown>) => ContractWorkflowCapabilities;
}).contractWorkflowActionPolicy;
export default function ContractCenterPage({
  initialView,
  onNavigate,
  detailTarget,
  onDetailTargetHandled,
}: {
  initialView: string;
  onNavigate?: (key: string) => void;
  detailTarget?: ContractDetailNavigationContext | null;
  onDetailTargetHandled?: () => void;
}) {
  const customerContextConsumerRef = useRef(createContractCustomerContextConsumer(sessionStorage));
  const newContractRouteInitializedRef = useRef(false);
  const isContractDetailView = initialView.startsWith("contract-detail-") || initialView.startsWith("contract-preview-");
  const isContractInvestigationView = initialView.startsWith("contract-investigation-");
  const contractDetailRouteMatch = initialView.match(/^contract-detail-(\d+)-(.+)$/);
  const contractInvestigationRouteMatch = initialView.match(/^contract-investigation-(\d+)-(.+)$/);
  const contractPreviewRouteMatch = initialView.match(/^contract-preview-(.+)$/);
  const contractDetailRouteTarget: ContractDetailNavigationContext | null = contractDetailRouteMatch
    ? { id: Number(contractDetailRouteMatch[1]), serial_no: decodeURIComponent(contractDetailRouteMatch[2]), at: Date.now() }
    : contractPreviewRouteMatch
      ? { serial_no: decodeURIComponent(contractPreviewRouteMatch[1]), at: Date.now() }
      : null;
  const contractInvestigationRouteTarget: ContractDetailNavigationContext | null = contractInvestigationRouteMatch
    ? { id: Number(contractInvestigationRouteMatch[1]), serial_no: decodeURIComponent(contractInvestigationRouteMatch[2]), at: Date.now() }
    : null;
  const [allRows, setAllRows] = useState<Contract[]>([]),
    [listTotal, setListTotal] = useState(0),
    [loading, setLoading] = useState(false),
    [open, setOpen] = useState(initialView === "contract-new"),
    [editing, setEditing] = useState<Contract | null>(null),
    [wizardDraft, setWizardDraft] = useState<Contract | null>(null),
    [wizardStep, setWizardStep] = useState(0),
    [submitting, setSubmitting] = useState<Contract | null>(null),
    [reviewing, setReviewing] = useState<Contract | null>(null),
    [steps, setSteps] = useState<Step[]>([]),
    [reviewCurrentStep, setReviewCurrentStep] = useState<Step | null>(null),
    [changing, setChanging] = useState<Contract | null>(null),
    [changeHistory, setChangeHistory] = useState<Contract | null>(null),
    [investigating, setInvestigating] = useState<Contract | null>(null),
    [investigationWizardStep, setInvestigationWizardStep] = useState(0),
    [investigationDraftValues, setInvestigationDraftValues] = useState<Record<string, any> | null>(null),
    [createdInvestigation, setCreatedInvestigation] = useState<{ id: number; serial_no: string; title: string } | null>(null),
    [investigationSupervisor, setInvestigationSupervisor] = useState<{ username: string; display_name: string } | null>(null),
    [investigationSubmitting, setInvestigationSubmitting] = useState(false),
    [paymentTarget, setPaymentTarget] = useState<Contract | null>(null),
    [invoiceTarget, setInvoiceTarget] = useState<Contract | null>(null),
    [viewing, setViewing] = useState<Contract | null>(null),
    [changes, setChanges] = useState<Change[]>([]),
    [contractEvents, setContractEvents] = useState<ContractEvent[]>([]),
    [contractWorkflowEvents, setContractWorkflowEvents] = useState<ContractEvent[]>([]),
    [contractEventPage, setContractEventPage] = useState(1),
    [contractEventPageSize, setContractEventPageSize] = useState(15),
    [contractEventTotal, setContractEventTotal] = useState(0),
    [contractEventKeyword, setContractEventKeyword] = useState(""),
    [contractEventsLoading, setContractEventsLoading] = useState(false),
    [contractEventsError, setContractEventsError] = useState<string | null>(null),
    [eventTarget, setEventTarget] = useState<Contract | null>(null),
    [eventSaving, setEventSaving] = useState(false);
  const [submitSaving, setSubmitSaving] = useState(false);
  const [paymentSaving, setPaymentSaving] = useState(false);
  const [invoiceSaving, setInvoiceSaving] = useState(false);
  const [directory, setDirectory] = useState<DirectoryUser[]>([]);
  const personName = (value: unknown) => displayChinesePersonName(value, directory);
  const peopleNames = (value: unknown) => displayChinesePersonNames(value, directory);
  const [approverSettingsOpen, setApproverSettingsOpen] = useState(false);
  const [approverSettings, setApproverSettings] = useState<ApproverSetting[]>([]);
  const [selectedApproverUsernames, setSelectedApproverUsernames] = useState<string[]>([]);
  const [approverSettingsTargetUsername, setApproverSettingsTargetUsername] = useState("");
  const [approverSettingsLoading, setApproverSettingsLoading] = useState(false);
  const [approverSettingsSaving, setApproverSettingsSaving] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [viewingAttachments, setViewingAttachments] = useState<Attachment[]>([]);
  const [legacyHistoricalAttachments, setLegacyHistoricalAttachments] = useState<LegacyHistoricalAttachment[]>([]);
  const [legacyHistoricalAttachmentsLoading, setLegacyHistoricalAttachmentsLoading] = useState(false);
  const [legacyHistoricalAttachmentsError, setLegacyHistoricalAttachmentsError] = useState<string | null>(null);
  const [detailActiveTab, setDetailActiveTab] = useState("objects");
  const [selectedAttachmentKeys, setSelectedAttachmentKeys] = useState<Key[]>([]);
  const [attachmentBatchSaving, setAttachmentBatchSaving] = useState(false);
  const [detailReceipts, setDetailReceipts] = useState<any[]>([]);
  const [detailInvoices, setDetailInvoices] = useState<Contract[]>([]);
  const [detailPayments, setDetailPayments] = useState<Contract[]>([]);
  const [detailApprovals, setDetailApprovals] = useState<Step[]>([]);
  const [detailApprovalsError, setDetailApprovalsError] = useState<string | null>(null);
  const [archiveSummary, setArchiveSummary] = useState<ContractArchiveSummary | null>(null);
  const [archiveSubjects, setArchiveSubjects] = useState<ContractArchiveSubject[]>([]);
  const [archiveSubjectsLoading, setArchiveSubjectsLoading] = useState(false);
  const [archiveClosureSaving, setArchiveClosureSaving] = useState(false);
  const [selectedArchiveObjectKeys, setSelectedArchiveObjectKeys] = useState<Key[]>([]);
  const [archiveClosureComment, setArchiveClosureComment] = useState("");
  type ContractObjectRow = {id:number;case_record_id:number;case_no:string;case_title:string;case_type:string;case_phase:string;fee_type:string;amount:number;customer_manager:string;remark:string;logs:Array<{id:number;action:string;before:Record<string,unknown>;after:Record<string,unknown>;operator:string;created_at:string}>};
  const [contractObjects, setContractObjects] = useState<ContractObjectRow[]>([]);
  const [objectPage, setObjectPage] = useState<number>(1);
  const [objectPageSize, setObjectPageSize] = useState<number>(CONTRACT_OBJECT_DEFAULT_PAGE_SIZE);
  const [paymentCandidates, setPaymentCandidates] = useState<ContractPaymentCandidate[]>([]);
  const [paymentTypes, setPaymentTypes] = useState<PaymentTypeOption[]>([]);
  const [paymentTypeSearch, setPaymentTypeSearch] = useState("");
  const [paymentTypeCreateOpen, setPaymentTypeCreateOpen] = useState(false);
  const [paymentTypeCreating, setPaymentTypeCreating] = useState(false);
  const [selectedPaymentObjectKeys, setSelectedPaymentObjectKeys] = useState<Key[]>([]);
  const [paymentAmounts, setPaymentAmounts] = useState<Record<number, number>>({});
  const [objectEditing, setObjectEditing] = useState<{id?:number}|null>(null);
  const [objectCases, setObjectCases] = useState<Array<{id:number;serial_no:string;title:string;customer:string}>>([]);
  const [objectLogTarget, setObjectLogTarget] = useState<ContractObjectRow | null>(null);
  const [viewingAttachmentsLoading, setViewingAttachmentsLoading] = useState(false);
  const [viewingAttachmentsError, setViewingAttachmentsError] = useState<string | null>(null);
  const { attachmentPreview, setAttachmentPreview, closeAttachmentPreview } = useContractAttachmentPreview();
  const viewingAttachmentRequest = useRef(0);
  const contractEventRequestTracker = useRef(createContractEventRequestTracker());
  const contractListRequestGuard = useRef(createContractListRequestGuard()).current;
  const contractEventSubmitGate = useRef(createContractEventSubmitGate());
  const contractMutationGates = useRef({
    submit: createContractMutationGate(),
    payment: createContractMutationGate(),
    invoice: createContractMutationGate(),
    attachment: createContractMutationGate(),
  });
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [sealAssets, setSealAssets] = useState<SealAsset[]>([]);
  const [customers, setCustomers] = useState<CustomerRef[]>([]);
  const [linkedCustomerContext, setLinkedCustomerContext] = useState<LinkedCustomerContext | null>(null);
  const [contractFile, setContractFile] = useState<File | null>(null);
  const [investigationRegionPickerOpen, setInvestigationRegionPickerOpen] = useState(false);
  const [selectedInvestigationRegions, setSelectedInvestigationRegions] = useState<string[]>([]);
  const [expandedInvestigationProvinces, setExpandedInvestigationProvinces] = useState<string[]>([]);
  const [changeFile, setChangeFile] = useState<File | null>(null);
  const [savingContract, setSavingContract] = useState(false);
  const [submittingWizard, setSubmittingWizard] = useState(false);
  const [profile, setProfile] = useState<Profile>(initialProfile);
  const contractCapabilities = (contract?: Contract | null, options: Record<string, unknown> = {}) =>
    contractWorkflowActionPolicy(profile, contract || {}, options);
  const denyContractAction = () => message.warning("\u5f53\u524d\u8d26\u53f7\u6ca1\u6709\u8be5\u5408\u540c\u64cd\u4f5c\u6743\u9650");
  const customerRelationQueryRef = useRef<Record<string, any> | null>(null);
  const customerRelationQueryViewRef = useRef<string | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]),
    [query, setQuery] = useState<Record<string, any>>(() => readContractQuery(initialView)),
    [listPagination, setListPagination] = useState(() => readContractListPagination(sessionStorage, initialView));
  const [form] = Form.useForm(),
    [submitForm] = Form.useForm(),
    [reviewForm] = Form.useForm(),
    [sealForm] = Form.useForm(),
    [investigationForm] = Form.useForm(),
    [paymentForm] = Form.useForm(),
    [paymentTypeCreateForm] = Form.useForm(),
    [invoiceForm] = Form.useForm(),
    [changeForm] = Form.useForm(),
    [queryForm] = Form.useForm(),
    [eventForm] = Form.useForm(),
    [objectForm] = Form.useForm();
  const investigationRegion = Form.useWatch("region", investigationForm);
  const selectedContractPaymentTypeId = Form.useWatch("payment_type_id", paymentForm);
  const selectedContractPaymentType = paymentTypes.find((item) => item.value === Number(selectedContractPaymentTypeId));
  const listViewConfig = contractListViewConfig(initialView);
  const isArchiveView = initialView === "contract-archive";
  const closeViewing = () => {
    viewingAttachmentRequest.current += 1;
    contractEventRequestTracker.current.next();
    setViewing(null);
    setViewingAttachments([]);
    setLegacyHistoricalAttachments([]);
    setLegacyHistoricalAttachmentsLoading(false);
    setLegacyHistoricalAttachmentsError(null);
    setSelectedAttachmentKeys([]);
    setAttachmentBatchSaving(false);
    setContractObjects([]);
    setObjectPage(1);
    setObjectPageSize(CONTRACT_OBJECT_DEFAULT_PAGE_SIZE);
    setObjectEditing(null);
    setObjectLogTarget(null);
    setPaymentCandidates([]);
    setPaymentTypes([]);
    setSelectedPaymentObjectKeys([]);
    setPaymentAmounts({});
    setArchiveSummary(null);
    setArchiveSubjects([]);
    setArchiveSubjectsLoading(false);
    setArchiveClosureSaving(false);
    setSelectedArchiveObjectKeys([]);
    setArchiveClosureComment("");
    setContractEvents([]);
    setContractWorkflowEvents([]);
    setContractEventPage(1);
    setContractEventPageSize(15);
    setContractEventTotal(0);
    setContractEventKeyword("");
    setContractEventsLoading(false);
    setContractEventsError(null);
    setDetailApprovalsError(null);
    setViewingAttachmentsError(null);
    setDetailReceipts([]);
    setDetailInvoices([]);
    setDetailPayments([]);
    setDetailApprovals([]);
    setViewingAttachmentsLoading(false);
    setDetailActiveTab("objects");
  };
  const { openViewing, reloadContractEvents, reloadDetailApprovals, loadArchiveSubjects, resolveContractDetailTarget, load, loadWizardContext, refreshWizard, exportCsv, exportExcel, exportContractDetailExcel, openRelatedCustomer, openRelatedCase } = createContractQueriesActions({
    get isContractDetailView() { return isContractDetailView; },
    get initialView() { return initialView; },
    get query() { return query; },
    get onNavigate() { return onNavigate; },
    get setDetailActiveTab() { return setDetailActiveTab; },
    get viewing() { return viewing; },
    get viewingAttachmentRequest() { return viewingAttachmentRequest; },
    get contractEventRequestTracker() { return contractEventRequestTracker; },
    get setViewing() { return setViewing; },
    get setViewingAttachments() { return setViewingAttachments; },
    get setSelectedAttachmentKeys() { return setSelectedAttachmentKeys; },
    get setViewingAttachmentsLoading() { return setViewingAttachmentsLoading; },
    get setViewingAttachmentsError() { return setViewingAttachmentsError; },
    get setContractEventsLoading() { return setContractEventsLoading; },
    get setContractEventsError() { return setContractEventsError; },
    get setContractEvents() { return setContractEvents; },
    get setContractWorkflowEvents() { return setContractWorkflowEvents; },
    get setContractEventPage() { return setContractEventPage; },
    get setContractEventPageSize() { return setContractEventPageSize; },
    get setContractEventTotal() { return setContractEventTotal; },
    get setContractEventKeyword() { return setContractEventKeyword; },
    get setObjectPage() { return setObjectPage; },
    get setObjectPageSize() { return setObjectPageSize; },
    get setContractObjects() { return setContractObjects; },
    get setObjectCases() { return setObjectCases; },
    get setDetailReceipts() { return setDetailReceipts; },
    get setDetailInvoices() { return setDetailInvoices; },
    get setDetailPayments() { return setDetailPayments; },
    get setDetailApprovals() { return setDetailApprovals; },
    get setDetailApprovalsError() { return setDetailApprovalsError; },
    get contractEventKeyword() { return contractEventKeyword; },
    get contractEventPageSize() { return contractEventPageSize; },
    get contractCapabilities() { return contractCapabilities; },
    get denyContractAction() { return denyContractAction; },
    get setArchiveSubjectsLoading() { return setArchiveSubjectsLoading; },
    get setArchiveSummary() { return setArchiveSummary; },
    get setArchiveSubjects() { return setArchiveSubjects; },
    get setSelectedArchiveObjectKeys() { return setSelectedArchiveObjectKeys; },
    get setArchiveClosureComment() { return setArchiveClosureComment; },
    get contractListRequestGuard() { return contractListRequestGuard; },
    get setLoading() { return setLoading; },
    get isContractInvestigationView() { return isContractInvestigationView; },
    get contractInvestigationRouteTarget() { return contractInvestigationRouteTarget; },
    get detailTarget() { return detailTarget; },
    get contractDetailRouteTarget() { return contractDetailRouteTarget; },
    get customerRelationQueryViewRef() { return customerRelationQueryViewRef; },
    get customerRelationQueryRef() { return customerRelationQueryRef; },
    get queryForm() { return queryForm; },
    get setQuery() { return setQuery; },
    get listPagination() { return listPagination; },
    get isArchiveView() { return isArchiveView; },
    get openInvestigation() { return openInvestigation; },
    get onDetailTargetHandled() { return onDetailTargetHandled; },
    get setAllRows() { return setAllRows; },
    get setListTotal() { return setListTotal; },
    get setProfile() { return setProfile; },
    get setDirectory() { return setDirectory; },
    get setSealAssets() { return setSealAssets; },
    get setCustomers() { return setCustomers; },
    get setWizardDraft() { return setWizardDraft; },
    get setSteps() { return setSteps; },
    get submitForm() { return submitForm; },
    get populateDraftForm() { return populateDraftForm; },
    get setAttachments() { return setAttachments; },
    get setHistory() { return setHistory; },
    get wizardDraft() { return wizardDraft; },
    get setWizardStep() { return setWizardStep; },
    get sealForm() { return sealForm; },
    get setContractFile() { return setContractFile; },
    get attachments() { return attachments; },
    get buildContractExportParams() { return buildContractExportParams; },
    get buildArchiveExportParams() { return buildArchiveExportParams; },
  });
  
  const { reloadViewingAttachments, loadLegacyHistoricalAttachments, downloadAttachment, previewAttachment, uploadDraftContractAttachment, uploadViewingAttachment, deleteViewingAttachment, batchDeleteViewingAttachments } = createContractDocumentsActions({
    get setViewingAttachmentsLoading() { return setViewingAttachmentsLoading; },
    get setViewingAttachmentsError() { return setViewingAttachmentsError; },
    get setViewingAttachments() { return setViewingAttachments; },
    get setSelectedAttachmentKeys() { return setSelectedAttachmentKeys; },
    get setLegacyHistoricalAttachmentsLoading() { return setLegacyHistoricalAttachmentsLoading; },
    get setLegacyHistoricalAttachmentsError() { return setLegacyHistoricalAttachmentsError; },
    get setLegacyHistoricalAttachments() { return setLegacyHistoricalAttachments; },
    get wizardDraft() { return wizardDraft; },
    get contractFile() { return contractFile; },
    get setContractFile() { return setContractFile; },
    get loadWizardContext() { return loadWizardContext; },
    get viewing() { return viewing; },
    get openViewing() { return openViewing; },
    get selectedAttachmentKeys() { return selectedAttachmentKeys; },
    get contractMutationGates() { return contractMutationGates; },
    get setAttachmentBatchSaving() { return setAttachmentBatchSaving; },
  });
  
  useEffect(() => {
    if (viewing && detailActiveTab === "legacy-attachments") void loadLegacyHistoricalAttachments(viewing);
  }, [detailActiveTab, viewing?.id]);

  const { submitArchiveClosure, saveContractObject, deleteContractObject, recoverWizard, openSubmitWizardFromList, save, submitWizard, approveWizard, createSealApplication, submit, openReview, approve, saveChange, reviewChange, openChanges, createContractEvent, openInvestigation, createInvestigation, advanceInvestigationWizard, startSelectedSeal, openApproverSettings, saveApproverSettings } = createContractWorkflowActions({
    get viewing() { return viewing; },
    get contractCapabilities() { return contractCapabilities; },
    get denyContractAction() { return denyContractAction; },
    get archiveSubjects() { return archiveSubjects; },
    get selectedArchiveObjectKeys() { return selectedArchiveObjectKeys; },
    get setArchiveClosureSaving() { return setArchiveClosureSaving; },
    get archiveClosureComment() { return archiveClosureComment; },
    get loadArchiveSubjects() { return loadArchiveSubjects; },
    get load() { return load; },
    get objectEditing() { return objectEditing; },
    get objectForm() { return objectForm; },
    get setObjectEditing() { return setObjectEditing; },
    get openViewing() { return openViewing; },
    get loadWizardContext() { return loadWizardContext; },
    get setOpen() { return setOpen; },
    get onNavigate() { return onNavigate; },
    get setWizardStep() { return setWizardStep; },
    get startCreate() { return startCreate; },
    get canOpenSubmitWizard() { return canOpenSubmitWizard; },
    get setEditing() { return setEditing; },
    get setSubmitting() { return setSubmitting; },
    get setChanging() { return setChanging; },
    get editing() { return editing; },
    get wizardDraft() { return wizardDraft; },
    get form() { return form; },
    get customers() { return customers; },
    get resolveCustomerRef() { return resolveCustomerRef; },
    get contractFile() { return contractFile; },
    get setSavingContract() { return setSavingContract; },
    get profile() { return profile; },
    get setWizardDraft() { return setWizardDraft; },
    get setContractFile() { return setContractFile; },
    get submitForm() { return submitForm; },
    get setAttachments() { return setAttachments; },
    get setSubmittingWizard() { return setSubmittingWizard; },
    get approvalOptions() { return approvalOptions; },
    get personName() { return personName; },
    get sealForm() { return sealForm; },
    get canActOnCurrentApproval() { return canActOnCurrentApproval; },
    get reviewForm() { return reviewForm; },
    get setSelectedAttachmentKeys() { return setSelectedAttachmentKeys; },
    get attachments() { return attachments; },
    get submitting() { return submitting; },
    get contractMutationGates() { return contractMutationGates; },
    get setSubmitSaving() { return setSubmitSaving; },
    get setReviewing() { return setReviewing; },
    get setSteps() { return setSteps; },
    get setReviewCurrentStep() { return setReviewCurrentStep; },
    get reviewing() { return reviewing; },
    get setViewing() { return setViewing; },
    get reloadViewingAttachments() { return reloadViewingAttachments; },
    get reloadDetailApprovals() { return reloadDetailApprovals; },
    get changing() { return changing; },
    get changeForm() { return changeForm; },
    get changeFile() { return changeFile; },
    get setChangeFile() { return setChangeFile; },
    get setSelectedRowKeys() { return setSelectedRowKeys; },
    get setChanges() { return setChanges; },
    get setChangeHistory() { return setChangeHistory; },
    get eventTarget() { return eventTarget; },
    get contractEventSubmitGate() { return contractEventSubmitGate; },
    get setEventSaving() { return setEventSaving; },
    get eventForm() { return eventForm; },
    get setEventTarget() { return setEventTarget; },
    get isContractInvestigationView() { return isContractInvestigationView; },
    get initialView() { return initialView; },
    get query() { return query; },
    get setInvestigationError() { return setInvestigationError; },
    get investigationForm() { return investigationForm; },
    get setSelectedInvestigationRegions() { return setSelectedInvestigationRegions; },
    get setInvestigationWizardStep() { return setInvestigationWizardStep; },
    get setInvestigationDraftValues() { return setInvestigationDraftValues; },
    get setCreatedInvestigation() { return setCreatedInvestigation; },
    get setInvestigationSupervisor() { return setInvestigationSupervisor; },
    get setInvestigating() { return setInvestigating; },
    get investigating() { return investigating; },
    get investigationDraftValues() { return investigationDraftValues; },
    get setInvestigationSubmitting() { return setInvestigationSubmitting; },
    get setApproverSettingsOpen() { return setApproverSettingsOpen; },
    get setApproverSettingsLoading() { return setApproverSettingsLoading; },
    get setApproverSettings() { return setApproverSettings; },
    get approverSettingsTargetUsername() { return approverSettingsTargetUsername; },
    get setSelectedApproverUsernames() { return setSelectedApproverUsernames; },
    get setApproverSettingsSaving() { return setApproverSettingsSaving; },
    get selectedApproverUsernames() { return selectedApproverUsernames; },
    get setDirectory() { return setDirectory; },
  });
  const handleContractDetailTabChange = (key: string) => {
    setDetailActiveTab(key);
    if (!viewing || key === detailActiveTab) return;
    if (key === "attachments") void reloadViewingAttachments(viewing);
    else if (key === "events") void reloadContractEvents(viewing, contractEventPage, contractEventKeyword, contractEventPageSize);
    else if (key === "approvals") void reloadDetailApprovals(viewing);
    else if (key === "archive") void loadArchiveSubjects(viewing);
    else void openViewing(viewing);
  };
  const returnFromDetail = () => {
    closeViewing();
    if (isContractDetailView) onNavigate?.(consumeContractDetailReturnView());
  };

  useEffect(() => {
    if (isContractDetailView || isContractInvestigationView || initialView === "contract-new") {
      void load();
      return;
    }
    const relationQuery = customerRelationQueryRef.current;
    const nextQuery = relationQuery || readContractQuery(initialView);
    const nextPagination = readContractListPagination(sessionStorage, initialView);
    setQuery(nextQuery);
    queryForm.resetFields();
    queryForm.setFieldsValue(nextQuery);
    setListPagination(nextPagination);
    setSelectedRowKeys([]);
    void load(nextQuery, nextPagination);
  }, [initialView, detailTarget?.id, detailTarget?.serial_no]);
  useEffect(() => {
    if (initialView !== "contract-new") {
      customerContextConsumerRef.current.reset();
      newContractRouteInitializedRef.current = false;
      setOpen(false);
      return;
    }
    if (newContractRouteInitializedRef.current) return;
    newContractRouteInitializedRef.current = true;
    // A customer-side “新增合同” always starts a new draft for that customer.
    // It must not restore an unfinished draft belonging to a different customer.
    const customerContext = getContractCustomerContext();
    if (customerContext) {
      startCreate(customerContext);
      return;
    }
    // The contract-center entry is always a blank contract. Existing drafts
    // remain available from "我的合同" and must not silently prefill this form.
    startCreate();
  }, [initialView]);
  useEffect(() => {
    if (initialView !== "contract-approver-settings") return;
    if (profile.role !== "admin") return;
    if (approverSettingsOpen || approverSettingsLoading) return;
    const targetUsername = String(new URLSearchParams(window.location.search).get("username") || "").trim();
    setApproverSettingsTargetUsername(targetUsername);
    void openApproverSettings();
  }, [initialView, profile.role, approverSettingsOpen, approverSettingsLoading]);
  // List filters, scope, status, and pagination are all applied by /records.
  // Keeping the current response intact avoids slicing or re-filtering a partial page.
  const rows = allRows;
  const getContractCustomerContext = (): LinkedCustomerContext | null => {
    if (sessionStorage.getItem(CONTRACT_CUSTOMER_ROUTE_SOURCE_KEY) !== "customer") {
      clearContractCustomerContext(sessionStorage);
      customerContextConsumerRef.current.reset();
      return null;
    }
    sessionStorage.removeItem(CONTRACT_CUSTOMER_ROUTE_SOURCE_KEY);
    return customerContextConsumerRef.current.consume();
  };
  const resolveCustomerRef = (customerId: number | undefined): CustomerRef | null => {
    return resolveContractCustomerSelection(customerId, customers, linkedCustomerContext, profile) as CustomerRef | null;
  };
  const startCreate = (context: LinkedCustomerContext | null = null) => {
    localStorage.removeItem(WIZARD_STORAGE_KEY);
    setEditing(null);
    setWizardDraft(null);
    setWizardStep(0);
    setContractFile(null);
    setSteps([]);
    setReviewCurrentStep(null);
    setAttachments([]);
    setHistory([]);
    form.resetFields();
    submitForm.resetFields();
    reviewForm.resetFields();
    sealForm.resetFields();
    let linkedCustomerId: number | undefined;
    let linkedContext: LinkedCustomerContext | null = null;
    if (context) {
      linkedContext = context;
      // The customer list loads asynchronously. Keep the linked id immediately;
      // customerOptions supplies the context label until the full list arrives.
      linkedCustomerId = context.id;
    }
    setLinkedCustomerContext(linkedContext);
    const defaults = buildContractDraftDefaults({
      serialNo: createContractNumber(),
      profile,
      customer: linkedContext ? { id: linkedContext.id, title: linkedContext.name } : null,
    });
    form.setFieldsValue({ ...defaults, customer_id: linkedCustomerId, signed_at: dayjs(defaults.signed_at) });
    setOpen(true);
  };
  useEffect(() => {
    const handleRouteReselect = (event: Event) => {
      if ((event as CustomEvent<string>).detail === "contract-new" && initialView === "contract-new") {
        customerContextConsumerRef.current.reset();
        startCreate(getContractCustomerContext());
      }
    };
    window.addEventListener("sunhold:route-reselect", handleRouteReselect);
    return () => window.removeEventListener("sunhold:route-reselect", handleRouteReselect);
  }, [initialView, profile.username, profile.department]);
  const populateDraftForm = (contract: Contract) => {
    setLinkedCustomerContext(null);
    const customerId = Number(contract.data.customer_id)
      || customers.find((customer) => customer.serial_no === contract.data.customer_no)?.id
      || customers.find((customer) => customer.title === contract.customer)?.id;
    form.setFieldsValue({
      ...contract,
      ...contract.data,
      customer_id: customerId || undefined,
      external_contract_numbers: contract.data.external_contract_numbers || (contract.data.external_contract_no ? [contract.data.external_contract_no] : []),
      signed_at: contract.data.signed_at ? dayjs(contract.data.signed_at) : dayjs(),
    });
  };

  const startEdit = (r: Contract) => {
    if (!contractCapabilities(r).canEdit) {
      denyContractAction();
      return;
    }
    setEditing(r);
    form.setFieldsValue({
      ...r,
      ...r.data,
      customer_id: Number(r.data.customer_id)
        || customers.find((customer) => customer.serial_no === r.data.customer_no)?.id
        || customers.find((customer) => customer.title === r.customer)?.id,
      external_contract_numbers: r.data.external_contract_numbers || (r.data.external_contract_no ? [r.data.external_contract_no] : []),
      signed_at: r.data.signed_at ? dayjs(r.data.signed_at) : undefined,
    });
    setOpen(true);
  };
  const canOpenSubmitWizard = (contract?: Contract | null) => ["草稿", "已拒绝"].includes(contract?.status || "");
  
  const openContractAttachments = (contract: Contract) => {
    void openViewing(contract, { detailTab: "attachments" });
  };
  const openContractApprovalInfo = (contract: Contract) => {
    void openViewing(contract, { detailTab: "approvals" });
  };
  const openContractRelatedCaseFromList = (contract: Contract) => {
    const data = contract.data as Record<string, unknown>;
    void openRelatedCase(data.case_no || data.case_serial_no || data.related_case_no);
  };

  const openChange = (r: Contract) => {
    if (!contractCapabilities(r).canChange) {
      denyContractAction();
      return;
    }
    setChanging(r);
    setChangeFile(null);
    changeForm.resetFields();
    changeForm.setFieldsValue({
      change_type: "合同补充/修订",
      customer: r.customer,
      contract_body: r.data.contract_body || "律所",
      contract_type: r.data.type || "其他",
      fee_type: r.data.fee_type || "固定收费",
      title: r.title,
      amount: r.data.amount,
      description: (r.data as any).description || "",
      external_contract_numbers: r.data.external_contract_numbers || (r.data.external_contract_no ? [r.data.external_contract_no] : []),
      end_date: r.data.end_date ? dayjs(r.data.end_date) : undefined,
    });
  };

  const openContractEvent = (contract: Contract) => {
    eventForm.resetFields();
    setEventTarget(contract);
  };
  
  const revokeDraft = (contract: Contract) => {
    if (!contractCapabilities(contract).canEdit) {
      denyContractAction();
      return;
    }
    confirmOperation({
      title: "撤销合同草稿",
      content: "将删除该草稿及其附件、事项记录，且无法恢复。仅未提交、未产生后续业务的草稿可以撤销。",
      okText: "确认撤销",
      okButtonProps: { danger: true },
      cancelText: "保留草稿",
      onConfirm: async () => {
        try {
          const response = await api.delete(`/contracts/${contract.id}/draft`);
          const feedback = normalizeContractActionResponse(response, "合同草稿撤销失败");
          if (!feedback.ok) throw new Error(feedback.message);
          localStorage.removeItem(WIZARD_STORAGE_KEY);
          setContractFile(null);
          setSelectedAttachmentKeys([]);
          setAttachments([]);
          sealForm.resetFields();
          setLinkedCustomerContext(null);
          if (wizardDraft?.id === contract.id) startCreate();
          if (viewing?.id === contract.id) closeViewing();
          setEventTarget((current) => current?.id === contract.id ? null : current);
          message.success("合同草稿已撤销，附件和事项记录已一并清理");
          void load();
        } catch (error: any) {
          message.error(extractContractErrorMessage(error, "合同草稿撤销失败"));
          throw error;
        }
      },
    });
  };
  const deleteRecycledContract = (contract: Contract) => {
    confirmOperation({
      title: "删除合同",
      content: "仅回收站合同可以物理删除；删除会同时清理合同附件和关联记录，且无法恢复。",
      okText: "确认删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onConfirm: async () => {
        try {
          const response = await api.post("/contracts/delete", { contract_ids: [contract.id] });
          const feedback = normalizeContractActionResponse(response, "合同删除失败");
          if (!feedback.ok) throw new Error(feedback.message);
          if (viewing?.id === contract.id) closeViewing();
          setSelectedAttachmentKeys([]);
          message.success("合同已删除");
          await load();
        } catch (error: any) {
          message.error(extractContractErrorMessage(error, "合同删除失败"));
          throw error;
        }
      },
    });
  };
  const deleteCompanyContract = (contract: Contract) => {
    confirmOperation({
      title: "删除合同",
      content: "将永久删除该公司合同及其附件和无关联记录，且无法恢复。已有审批、收款、案件、用印或财务关联的合同不能删除。",
      okText: "确认删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onConfirm: async () => {
        try {
          const response = await api.post("/contracts/company/delete", { contract_ids: [contract.id] });
          const feedback = normalizeContractActionResponse(response, "公司合同删除失败");
          if (!feedback.ok) throw new Error(feedback.message);
          if (viewing?.id === contract.id) closeViewing();
          setSelectedAttachmentKeys([]);
          message.success("公司合同已删除");
          await load();
        } catch (error: any) {
          message.error(extractContractErrorMessage(error, "公司合同删除失败"));
          throw error;
        }
      },
    });
  };
  const [investigationError, setInvestigationError] = useState("");

  const closeInvestigationWizard = () => {
    setInvestigationError("");
    setInvestigating(null);
    setCreatedInvestigation(null);
    setInvestigationDraftValues(null);
    setInvestigationSupervisor(null);
    setInvestigationWizardStep(0);
    setContractFile(null);
    investigationForm.resetFields();
    if (isContractInvestigationView) onNavigate?.(consumeContractDetailReturnView());
  };
  
  const { openContractPayment, createContractPaymentType, createContractPayment, createContractInvoice } = createContractFinanceActions({
    get contractCapabilities() { return contractCapabilities; },
    get denyContractAction() { return denyContractAction; },
    get paymentForm() { return paymentForm; },
    get setPaymentTarget() { return setPaymentTarget; },
    get setPaymentCandidates() { return setPaymentCandidates; },
    get setPaymentTypes() { return setPaymentTypes; },
    get setSelectedPaymentObjectKeys() { return setSelectedPaymentObjectKeys; },
    get setPaymentAmounts() { return setPaymentAmounts; },
    get paymentTarget() { return paymentTarget; },
    get setPaymentTypeCreating() { return setPaymentTypeCreating; },
    get paymentTypeCreateForm() { return paymentTypeCreateForm; },
    get setPaymentTypeCreateOpen() { return setPaymentTypeCreateOpen; },
    get setPaymentTypeSearch() { return setPaymentTypeSearch; },
    get contractMutationGates() { return contractMutationGates; },
    get setPaymentSaving() { return setPaymentSaving; },
    get selectedPaymentObjectKeys() { return selectedPaymentObjectKeys; },
    get paymentAmounts() { return paymentAmounts; },
    get paymentCandidates() { return paymentCandidates; },
    get viewing() { return viewing; },
    get openViewing() { return openViewing; },
    get invoiceTarget() { return invoiceTarget; },
    get setInvoiceSaving() { return setInvoiceSaving; },
    get invoiceForm() { return invoiceForm; },
    get setInvoiceTarget() { return setInvoiceTarget; },
  });
  const openContractPaymentTypeCreator = () => {
    paymentTypeCreateForm.resetFields();
    paymentTypeCreateForm.setFieldsValue({ nature: "官费", payee: paymentTypeSearch.trim() });
    setPaymentTypeCreateOpen(true);
  };

  const openContractInvoice = (contract: Contract) => {
    if (!contractCapabilities(contract).canInvoice) {
      denyContractAction();
      return;
    }
    const invoiceDue = Number(contract.data.invoice_should || 0) - Number(contract.data.invoice_opened || 0);
    invoiceForm.resetFields();
    invoiceForm.setFieldsValue({
      amount: invoiceDue > 0 ? invoiceDue : contract.data.amount,
      invoice_title: contract.customer,
      invoice_type: "增值税普通发票",
      invoice_content: "法律服务费",
      delivery_method: "电子发票",
    });
    setInvoiceTarget(contract);
  };

  const startCaseFromContract = (contract: Contract) => {
    if (!contractListActionPolicy(contract.status).canCreateCase) {
      message.warning("只能从审批中、审批通过或已完成的合同新建案件");
      return;
    }
    const context = buildCaseContractContext(contract);
    if (!context) {
      message.warning("合同缺少可用的合同号或客户信息，无法新建案件");
      return;
    }
    rememberCaseContractContext(sessionStorage, context);
    onNavigate?.("case-new");
  };
  const buildContractExportParams = () => {
    const { page: _page, page_size: _pageSize, ...exportParams } = buildContractListRequestParams(
      initialView,
      listPagination,
      query,
    );
    return exportParams;
  };
  const buildArchiveExportParams = () => {
    const archiveDate = Array.isArray(query.archive_date) ? query.archive_date : [];
    return {
      contract_no: query.serial_no || undefined,
      customer: query.customer || undefined,
      archive_status: query.archive_status || undefined,
      archive_date_from: archiveDate[0]?.format?.("YYYY-MM-DD"),
      archive_date_to: archiveDate[1]?.format?.("YYYY-MM-DD"),
    };
  };

  const needSelected = (action: () => void) =>
    selected ? action() : message.warning("请先选择一份合同");
  const selected = rows.find((row) => row.id === Number(selectedRowKeys[0]));
  const selectedActionPolicy = contractListActionPolicy(selected?.status);
  const selectedSecondaryActionPolicy = contractSecondaryActionPolicy(selected?.status);
  const selectedContractCapabilities = contractCapabilities(selected);
  const totals = Object.fromEntries(
    moneyKeys.map((key) => [
      key,
      rows.reduce((sum, row) => sum + Number(row.data[key] || 0), 0),
    ]),
  ) as Record<(typeof moneyKeys)[number], number>;
  const isAuditView = initialView === "contract-audit" || initialView.startsWith("contract-audit-");
  const auditActionPolicy = canAccessContractView(initialView, profile)
    ? contractAuditActionPolicy(initialView)
    : { canReview: false, canReviewChange: false, canExport: false };
  const stepItems = steps.map((s) => ({
    title: `第${s.step_order}级：${personName(s.approver_display_name || s.approver)}`,
    description: (
      <>
        <Tag
          color={
            s.status === "已通过"
              ? "green"
              : s.status === "已拒绝"
                ? "red"
                : s.status === "待审批"
                  ? "orange"
                  : "default"
          }
        >
          {displayContractStatus(s.status)}
        </Tag>
        {s.acted_at && (
          <span>{new Date(s.acted_at).toLocaleString("zh-CN")}</span>
        )}
        {s.comment && <p>{s.comment}</p>}
      </>
    ),
    status: (s.status === "已通过"
      ? "finish"
      : s.status === "待审批"
        ? "process"
        : s.status === "已拒绝"
          ? "error"
          : "wait") as "finish" | "process" | "error" | "wait",
  }));
  const currentApproval = reviewing
    ? (reviewCurrentStep || steps.find((step) => step.status === "待审批"))
    : steps.find((step) => step.status === "待审批");
  const approvalTarget = reviewing || wizardDraft;
  const approvalCapabilities = approvalTarget?.data.approval_capabilities;
  const currentApprover = approvalCapabilities?.current_approver
    || approvalTarget?.data.current_approver
    || currentApproval?.approver;
  const canActOnCurrentApproval = Boolean(
    currentApproval?.status === "待审批"
    && contractCapabilities(approvalTarget, {
      currentApprover,
      canApproveCurrent: approvalCapabilities?.can_approve_current,
    }).canApprove,
  );
  const contractObjectPolicy = contractObjectActionPolicy(viewing?.status);
  const detailSecondaryActionPolicy = contractSecondaryActionPolicy(viewing?.status);
  const detailContractCapabilities = contractCapabilities(viewing);
  const presentedReceipts = detailReceipts.map((row) => {
    const item = normalizeIncomingPaymentForContract(row, viewing || {});
    if (!item) return null;
    return { ...row, receipt_no: item.sequenceNo, received_date: item.receivedDate, bank_reference: item.bankReference, amount: item.amount, official_amount: item.officialAmount, agency_amount: item.agencyAmount, other_amount: item.otherAmount, payment_method: item.paymentMethod, claimant: item.claimant };
  }).filter(Boolean);
  const presentedInvoices = detailInvoices.map((row) => {
    const item = normalizeInvoiceObject(row);
    return { ...row, serial_no: item.applicationNo, status: item.status, description: item.remark, data: { ...row.data, invoice_no: item.invoiceNo, invoice_date: item.invoiceDate, amount: item.amount, official_amount: item.officialAmount, agency_amount: item.agencyAmount, other_amount: item.otherAmount, __lineThrough: item.lineThrough } };
  });
  const presentedPayments = detailPayments.map((row) => {
    const item = normalizePaidObject(row);
    return { ...row, serial_no: item.applicationNo, data: { ...row.data, applicant: item.applicant, pending_amount: item.pendingAmount, payment_date: item.paymentDate, payment_reference: item.packageNo, amount: item.paidAmount, payment_type: item.paymentType, official_amount: item.officialAmount, other_amount: item.otherAmount, __lineThrough: item.lineThrough } };
  });
  const viewingHasEventEndpoint = Boolean(viewing && buildContractEventsRequest(viewing, { page: contractEventPage, pageSize: contractEventPageSize, keyword: contractEventKeyword }).path);
  const objectPageData = paginateContractObjectRows(contractObjects, objectPage, objectPageSize);
  const approvalOptions = buildChinesePersonOptions(directory, (user: DirectoryUser) => Boolean(user.can_approve_contract));

  const contractApproverLabel = (
    <Space size={4}>
      <span>合同审批人</span>
    </Space>
  );

  const openRelatedPayment = (payment: Contract) => {
    const target = buildContractPaymentNavigation({
      pathname: window.location.pathname,
      hash: window.location.hash,
      payment,
      contract: viewing || {},
    });
    if (!target.ok) {
      message.warning(target.message);
      return;
    }
    window.history.pushState(null, "", target.url);
    onNavigate?.(target.page);
  };
  const updateListPagination = (current: number, pageSize: number) => {
    const nextPagination = saveContractListPagination(sessionStorage, initialView, { current, pageSize });
    setSelectedRowKeys([]);
    setListPagination(nextPagination);
    void load(undefined, nextPagination);
  };
  const applyQuery = (values: Record<string, any>) => {
    const normalized = normalizeContractQuery(values);
    customerRelationQueryRef.current = null;
    customerRelationQueryViewRef.current = null;
    saveContractListQuery(sessionStorage, initialView, normalized);
    setQuery(normalized);
    const nextPagination = saveContractListPagination(sessionStorage, initialView, { current: 1, pageSize: listPagination.pageSize });
    setSelectedRowKeys([]);
    setListPagination(nextPagination);
    void load(normalized, nextPagination);
  };
  const clearQuery = () => {
    queryForm.resetFields();
    applyQuery({});
  };
  const uniqueCustomers = Array.from(new Map(customers.map((customer) => [customer.title.normalize("NFKC").trim().toLocaleLowerCase(), customer])).values());
  const customerOptions = uniqueCustomers.map((customer) => ({
    value: customer.id,
    label: customer.title,
  }));
  if (linkedCustomerContext && !customerOptions.some((option) => option.value === linkedCustomerContext.id)) {
    customerOptions.unshift({ value: linkedCustomerContext.id, label: linkedCustomerContext.name });
  }
  const historyItems = history.map((event) => ({
    color: event.to_status === "已拒绝" ? "red" : event.action.includes("创建") ? "blue" : "green",
    children: (
      <div className="contract-history-item">
        <b>{event.action}</b>
        {event.from_status && event.from_status !== event.to_status && <Tag>{event.from_status} → {event.to_status}</Tag>}
        <small>{personName(event.operator)} · {dayjs(event.created_at).format("YYYY-MM-DD HH:mm")}</small>
        {event.comment && <p>{event.comment}</p>}
      </div>
    ),
  }));
  const handlePaymentObjectSelectionChange = (keys: Key[]) => {
    setSelectedPaymentObjectKeys(keys);
    setPaymentAmounts((previous) => {
      const next = { ...previous };
      keys.forEach((key) => {
        const id = Number(key);
        if (next[id] === undefined) {
          next[id] = Number(
            paymentCandidates.find((item) => item.contract_object_id === id)?.remaining_amount || 0,
          );
        }
      });
      return next;
    });
  };

  return (
    <>
      {initialView !== "contract-new" && !isContractDetailView && !isContractInvestigationView && (
        <ContractList
          initialView={initialView}
          queryForm={queryForm}
          isArchiveView={isArchiveView}
          isAuditView={isAuditView}
          loading={loading}
          rows={rows}
          listTotal={listTotal}
          listPagination={listPagination}
          selectedRowKeys={selectedRowKeys}
          selected={selected}
          selectedActionPolicy={selectedActionPolicy}
          selectedSecondaryActionPolicy={selectedSecondaryActionPolicy}
          selectedContractCapabilities={selectedContractCapabilities}
          auditActionPolicy={auditActionPolicy}
          profileDisplayName={profile.display_name}
          profileUsername={profile.username}
          totals={totals}
          personName={personName}
          peopleNames={peopleNames}
          contractCapabilities={contractCapabilities}
          canOpenSubmitWizard={canOpenSubmitWizard}
          onQuery={(values) => applyQuery(values)}
          onClearQuery={clearQuery}
          onPageChange={updateListPagination}
          onSelectionChange={(keys) => {
            setSelectedRowKeys(keys.length ? [keys[keys.length - 1]] : []);
            setChanging(null);
          }}
          onView={(contract) => void openViewing(contract)}
          onEdit={startEdit}
          onSeal={(contract) => void startSelectedSeal(contract)}
          onOpenAttachments={openContractAttachments}
          onOpenApprovalInfo={openContractApprovalInfo}
          onOpenRelatedCase={openContractRelatedCaseFromList}
          onOpenRelatedCustomer={openRelatedCustomer}
          onCreateCase={startCaseFromContract}
          onSubmitWizard={(contract) => void openSubmitWizardFromList(contract)}
          onRevokeDraft={revokeDraft}
          onDeleteRecycled={deleteRecycledContract}
          onDeleteCompany={deleteCompanyContract}
          onChangeContract={openChange}
          onPayment={(contract) => void openContractPayment(contract)}
          onInvoice={openContractInvoice}
          onInvestigation={(contract) => void openInvestigation(contract)}
          onApprove={(contract) => void openReview(contract)}
          onReviewChange={reviewChange}
          onExportExcel={exportExcel}
          onExportCsv={exportCsv}
          onImport={() => void load()}
        />
      )}

      {initialView === "contract-new" && (
        <Card className="panel contract-create-page" title="新建合同">
          <ContractWizardContent
            onDownloadAttachment={downloadAttachment}
            onClearLinkedCustomerContext={() => setLinkedCustomerContext(null)}
            wizardStep={wizardStep}
            editing={null}
            wizardDraft={wizardDraft}
            form={form}
            submitForm={submitForm}
            reviewForm={reviewForm}
            sealForm={sealForm}
            steps={steps}
            attachments={attachments}
            historyItems={historyItems}
            stepItems={stepItems}
            customerOptions={customerOptions}
            approvalOptions={approvalOptions}
            sealAssets={sealAssets}
            currentApproval={currentApproval}
            canActOnCurrentApproval={canActOnCurrentApproval}
            contractApproverLabel={contractApproverLabel}
            contractCapabilities={contractCapabilities}
            savingContract={savingContract}
            submittingWizard={submittingWizard}
            contractFile={contractFile}
            personName={personName}
            mode="page"
            onSave={save}
            onSubmitWizard={submitWizard}
            onRevokeDraft={() => wizardDraft && revokeDraft(wizardDraft)}
            onApproveWizard={approveWizard}
            onRefreshWizard={refreshWizard}
            onCreateSealApplication={createSealApplication}
            onContractFileChange={setContractFile}
            onUploadDraftAttachment={uploadDraftContractAttachment}
            onStartCreate={startCreate}
            onNavigate={onNavigate}
            onOpenContractCustomerCreation={() => openContractCustomerCreation(onNavigate)}
          />
          <div className="contract-page-actions">
            <Space>
              {wizardStep > 0 &&
                wizardStep < CONTRACT_CREATE_STEP_TITLES.length &&
                (wizardStep !== 1 ||
                  ["草稿", "已拒绝"].includes(wizardDraft?.status || "")) && (
                  <Button onClick={() => setWizardStep((step) => Math.max(0, step - 1))}>
                    上一步
                  </Button>
                )}
              {wizardStep === 0 && (
                <Button
                  type="primary"
                  loading={savingContract}
                  disabled={
                    !(editing || wizardDraft
                      ? contractCapabilities(editing || wizardDraft).canEdit
                      : contractCapabilities().canCreate)
                  }
                  onClick={save}
                >
                  下一步
                </Button>
              )}
              {wizardStep === 1 && wizardDraft?.status === "草稿" && (
                <Button
                  danger
                  disabled={!contractCapabilities(wizardDraft).canEdit}
                  onClick={() => revokeDraft(wizardDraft)}
                >
                  撤销草稿
                </Button>
              )}
              {wizardStep === 1 && ["草稿", "已拒绝"].includes(wizardDraft?.status || "") && (
                <Button
                  type="primary"
                  loading={submittingWizard}
                  disabled={!contractCapabilities(wizardDraft).canSubmit}
                  onClick={submitWizard}
                >
                  提交审批
                </Button>
              )}
              {wizardStep === 1 && wizardDraft?.status === "审批中" && (
                <Button
                  type="primary"
                  onClick={() => {
                    const route = buildContractDetailRoute(wizardDraft);
                    if (route) onNavigate?.(route);
                  }}
                >
                  查看合同详情
                </Button>
              )}
              {wizardStep === 2 && (
                <Button type="primary" onClick={refreshWizard}>
                  刷新审批状态
                </Button>
              )}
              {wizardStep === 3 && !wizardDraft?.data.seal_application_id && (
                <Button
                  onClick={() => {
                    sealForm.setFieldValue("submit", false);
                    void createSealApplication(false);
                  }}
                >
                  保存用印草稿
                </Button>
              )}
              {wizardStep === 3 &&
                !wizardDraft?.data.seal_application_id &&
                wizardDraft?.status === "审批中" &&
                wizardDraft.data.sync_seal && (
                  <Button
                    type="primary"
                    onClick={() => {
                      void createSealApplication(true);
                    }}
                  >
                    提交同步用印
                  </Button>
                )}
              {wizardStep === 3 &&
                !wizardDraft?.data.seal_application_id &&
                !(wizardDraft?.status === "审批中" && wizardDraft?.data.sync_seal) && (
                  <Button
                    type="primary"
                    onClick={() => {
                      void createSealApplication(true);
                    }}
                  >
                    提交申请
                  </Button>
                )}
              {wizardStep === 3 && Boolean(wizardDraft?.data.seal_application_id) && (
                <Button onClick={() => startCreate()}>开始新建合同</Button>
              )}
              {wizardStep === 3 &&
                wizardDraft?.data.seal_application_id &&
                wizardDraft?.status !== "审批中" && (
                  <Button onClick={() => startCreate()}>继续新建合同</Button>
                )}
              {wizardStep === 3 &&
                wizardDraft?.data.seal_application_id &&
                wizardDraft?.status !== "审批中" && (
                  <Button type="primary" onClick={() => onNavigate?.("seal-my")}>
                    进入用印中心
                  </Button>
                )}
            </Space>
          </div>
        </Card>
      )}

      {isContractInvestigationView && (
        <ContractInvestigationWizard
          open={Boolean(investigating || contractInvestigationRouteTarget)}
          isContractInvestigationView={isContractInvestigationView}
          investigating={investigating}
          wizardStep={investigationWizardStep}
          investigationForm={investigationForm}
          investigationError={investigationError}
          investigationDraftValues={investigationDraftValues}
          investigationSupervisor={investigationSupervisor}
          createdInvestigation={createdInvestigation}
          investigationSubmitting={investigationSubmitting}
          investigationRegion={investigationRegion}
          contractFile={contractFile}
          personName={personName}
          onCancel={closeInvestigationWizard}
          onNext={() => void advanceInvestigationWizard()}
          onPrev={() => setInvestigationWizardStep(0)}
          onSubmit={() => void createInvestigation()}
          onRegionPickerOpen={() => setInvestigationRegionPickerOpen(true)}
          onContractFileChange={setContractFile}
          onNavigate={(key) => onNavigate?.(key)}
        />
      )}

      <Modal
        width={isContractDetailView ? "100%" : 860}
        open={Boolean(viewing)}
        title={isContractDetailView ? "合同查看" : `合同查看：${viewing?.serial_no || ""}`}
        footer={
          <Space>
            {viewing?.status === "草稿" && (
              <Button
                danger
                disabled={!contractCapabilities(viewing).canEdit}
                onClick={() => revokeDraft(viewing)}
              >
                撤销草稿
              </Button>
            )}
            {viewing && (
              <Button
                disabled={!contractCapabilities(viewing).canChange}
                onClick={() => openChange(viewing)}
              >
                合同变更
              </Button>
            )}
            {!isContractDetailView && (
              <Button onClick={() => viewing && void exportContractDetailExcel(viewing)}>
                导出Excel
              </Button>
            )}
            <Button onClick={() => viewing && openContractEvent(viewing)}>新增事项</Button>
            <Button onClick={returnFromDetail}>关闭</Button>
          </Space>
        }
        onCancel={returnFromDetail}
        getContainer={isContractDetailView ? false : undefined}
        mask={!isContractDetailView}
        rootClassName={isContractDetailView ? "contract-detail-static-root" : undefined}
      >
        <ContractDetailView
          viewing={viewing}
          isContractDetailView={isContractDetailView}
          detailActiveTab={detailActiveTab}
          contractObjects={contractObjects}
          objectPage={objectPage}
          objectPageSize={objectPageSize}
          objectCases={objectCases}
          objectLogTarget={objectLogTarget}
          viewingAttachments={viewingAttachments}
          viewingAttachmentsLoading={viewingAttachmentsLoading}
          viewingAttachmentsError={viewingAttachmentsError}
          selectedAttachmentKeys={selectedAttachmentKeys}
          attachmentBatchSaving={attachmentBatchSaving}
          contractEvents={contractEvents}
          contractWorkflowEvents={contractWorkflowEvents}
          contractEventPage={contractEventPage}
          contractEventPageSize={contractEventPageSize}
          contractEventTotal={contractEventTotal}
          contractEventKeyword={contractEventKeyword}
          contractEventsLoading={contractEventsLoading}
          contractEventsError={contractEventsError}
          legacyHistoricalAttachments={legacyHistoricalAttachments}
          legacyHistoricalAttachmentsLoading={legacyHistoricalAttachmentsLoading}
          legacyHistoricalAttachmentsError={legacyHistoricalAttachmentsError}
          detailApprovals={detailApprovals}
          detailApprovalsError={detailApprovalsError}
          archiveSummary={archiveSummary}
          archiveSubjects={archiveSubjects}
          archiveSubjectsLoading={archiveSubjectsLoading}
          archiveClosureSaving={archiveClosureSaving}
          selectedArchiveObjectKeys={selectedArchiveObjectKeys}
          archiveClosureComment={archiveClosureComment}
          detailReceipts={detailReceipts}
          detailInvoices={detailInvoices}
          detailPayments={detailPayments}
          detailContractCapabilities={contractCapabilities(viewing)}
          contractFile={contractFile}
          personName={personName}
          peopleNames={peopleNames}
          onTabChange={handleContractDetailTabChange}
          onObjectPageChange={(page, pageSize) => {
            setObjectPage(page);
            setObjectPageSize(pageSize);
          }}
          onAddObject={() => {
            objectForm.resetFields();
            setObjectEditing({});
          }}
          onEditObject={(row) => {
            objectForm.setFieldsValue({
              case_record_id: row.case_record_id,
              fee_type: row.fee_type,
              amount: row.amount,
              remark: row.remark,
            });
            setObjectEditing({ id: row.id });
          }}
          onDeleteObject={(id) => void deleteContractObject(id)}
          onViewObjectLog={(row) => setObjectLogTarget(row)}
          onEventSearch={(value) => {
            setContractEventKeyword(value);
            setContractEventPage(1);
            if (viewing) void reloadContractEvents(viewing, 1, value, contractEventPageSize);
          }}
          onEventKeywordChange={(value) => setContractEventKeyword(value)}
          onEventPageChange={(page, pageSize) => {
            setContractEventPage(page);
            setContractEventPageSize(pageSize);
            if (viewing) void reloadContractEvents(viewing, page, contractEventKeyword, pageSize);
          }}
          onReloadEvents={() => viewing && void reloadContractEvents(viewing)}
          onUploadAttachment={() => void uploadViewingAttachment()}
          onDeleteAttachment={(item) => void deleteViewingAttachment(item)}
          onBatchDeleteAttachments={() => void batchDeleteViewingAttachments()}
          onAttachmentSelectionChange={setSelectedAttachmentKeys}
          onPreviewAttachment={(item) => void previewAttachment(item)}
          onDownloadAttachment={(item) => void downloadAttachment(item)}
          onReloadAttachments={() => viewing && void reloadViewingAttachments(viewing)}
          onReloadApprovals={() => viewing && void reloadDetailApprovals(viewing)}
          onArchiveClosureCommentChange={setArchiveClosureComment}
          onArchiveSelectionChange={(keys) => {
            setSelectedArchiveObjectKeys(keys);
          }}
          onSubmitArchiveClosure={() => void submitArchiveClosure()}
          onContractFileChange={setContractFile}
          onOpenRelatedCustomer={() => viewing && void openRelatedCustomer(viewing)}
          onOpenRelatedCase={(caseNo) => void openRelatedCase(caseNo)}
          onOpenRelatedPayment={openRelatedPayment}
          onExportDetailExcel={() => viewing && void exportContractDetailExcel(viewing)}
          onOpenContractEvent={() => viewing && openContractEvent(viewing)}
          onRevokeDraft={() => viewing && revokeDraft(viewing)}
          onChangeContract={() => viewing && openChange(viewing)}
          onReturn={returnFromDetail}
        />
      </Modal>

      <ContractObjectEditModal
        open={Boolean(objectEditing)}
        editing={objectEditing}
        objectForm={objectForm}
        objectCases={objectCases}
        viewingCustomer={viewing?.customer || ""}
        onCancel={() => {
          setObjectEditing(null);
          objectForm.resetFields();
        }}
        onOk={() => void saveContractObject()}
      />

      <ContractObjectLogModal
        open={Boolean(objectLogTarget)}
        logTarget={objectLogTarget}
        personName={personName}
        onCancel={() => setObjectLogTarget(null)}
      />

      <AttachmentPreviewModal
        open={Boolean(attachmentPreview)}
        preview={attachmentPreview}
        onClose={closeAttachmentPreview}
      />

      <ContractEventModal
        open={Boolean(eventTarget)}
        target={eventTarget}
        eventForm={eventForm}
        saving={eventSaving}
        onCancel={() => {
          if (eventSaving) return;
          setEventTarget(null);
          eventForm.resetFields();
        }}
        onOk={() => void createContractEvent()}
      />

      <Modal
        width={820}
        open={open && initialView !== "contract-new"}
        title={editing ? "编辑合同" : "新建合同"}
        footer={
          editing ? (
            <>
              <Button onClick={() => setOpen(false)}>取消</Button>
              <Button type="primary" loading={savingContract} onClick={save}>
                保存草稿
              </Button>
            </>
          ) : (
            <>
              {wizardStep > 0 &&
                wizardStep < CONTRACT_CREATE_STEP_TITLES.length &&
                (wizardStep !== 1 || ["草稿", "已拒绝"].includes(wizardDraft?.status || "")) && (
                  <Button onClick={() => setWizardStep((step) => Math.max(0, step - 1))}>
                    上一步
                  </Button>
                )}
              <Button onClick={() => setOpen(false)}>
                {wizardStep === 0 ? "取消" : "关闭"}
              </Button>
              {wizardStep === 0 && (
                <Button type="primary" loading={savingContract} onClick={save}>
                  下一步
                </Button>
              )}
              {wizardStep === 1 && wizardDraft?.status === "草稿" && (
                <Button danger onClick={() => wizardDraft && revokeDraft(wizardDraft)}>
                  撤销草稿
                </Button>
              )}
              {wizardStep === 1 && ["草稿", "已拒绝"].includes(wizardDraft?.status || "") && (
                <Button type="primary" loading={submittingWizard} onClick={submitWizard}>
                  提交审批
                </Button>
              )}
              {wizardStep === 1 && wizardDraft?.status === "审批中" && (
                <Button
                  type="primary"
                  onClick={() => {
                    const route = buildContractDetailRoute(wizardDraft!);
                    if (route) {
                      setOpen(false);
                      onNavigate?.(route);
                    }
                  }}
                >
                  查看合同详情
                </Button>
              )}
              {wizardStep === 2 && (
                <Button type="primary" onClick={refreshWizard}>
                  刷新审批状态
                </Button>
              )}
              {wizardStep === 3 && !wizardDraft?.data.seal_application_id && (
                <Button
                  onClick={() => {
                    sealForm.setFieldValue("submit", false);
                    void createSealApplication(false);
                  }}
                >
                  保存用印草稿
                </Button>
              )}
              {wizardStep === 3 &&
                !wizardDraft?.data.seal_application_id &&
                wizardDraft?.status === "审批中" &&
                wizardDraft.data.sync_seal && (
                  <Button type="primary" onClick={() => void createSealApplication(true)}>
                    提交同步用印
                  </Button>
                )}
              {wizardStep === 3 &&
                !wizardDraft?.data.seal_application_id &&
                !(wizardDraft?.status === "审批中" && wizardDraft?.data.sync_seal) && (
                  <Button type="primary" onClick={() => void createSealApplication(true)}>
                    提交申请
                  </Button>
                )}
              {wizardStep === 3 &&
                wizardDraft?.data.seal_application_id &&
                wizardDraft?.status !== "审批中" && (
                  <Button
                    type="primary"
                    onClick={() => {
                      setOpen(false);
                      onNavigate?.("seal-my");
                    }}
                  >
                    进入用印中心
                  </Button>
                )}
            </>
          )
        }
        onCancel={() => setOpen(false)}
        destroyOnHidden
      >
        <ContractWizardContent
            onDownloadAttachment={downloadAttachment}
            onClearLinkedCustomerContext={() => setLinkedCustomerContext(null)}
          wizardStep={wizardStep}
          editing={editing}
          wizardDraft={wizardDraft}
          form={form}
          submitForm={submitForm}
          reviewForm={reviewForm}
          sealForm={sealForm}
          steps={steps}
          attachments={attachments}
          historyItems={historyItems}
          stepItems={stepItems}
          customerOptions={customerOptions}
          approvalOptions={approvalOptions}
          sealAssets={sealAssets}
          currentApproval={currentApproval}
          canActOnCurrentApproval={canActOnCurrentApproval}
          contractApproverLabel={contractApproverLabel}
          contractCapabilities={contractCapabilities}
          savingContract={savingContract}
          submittingWizard={submittingWizard}
          contractFile={contractFile}
          personName={personName}
          mode="modal"
          onSave={save}
          onSubmitWizard={submitWizard}
          onRevokeDraft={() => wizardDraft && revokeDraft(wizardDraft)}
          onApproveWizard={approveWizard}
          onRefreshWizard={refreshWizard}
          onCreateSealApplication={createSealApplication}
          onContractFileChange={setContractFile}
          onUploadDraftAttachment={uploadDraftContractAttachment}
          onStartCreate={startCreate}
          onNavigate={onNavigate}
          onOpenContractCustomerCreation={() => openContractCustomerCreation(onNavigate)}
        />
      </Modal>

      <ContractSubmitModal
        open={Boolean(submitting)}
        submitting={submitting}
        submitForm={submitForm}
        approvalOptions={approvalOptions}
        contractApproverLabel={contractApproverLabel}
        saving={submitSaving}
        onCancel={() => {
          if (submitSaving) return;
          setSubmitting(null);
        }}
        onOk={submit}
      />

      <ApproverSettingsModal
        open={approverSettingsOpen}
        approverSettings={approverSettings}
        selectedApproverUsernames={selectedApproverUsernames}
        approverSettingsTargetUsername={approverSettingsTargetUsername}
        loading={approverSettingsLoading}
        saving={approverSettingsSaving}
        personName={personName}
        onNavigate={(key) => onNavigate?.(key)}
        onCancel={() => setApproverSettingsOpen(false)}
        onOk={saveApproverSettings}
        onSelectionChange={(keys) => setSelectedApproverUsernames(keys.map(String))}
      />

      <ContractReviewModal
        open={Boolean(reviewing)}
        reviewing={reviewing}
        reviewForm={reviewForm}
        stepItems={stepItems}
        currentApproval={currentApproval}
        canActOnCurrentApproval={canActOnCurrentApproval}
        personName={personName}
        onCancel={() => setReviewing(null)}
        onApprove={approve}
      />

      <ContractChangeModal
        open={Boolean(changing)}
        changing={changing}
        changeForm={changeForm}
        changeFile={changeFile}
        CONTRACT_CREATE_STEP_TITLES={CONTRACT_CREATE_STEP_TITLES}
        onCancel={() => {
          setChanging(null);
          setChangeFile(null);
          changeForm.resetFields();
        }}
        onOk={saveChange}
        onChangeFile={setChangeFile}
      />

      <ContractChangeHistoryModal
        open={Boolean(changeHistory)}
        changeHistory={changeHistory}
        changes={changes}
        personName={personName}
        onCancel={() => setChangeHistory(null)}
      />

      <ContractPaymentModal
        open={Boolean(paymentTarget)}
        paymentTarget={paymentTarget}
        paymentForm={paymentForm}
        paymentTypes={paymentTypes}
        paymentTypeSearch={paymentTypeSearch}
        selectedPaymentObjectKeys={selectedPaymentObjectKeys}
        paymentAmounts={paymentAmounts}
        paymentCandidates={paymentCandidates}
        selectedContractPaymentType={selectedContractPaymentType}
        paymentSaving={paymentSaving}
        onCancel={() => {
          if (paymentSaving) return;
          setPaymentTarget(null);
          setSelectedPaymentObjectKeys([]);
          setPaymentAmounts({});
        }}
        onOk={createContractPayment}
        onPaymentTypeSearch={setPaymentTypeSearch}
        onOpenPaymentTypeCreator={openContractPaymentTypeCreator}
        onPaymentObjectSelectionChange={handlePaymentObjectSelectionChange}
        onPaymentAmountChange={(objectId, value) =>
          setPaymentAmounts((previous) => ({ ...previous, [objectId]: value }))
        }
      />

      <PaymentTypeCreateModal
        open={paymentTypeCreateOpen}
        paymentTypeCreateForm={paymentTypeCreateForm}
        creating={paymentTypeCreating}
        onCancel={() => {
          setPaymentTypeCreateOpen(false);
          paymentTypeCreateForm.resetFields();
        }}
        onOk={() => void createContractPaymentType()}
      />

      <ContractInvoiceModal
        open={Boolean(invoiceTarget)}
        invoiceTarget={invoiceTarget}
        invoiceForm={invoiceForm}
        invoiceSaving={invoiceSaving}
        onCancel={() => {
          if (invoiceSaving) return;
          setInvoiceTarget(null);
        }}
        onOk={createContractInvoice}
      />

      {!isContractInvestigationView && (
        <ContractInvestigationWizard
          open={Boolean(investigating)}
          isContractInvestigationView={false}
          investigating={investigating}
          wizardStep={investigationWizardStep}
          investigationForm={investigationForm}
          investigationError={investigationError}
          investigationDraftValues={investigationDraftValues}
          investigationSupervisor={investigationSupervisor}
          createdInvestigation={createdInvestigation}
          investigationSubmitting={investigationSubmitting}
          investigationRegion={investigationRegion}
          contractFile={contractFile}
          personName={personName}
          onCancel={closeInvestigationWizard}
          onNext={() => void advanceInvestigationWizard()}
          onPrev={() => setInvestigationWizardStep(0)}
          onSubmit={() => void createInvestigation()}
          onRegionPickerOpen={() => setInvestigationRegionPickerOpen(true)}
          onContractFileChange={setContractFile}
          onNavigate={(key) => onNavigate?.(key)}
        />
      )}

      <InvestigationRegionPickerModal
        open={investigationRegionPickerOpen}
        selectedRegions={selectedInvestigationRegions}
        expandedProvinces={expandedInvestigationProvinces}
        investigationForm={investigationForm}
        onCancel={() => setInvestigationRegionPickerOpen(false)}
        onOk={() => {
          if (!selectedInvestigationRegions.length) {
            message.warning("请至少选择一个省市");
            return;
          }
          investigationForm.setFieldValue("authorization_scope", selectedInvestigationRegions.join("、"));
          setInvestigationRegionPickerOpen(false);
        }}
        onSelectAll={() =>
          setSelectedInvestigationRegions([
            ...new Set(INVESTIGATION_REGION_GROUPS.flatMap(({ province, cities }) => [province, ...cities])),
          ])
        }
        onClearAll={() => setSelectedInvestigationRegions([])}
        onProvinceToggle={(province, checked) =>
          setSelectedInvestigationRegions((current) =>
            checked ? [...new Set([...current, province])] : current.filter((value) => value !== province),
          )
        }
        onProvinceExpand={(province) =>
          setExpandedInvestigationProvinces((current) =>
            current.includes(province) ? current.filter((value) => value !== province) : [...current, province],
          )
        }
        onCitiesChange={(province, values) => {
          const cities = INVESTIGATION_REGION_GROUPS.find((g) => g.province === province)?.cities || [];
          setSelectedInvestigationRegions((current) => [
            ...current.filter((value) => !cities.includes(value)),
            ...(values as string[]),
          ]);
        }}
      />
    </>
  );
}
