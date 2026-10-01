"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""


import asyncio as asyncio


import base64 as base64


import ctypes as ctypes


from contextlib import asynccontextmanager as asynccontextmanager, suppress as suppress


import csv as csv


import math as math


import gc as gc


import hashlib as hashlib


from datetime import date as date, datetime as datetime, timedelta as timedelta, timezone as timezone


from decimal import Decimal as Decimal, ROUND_UP as ROUND_UP


import io as io


import json as json


import logging as logging


from pathlib import Path as Path


import re as re


import secrets as secrets


import sys as sys


from typing import Annotated as Annotated, Literal as Literal


import unicodedata as unicodedata


import zipfile as zipfile


from zoneinfo import ZoneInfo as ZoneInfo


from urllib.parse import quote as quote


from uuid import NAMESPACE_URL as NAMESPACE_URL, uuid4 as uuid4, uuid5 as uuid5


from xml.sax.saxutils import escape as xml_escape  # noqa: F401 -- main 兼容导出使用原有名称。


import httpx as httpx


from fastapi import Depends as Depends, FastAPI as FastAPI, File as File, Form as Form, HTTPException as HTTPException, Query as Query, Request as Request, Response as Response, UploadFile as UploadFile, status as status


from docx import Document as Document


from docx.enum.text import WD_ALIGN_PARAGRAPH as WD_ALIGN_PARAGRAPH


from docx.oxml.ns import qn as qn


from docx.shared import Cm as Cm, Inches as Inches, Pt as Pt


from openpyxl import load_workbook as load_workbook


from fastapi.middleware.cors import CORSMiddleware as CORSMiddleware


from fastapi.exceptions import RequestValidationError as RequestValidationError


from fastapi.security import OAuth2PasswordRequestForm as OAuth2PasswordRequestForm


from fastapi.responses import FileResponse as FileResponse, JSONResponse as JSONResponse, StreamingResponse as StreamingResponse


from pydantic import BaseModel as BaseModel, Field as Field, field_validator as field_validator


import qrcode as qrcode


import pypdfium2 as pdfium  # noqa: F401 -- storage 与 main 从此聚合入口导入。


from sqlalchemy import String as String, and_ as and_, delete as delete, false as false, func as func, inspect as inspect, or_ as or_, select as select, text as text, update as update


from sqlalchemy.exc import IntegrityError as IntegrityError, SQLAlchemyError as SQLAlchemyError


from sqlalchemy.ext.asyncio import AsyncSession as AsyncSession


from app.deepseek_harness import create_case_agent_runtime as create_case_agent_runtime


from app.agent_skills import GENERAL_SKILL as GENERAL_SKILL, SKILLS_BY_ID as SKILLS_BY_ID, public_skill_catalog as public_skill_catalog


from app.agent_attachment_reader import read_attachment as read_attachment


from app.case_workflow_rules import build_case_workflow_guide as build_case_workflow_guide


from app.config import settings as settings


from app.database import Base as Base, SessionLocal as SessionLocal, engine as engine, get_db as get_db


from app.legacy_contract_history_router import create_legacy_contract_history_router as create_legacy_contract_history_router


from app.legacy_ipr_history_router import create_legacy_ipr_history_router as create_legacy_ipr_history_router


from app.ipr_fee_file_router import router as ipr_fee_file_router  # noqa: F401 -- main 挂载该路由。


from app.ipr_cpc import CPC_APPLICATION_CATEGORY as CPC_APPLICATION_CATEGORY, create_ipr_cpc_router as create_ipr_cpc_router, is_cpc_application_attachment as is_cpc_application_attachment


from app.legacy_ls_history_router import create_legacy_ls_history_router as create_legacy_ls_history_router


from app.dingtalk import DingTalkError as DingTalkError, dingtalk_client as dingtalk_client


from app.legacy_schema import align_legacy_column_types as align_legacy_column_types, align_legacy_constraints as align_legacy_constraints, align_legacy_indexes as align_legacy_indexes, create_full_legacy_schema as create_full_legacy_schema, ensure_legacy_indexes as ensure_legacy_indexes


from app.models import AgentDocument as AgentDocument, BusinessRecord as BusinessRecord, CaseAssistedFee as CaseAssistedFee, CaseEvent as CaseEvent, CaseFileTypeFeeTypeRelation as CaseFileTypeFeeTypeRelation, CaseTypeCasePhaseRelation as CaseTypeCasePhaseRelation, CaseTypeFileTypeRelation as CaseTypeFileTypeRelation, CommunicationLog as CommunicationLog, ContractApprovalStep as ContractApprovalStep, ContractEvent as ContractEvent, ContractObject as ContractObject, ContractObjectLog as ContractObjectLog, ContractPaymentLine as ContractPaymentLine, Department as Department, DocumentTemplate as DocumentTemplate, FileAttachment as FileAttachment, FinanceTransaction as FinanceTransaction, HearingSchedule as HearingSchedule, HrSubrecord as HrSubrecord, IncomingPayment as IncomingPayment, InvestigationClueLink as InvestigationClueLink, InvestigationEvidence as InvestigationEvidence, InvestigationEvidenceFile as InvestigationEvidenceFile, InvestigationHistoricalReference as InvestigationHistoricalReference, InvestigationTaskLink as InvestigationTaskLink, IprCaseAssistedFee as IprCaseAssistedFee, IprCaseAnnualFee as IprCaseAnnualFee, IprCaseBatch as IprCaseBatch, IprCaseBatchItem as IprCaseBatchItem, IprCaseCustomer as IprCaseCustomer, IprCaseCustomerContact as IprCaseCustomerContact, IprCaseFileCustomImportBatch as IprCaseFileCustomImportBatch, IprCaseFileCustomImportCandidate as IprCaseFileCustomImportCandidate, IprCaseLawFirm as IprCaseLawFirm, IprCaseLog as IprCaseLog, IprCaseRebootLink as IprCaseRebootLink, IprCaseReminder as IprCaseReminder, IprCaseReminderSuppression as IprCaseReminderSuppression, IprCaseReminderType as IprCaseReminderType, IprCaseWarning as IprCaseWarning, IprCaseWarningRule as IprCaseWarningRule, IprOfficialImportBatch as IprOfficialImportBatch, IprOfficialImportCandidate as IprOfficialImportCandidate, JarFeeAuditLog as JarFeeAuditLog, JobRole as JobRole, LawFirm as LawFirm, LawFirmAudit as LawFirmAudit, LawFirmContact as LawFirmContact, LegacyCase as LegacyCase, LegacyCaseFile as LegacyCaseFile, LegacyCaseLog as LegacyCaseLog, LegacyCaseParticipant as LegacyCaseParticipant, LegacyCaseTaskHistory as LegacyCaseTaskHistory, LegacyCaseTaskHistoryFile as LegacyCaseTaskHistoryFile, LegacyCaseTaskHistoryMessage as LegacyCaseTaskHistoryMessage, LegacyCaseTaskHistoryNode as LegacyCaseTaskHistoryNode, LegacyCaseTaskHistoryNodeParticipant as LegacyCaseTaskHistoryNodeParticipant, LegacyCaseTaskHistoryNotification as LegacyCaseTaskHistoryNotification, LegacyCaseTaskHistoryReadReceipt as LegacyCaseTaskHistoryReadReceipt, LegacyContract as LegacyContract, LegacyContractAudit as LegacyContractAudit, LegacyContractFile as LegacyContractFile, LegacyCustomer as LegacyCustomer, LegacyCustomerContact as LegacyCustomerContact, LegacyCustomerHistoryBaseline as LegacyCustomerHistoryBaseline, LegacyCustomerHistoryContact as LegacyCustomerHistoryContact, LegacyCustomerHistoryCoordinator as LegacyCustomerHistoryCoordinator, LegacyCustomerHistoryEvent as LegacyCustomerHistoryEvent, LegacyCustomerHistoryFile as LegacyCustomerHistoryFile, LegacyFinanceAllocation as LegacyFinanceAllocation, LegacyFinanceAudit as LegacyFinanceAudit, LegacyFinanceFile as LegacyFinanceFile, LegacyFinanceRecord as LegacyFinanceRecord, LegacyHistoricalAttachment as LegacyHistoricalAttachment, LegacyInvestigation as LegacyInvestigation, LegacyInvestigationClue as LegacyInvestigationClue, LegacyInvestigationClueEvidence as LegacyInvestigationClueEvidence, LegacyInvestigationClueEvidenceFile as LegacyInvestigationClueEvidenceFile, LegacyInvestigationClueFile as LegacyInvestigationClueFile, LegacyInvestigationTask as LegacyInvestigationTask, LegacyOfficialDocument as LegacyOfficialDocument, LegacyOfficialDocumentAudit as LegacyOfficialDocumentAudit, LegacyOfficialDocumentFile as LegacyOfficialDocumentFile, Notification as Notification, OfficialOutgoingDocument as OfficialOutgoingDocument, ReceivablePlan as ReceivablePlan, ReconciliationBatch as ReconciliationBatch, RolePermission as RolePermission, SealAsset as SealAsset, SealAssetAudit as SealAssetAudit, SecurityPolicy as SecurityPolicy, SystemConfig as SystemConfig, SystemMenu as SystemMenu, SystemParameter as SystemParameter, User as User, VipTask as VipTask, VipTaskMessage as VipTaskMessage, VipTaskNode as VipTaskNode, Warehouse as Warehouse, WarehouseEvidenceLocation as WarehouseEvidenceLocation, WarehouseLegacyEvidenceMapping as WarehouseLegacyEvidenceMapping, WarehouseStorageLocation as WarehouseStorageLocation, WorkflowEvent as WorkflowEvent


from app.security import create_token as create_token, current_identity as current_identity, hash_password as hash_password, password_needs_rehash as password_needs_rehash, user_role_ids as user_role_ids, verify_password as verify_password


from app.user_agent_skills import CUSTOM_SKILL_FILE_LIMIT as CUSTOM_SKILL_FILE_LIMIT, CUSTOM_SKILL_LIMIT as CUSTOM_SKILL_LIMIT, custom_skill_agent as custom_skill_agent, custom_skill_public as custom_skill_public, normalize_custom_skill as normalize_custom_skill, parse_uploaded_skill as parse_uploaded_skill, user_skill_config_key as user_skill_config_key
