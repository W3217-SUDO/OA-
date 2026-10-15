/*菜单*/
var menu = {

    List: function() {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemManagement/MenuList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblMenuList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.MenuList, function (i, c) {
                        $("tbody", "#tblMenuList").addRow(c.MenuId, c.MenuName,
                            "<a href='javascript:void(0)' onclick='javascript:menu.Open(" + c.MenuId + ")'>修改</a>");
                    });

                    $("tfoot", "#tblMenuList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.Menulist").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: menu.List,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblMenuList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    /*创建角色*/
    Open: function (menuId) {
         
        var url =  AP_ROOT + AP_PAGE_ID + "/System/SystemManagement/Menu";
        var data = {
            menuId: menuId
        };
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);
 
            $('#menuModal').modal({ backdrop: 'static', keyboard: false });
            $('#menuModal').on('hidden.bs.modal', function () {
                $("#menuModal").remove();
            });
        });

        //$('.menu').load(url, data, function (result) {
        //    $.closeLoading();
        //    $('#menuModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    Close: function() {
        $('#menuModal').modal('hide');
    },

    CreateUpdate: function () {

        if ($("#Menu_MenuName").val() == '') {
            $.showModalMessageBox("请输入菜单名称.");
            return false;
        }

        if ($("#Menu_Comments").val() == '') {
            $.showModalMessageBox("请输入菜单名称描述.");
            return false;
        }

        var data = {};

        data["Menu.MenuId"] = $("#MenuId").val();
        data["Menu.MenuName"] = $("#Menu_MenuName").val();
        data["Menu.Comments"] = $("#Menu_Comments").val();

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemManagementMenu/CreateUpdate", data, function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                menu.Close();
                menu.List();
            }
            else {
                ;
                $.showModalMessageBox(response.Message);
            }
        });
    },
 
}

$(document).ready(function () {

    menu.List();

    $(document).off('click', '.MenuCreate').on('click', '.MenuCreate', function () {
        menu.Open();
    });

    $(document).off('click', '#btnMenuCreate').on('click', '#btnMenuCreate', function () {
        menu.Open();
    });

    $(document).off('click', '#btnMenuClose').on('click', '#btnMenuClose', function () {
        menu.Close();
    });

    $(document).off('click', '#btnMenuCancel').on('click', '#btnMenuCancel', function () {
        menu.Close();
    });

    $(document).off('click', '#btnMenuAddItem').on('click', '#btnMenuAddItem', function () {
        menu.MenuItem.Add();
    });

    $(document).off('click', '.btn_clear').on('click', '.btn_clear', function () {
        menu.MenuItem.Clear(this);
    });

    $(document).off('click', '.btn_remove').on('click', '.btn_remove', function () {
        menu.MenuItem.Remove(this);
    });

    $(document).off('click', '#btnMenu').on('click', '#btnMenu', function () {
        menu.CreateUpdate();
    });
});


