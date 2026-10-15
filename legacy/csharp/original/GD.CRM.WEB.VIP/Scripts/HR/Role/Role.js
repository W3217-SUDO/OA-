/*角色*/
var role = {
    List: function() {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/HR/Role/RoleList", function(response) {
            
            if (response.IsSuccess) {
                $("tbody", "#tblRoleList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.RoleList, function(i, c) {
                        $("tbody", "#tblRoleList").addRow(c.RoleId, c.RoleName,
                            "<a href='javascript:void(0)' onclick='javascript:role.Permissions(" + c.RoleId + ")'>权限设定</a>",
                            "<a href='javascript:void(0)' onclick='javascript:role.Open(" + c.RoleId + ")'>修改</a>");
                    });

                    $("tfoot", "#tblRoleList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.Rolelist").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: role.List,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblRoleList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    /*创建角色权限*/
    Permissions: function(roleId) {

        var url =  AP_ROOT + AP_PAGE_ID + "/HR/Role/RolePermissions";
        var data = {
            roleId: roleId
        };
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#permissionsModal').modal({ backdrop: 'static', keyboard: false });
            $('#permissionsModal').on('hidden.bs.modal', function () {
                $("#permissionsModal").remove();
            });
        });

        //$('.permissions').load(url, data, function(result) {
        //    $.closeLoading();
        //    $('#permissionsModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    /*创建角色*/
    Open: function(roleId) {

        var url =  AP_ROOT + AP_PAGE_ID + "/HR/Role/Role";
        var data = {
            roleId: roleId
        };
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#roleModal').modal({ backdrop: 'static', keyboard: false });
            $('#roleModal').on('hidden.bs.modal', function () {
                $("#roleModal").remove();
            });
        });

        //$('.role').load(url, data, function(result) {
        //    $.closeLoading();
        //    $('#roleModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    Close: function() {
        $('#roleModal').modal('hide');
    },

    PermissionsClose: function() {
        $('#permissionsModal').modal('hide');
    },

    CreateUpdate: function() {

        if ($("#Role_RoleName").val() == '') {
            $.showModalMessageBox("请输入角色名称.");
            return false;
        }

        if ($("#Role_RoleDesc").val() == '') {
            $.showModalMessageBox("请输入角色名称描述.");
            return false;
        }

        var data = {};

        data["Role.RoleId"] = $("#RoleId").val();
        data["Role.RoleName"] = $("#Role_RoleName").val();
        data["Role.RoleDesc"] = $("#Role_RoleDesc").val();

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/HR/Role/RoleCreateUpdate", data, function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                role.Close();
                role.List();
            } else {
                ;
                $.showModalMessageBox(response.Message);
            }
        });
    },

    BulidPermissionsTreeView: function() {
        var data1 = {
            roleId: $("#RoleId").val()
        };

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/HR/Role/GetRolePermissions", data1, function (response) {
            if (response.IsSuccess) {
                
                $('#treeview').treeview({
                    data: response.Data, // 数据源
                    showCheckbox: true, //是否显示复选框
                    highlightSelected: false, //是否高亮选中
                    //nodeIcon: 'glyphicon glyphicon-user',    //节点上的图标
                    nodeIcon: '',
                    emptyIcon: 'icon expand-icon glyphicon glyphicon-minus', //没有子节点的节点图标
                    multiSelect: true, //多选
                    onNodeChecked: function (event, data) {
                         
                        if (data.parentId != null) {
                            $('#treeview').treeview('checkNode', [data.parentId, { silent: true }]);
                        }
                        if (data.nodes != null) {
                            $.each(data.nodes, function(i, c) {
                                $('#treeview').treeview('checkNode', [c.nodeId, { silent: true }]);
                            });
                        }
                    },
                    onNodeUnchecked: function(event, data) {
                        if (data.nodes != null) {
                            $.each(data.nodes, function(i, c) {
                                $('#treeview').treeview('uncheckNode', [c.nodeId, { silent: true }]);
                            });
                        }
                    },
                    onNodeSelected: function(event, data) {
                    }
                });
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    CreateUpdateRolePermissions: function() {
        var nodes = $('#treeview').treeview('getChecked');
        var data = {};

        data["RoleId"] = $("#RoleId").val();
       
        if (nodes != null) {
            $.each(nodes, function (i) {
                data["Nodes[" + i + "].nodeOriginalId"] = nodes[i].nodeOriginalId;
                data["Nodes[" + i + "].nodeType"] = nodes[i].nodeType;
                data["Nodes[" + i + "].nodeCode"] = nodes[i].nodeCode;
                data["Nodes[" + i + "].text"] = nodes[i].text;
            });
        }

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/HR/Role/RolePermissionsCreateUpdate", data, function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                role.PermissionsClose();
            } else {
                ;
                $.showModalMessageBox(response.Message);
            }
        });
    },
}

$(document).ready(function () {

    role.List();

    $(document).off('click', '.RoleCreate').on('click', '.RoleCreate', function () {
        role.Open();
    });

    $(document).off('click', '#btnRoleCreate').on('click', '#btnRoleCreate', function () {
        role.Open();
    });

    $(document).off('click', '#btnRoleClose').on('click', '#btnRoleClose', function () {
        role.Close();
    });

    $(document).off('click', '#btnRoleCancel').on('click', '#btnRoleCancel', function () {
        role.Close();
    });

    $(document).off('click', '#btnRoleAddItem').on('click', '#btnRoleAddItem', function () {
        role.RoleItem.Add();
    });

    $(document).off('click', '.btn_clear').on('click', '.btn_clear', function () {
        role.RoleItem.Clear(this);
    });

    $(document).off('click', '.btn_remove').on('click', '.btn_remove', function () {
        role.RoleItem.Remove(this);
    });

    $(document).off('click', '#btnRole').on('click', '#btnRole', function () {
        role.CreateUpdate();
    });

    $(document).off('click', '#btnRolePermissions').on('click', '#btnRolePermissions', function () {
        role.CreateUpdateRolePermissions();
    });
 
    $(document).off('click', '#btnRolePermissionsCancel').on('click', '#btnRolePermissionsCancel', function () {
        role.PermissionsClose();
    });

    $(document).off('click', '#btnRolePermissionsClose').on('click', '#btnRolePermissionsClose', function () {
    //$("#btnRolePermissionsClose").off().on("click", function () {
        role.PermissionsClose();
    });
});


