/*部门*/
var department = {
    List: function() {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/HR/Department/DepartmentList", function (response) {
            
            if (response.IsSuccess) {
                $("tbody", "#tblDepartmentList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.DepartmentList, function(i, c) {
                        $("tbody", "#tblDepartmentList").addRow(c.DepartmentId, c.DepartmentName,c.DepartmentCode,
                            "<a href='javascript:void(0)' onclick='javascript:department.Open(" + c.DepartmentId + ")'>修改</a>");
                    });

                    $("tfoot", "#tblDepartmentList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.Departmentlist").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: department.List,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblDepartmentList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },
 

    /*创建部门*/
    Open: function(departmentId) {

        var url =  AP_ROOT + AP_PAGE_ID + "/HR/Department/Department";
        var data = {
            departmentId: departmentId
        };
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#departmentModal').modal({ backdrop: 'static', keyboard: false });
            $('#departmentModal').on('hidden.bs.modal', function () {
                $("#departmentModal").remove();
            });
        });

        //$('.department').load(url, data, function(result) {
        //    $.closeLoading();
        //    $('#departmentModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    Close: function() {
        $('#departmentModal').modal('hide');
    },

    CreateUpdate: function() {

        if ($("#Department_DepartmentName").val() == '') {
            $.showModalMessageBox("请输入部门名称.");
            return false;
        }

        if ($("#Department_DepartmentCode").val() == '') {
            $.showModalMessageBox("请输入部门代码.");
            return false;
        }

        var data = {};

        data["Department.DepartmentId"] = $("#Department_DepartmentId").val();
        data["Department.ParentDepartmentId"] = $("#Department_ParentDepartmentId").val();
        data["Department.DepartmentCode"] = $("#Department_DepartmentCode").val();
        data["Department.DepartmentName"] = $("#Department_DepartmentName").val();

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/HR/Department/DepartmentCreateUpdate", data, function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                department.Close();
                department.List();
            } else {
                ;
                $.showModalMessageBox(response.Message);
            }
        });
    },
}

$(document).ready(function () {

    department.List();

    $(document).off('click', '.DepartmentCreate').on('click', '.DepartmentCreate', function () {
        department.Open();
    });

    $(document).off('click', '#btnDepartmentCreate').on('click', '#btnDepartmentCreate', function () {
        department.Open();
    });

    $(document).off('click', '#btnDepartmentClose').on('click', '#btnDepartmentClose', function () {
        department.Close();
    });

    $(document).off('click', '#btnDepartmentCancel').on('click', '#btnDepartmentCancel', function () {
        department.Close();
    });

    $(document).off('click', '#btnDepartment').on('click', '#btnDepartment', function () {
        department.CreateUpdate();
    });

});


