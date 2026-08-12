from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase


class LegacyBase(DeclarativeBase):
    pass


class SysMenu(LegacyBase):
    __tablename__ = "SYS_Menu"

    menu_id = Column("MenuId", BigInteger, primary_key=True)
    menu_code = Column("MenuCode", String(20))
    menu_name = Column("MenuName", String(50))
    parent_menu_id = Column("ParentMenuId", String(20))
    order_id = Column("OrderId", Integer)
    image_url = Column("ImageUrl", String(128))
    link_url = Column("LinkUrl", String(128))
    comments = Column("Comments", String(256))
    menu_type_id = Column("MenuTypeId", Integer)
    is_actived = Column("IsActived", String(1))


class HrRole(LegacyBase):
    __tablename__ = "HR_Role"

    role_id = Column("RoleId", Integer, primary_key=True)
    company_id = Column("CompanyId", Integer)
    role_name = Column("RoleName", String(30))
    role_desc = Column("RoleDesc", String(50))


class HrRolePermission(LegacyBase):
    __tablename__ = "HR_Role_Permissions"

    role_id = Column("RoleId", Integer, primary_key=True)
    resource_id = Column("ResourceId", BigInteger, primary_key=True)
    resource_code = Column("ResourceCode", String(20), primary_key=True)
    resource_type = Column("ResourceType", String(10), primary_key=True)
    resource_name = Column("ResourceName", String(64))


class HrStaff(LegacyBase):
    __tablename__ = "HR_Staff"

    staff_id = Column("StaffId", Integer, primary_key=True)
    staff_no = Column("StaffNo", String(30))
    staff_name = Column("StaffName", String(30))
    staff_ch_name = Column("StaffChName", String(100))
    department_id = Column("DepartmentId", Integer)
    org_id = Column("OrgId", Integer)
    manager_id = Column("ManagerId", Integer)
    role_id = Column("RoleId", Integer)
    is_actived = Column("IsActived", String(1))
    status = Column("Status", Integer)
    is_admin = Column("IsAdmin", String(1))
    is_manager = Column("IsManager", String(1))
    open_id = Column("OpenId", String(100))


class IprUser(LegacyBase):
    __tablename__ = "IPR_User"

    user_id = Column("UserId", Integer, primary_key=True)
    user_name = Column("UserName", String(30))
    employee_name = Column("EmployeeName", String(100))
    department_id = Column("DepartmentId", Integer)
    org_id = Column("OrgId", Integer)
    is_admin = Column("IsAdmin", String(1))
    status = Column("Status", Integer)


class IprUserRole(LegacyBase):
    __tablename__ = "IPR_UserRole"

    user_role_id = Column("UserRoleId", Integer, primary_key=True)
    user_id = Column("UserId", Integer)
    role_id = Column("RoleId", Integer)
