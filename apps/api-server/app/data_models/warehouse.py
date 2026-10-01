"""仓库、库位及证据存放数据模型。"""

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Warehouse(Base):
    """Warehouse master data, preserving the BAS_Warehouse business key."""

    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True)
    legacy_warehouse_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    warehouse_no: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(30), index=True)
    address: Mapped[str] = mapped_column(String(500), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    legacy_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    legacy_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WarehouseStorageLocation(Base):
    """A physical storage location belongs to exactly one warehouse."""

    __tablename__ = "warehouse_storage_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    legacy_storage_location_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True)
    storage_location_no: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(30), index=True)
    address: Mapped[str] = mapped_column(String(500), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    legacy_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    legacy_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WarehouseEvidenceLocation(Base):
    """Structured warehouse and storage-location binding for a warehouse record."""

    __tablename__ = "warehouse_evidence_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), unique=True, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True)
    storage_location_id: Mapped[int] = mapped_column(ForeignKey("warehouse_storage_locations.id", ondelete="RESTRICT"), index=True)
    assigned_by: Mapped[str] = mapped_column(String(64), default="system")
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WarehouseLegacyEvidenceMapping(Base):
    """Auditable one-to-one import state for every legacy evidence row."""

    __tablename__ = "warehouse_legacy_evidence_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    legacy_evidence_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    legacy_evidence_guid: Mapped[str] = mapped_column(String(50), default="", index=True)
    record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True, index=True)
    storage_location_id: Mapped[int | None] = mapped_column(ForeignKey("warehouse_storage_locations.id", ondelete="SET NULL"), nullable=True, index=True)
    mapping_status: Mapped[str] = mapped_column(String(64), index=True)
    reason: Mapped[str] = mapped_column(String(500), default="")
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
