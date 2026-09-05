"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""


import asyncio


import base64


import ctypes


from contextlib import asynccontextmanager, suppress


import csv


import math


import gc


import hashlib


from datetime import date, datetime, timedelta, timezone


from decimal import Decimal, ROUND_UP


import io


import json


import logging


from pathlib import Path


import re


import secrets


import sys


from typing import Annotated, Literal


import unicodedata


import zipfile


from zoneinfo import ZoneInfo


from urllib.parse import quote


from uuid import NAMESPACE_URL, uuid4, uuid5


from xml.sax.saxutils import escape as xml_escape


import httpx


from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile, status


from docx import Document


from docx.enum.text import WD_ALIGN_PARAGRAPH


from docx.oxml.ns import qn


from docx.shared import Cm, Inches, Pt


from openpyxl import load_workbook


from fastapi.middleware.cors import CORSMiddleware


from fastapi.exceptions import RequestValidationError


from fastapi.security import OAuth2PasswordRequestForm


from fastapi.responses import FileResponse, JSONResponse, StreamingResponse


from pydantic import BaseModel, Field, field_validator


import qrcode


import pypdfium2 as pdfium


from sqlalchemy import String, and_, delete, false, func, inspect, or_, select, text, update


from sqlalchemy.exc import IntegrityError, SQLAlchemyError


from sqlalchemy.ext.asyncio import AsyncSession


from app.deepseek_harness import create_case_agent_runtime


from app.agent_skills import GENERAL_SKILL, SKILLS_BY_ID, public_skill_catalog


from app.agent_attachment_reader import read_attachment


from app.case_workflow_rules import build_case_workflow_guide


from app.config import settings


from app.database import Base, SessionLocal, engine, get_db


from app.legacy_contract_history_router import create_legacy_contract_history_router


from app.legacy_ipr_history_router import create_legacy_ipr_history_router


from app.ipr_fee_file_router import router as ipr_fee_file_router


from app.ipr_cpc import CPC_APPLICATION_CATEGORY, create_ipr_cpc_router, is_cpc_application_attachment


from app.legacy_ls_history_router import create_legacy_ls_history_router


from app.dingtalk import DingTalkError, dingtalk_client


from app.legacy_schema import align_legacy_column_types, align_legacy_constraints, align_legacy_indexes, create_full_legacy_schema, ensure_legacy_indexes


from app.models import AgentDocument, BusinessRecord, CaseAssistedFee, CaseEvent, CaseFileTypeFeeTypeRelation, CaseTypeCasePhaseRelation, CaseTypeFileTypeRelation, CommunicationLog, ContractApprovalStep, ContractEvent, ContractObject, ContractObjectLog, ContractPaymentLine, Department, DocumentTemplate, FileAttachment, FinanceTransaction, HearingSchedule, HrSubrecord, IncomingPayment, InvestigationClueLink, InvestigationEvidence, InvestigationEvidenceFile, InvestigationHistoricalReference, InvestigationTaskLink, IprCaseAssistedFee, IprCaseAnnualFee, IprCaseBatch, IprCaseBatchItem, IprCaseCustomer, IprCaseCustomerContact, IprCaseFileCustomImportBatch, IprCaseFileCustomImportCandidate, IprCaseLawFirm, IprCaseLog, IprCaseRebootLink, IprCaseReminder, IprCaseReminderSuppression, IprCaseReminderType, IprCaseWarning, IprCaseWarningRule, IprOfficialImportBatch, IprOfficialImportCandidate, JarFeeAuditLog, JobRole, LawFirm, LawFirmAudit, LawFirmContact, LegacyCase, LegacyCaseFile, LegacyCaseLog, LegacyCaseParticipant, LegacyCaseTaskHistory, LegacyCaseTaskHistoryFile, LegacyCaseTaskHistoryMessage, LegacyCaseTaskHistoryNode, LegacyCaseTaskHistoryNodeParticipant, LegacyCaseTaskHistoryNotification, LegacyCaseTaskHistoryReadReceipt, LegacyContract, LegacyContractAudit, LegacyContractFile, LegacyCustomer, LegacyCustomerContact, LegacyCustomerHistoryBaseline, LegacyCustomerHistoryContact, LegacyCustomerHistoryCoordinator, LegacyCustomerHistoryEvent, LegacyCustomerHistoryFile, LegacyFinanceAllocation, LegacyFinanceAudit, LegacyFinanceFile, LegacyFinanceRecord, LegacyHistoricalAttachment, LegacyInvestigation, LegacyInvestigationClue, LegacyInvestigationClueEvidence, LegacyInvestigationClueEvidenceFile, LegacyInvestigationClueFile, LegacyInvestigationTask, LegacyOfficialDocument, LegacyOfficialDocumentAudit, LegacyOfficialDocumentFile, Notification, OfficialOutgoingDocument, ReceivablePlan, ReconciliationBatch, RolePermission, SealAsset, SealAssetAudit, SecurityPolicy, SystemConfig, SystemMenu, SystemParameter, User, VipTask, VipTaskMessage, VipTaskNode, Warehouse, WarehouseEvidenceLocation, WarehouseLegacyEvidenceMapping, WarehouseStorageLocation, WorkflowEvent


from app.security import create_token, current_identity, hash_password, password_needs_rehash, user_role_ids, verify_password


from app.user_agent_skills import CUSTOM_SKILL_FILE_LIMIT, CUSTOM_SKILL_LIMIT, custom_skill_agent, custom_skill_public, normalize_custom_skill, parse_uploaded_skill, user_skill_config_key
