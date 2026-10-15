/*案件律所*/
var lawFirm = {
    List: function() {
        $("#postForm").ajaxPost(AP_ROOT + "IPR/LawFirm/List", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblLawFirmList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.LawFirms, function (i, c) {

                        $("tbody", "#tblLawFirmList").addRow(c.LawFirmNo, c.LawFirmName, c.RegisteredAddress, c.Zip,
                                        c.Telphone, c.Fax, c.Email, c.Country, c.CompanyCode,
                                        c.LawFirmCode, c.BusinessAddress,
                                        "<a href='javascript:void(0)' onclick='javascript:lawFirm.Open(" + c.LawFirmId + ")'>修改</a> &nbsp; &nbsp;&nbsp;" +
                                        "<a href='javascript:void(0)' onclick='javascript:lawFirm.ContactsList(" + c.LawFirmId + ")'>联系人管理</a>");
                        
                    });

                    $("tfoot", "#tblLawFirmList").show();
                    $(".simple-grid-none-data-wrap").hide();
                     
                    $(".pull-right.page-box.lawFirm").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: lawFirm.List,
                        callBackArgs: null
                    });
                } else {
                     
                    $("tfoot", "#tblLawFirmList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    /*创建律所*/
    Open: function (lawFirmId) {
         
        var data =
        {
            lawFirmId: lawFirmId,
        };
        var url = AP_ROOT + "IPR/LawFirm/CreateUpdate";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);
            $('#lawFirmModal').modal({ backdrop: 'static', keyboard: false });
            $('#lawFirmModal').on('hidden.bs.modal', function () {
                $("#lawFirmModal").remove();
            });
        });

        //$('.lawFirmCreateUpdate').load(url, data, function (result) {
        //    $.closeLoading();
        //    $('#lawFirmModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    /*律所联系人*/
    ContactsList: function (lawFirmId) {
        var data = {
            lawFirmId: lawFirmId
        };
        var url = AP_ROOT + "IPR/LawFirm/ContactsList";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);
            $('#contactsListModal').modal({ backdrop: 'static', keyboard: false });
            $('#contactsListModal').on('hidden.bs.modal', function () {
                $("#contactsListModal").remove();
            });
        });

        //$('.contactsList').load(url, data, function (result) {
        //    $.closeLoading();
        //    $('#contactsListModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    /*保存律所信息*/
    CreateUpdate: function () {
        if (!postValid()) {
            return false;
        }
        
        if ($("#flLicenseFile").val() == '') {
            $.showModalMessageBox("请选择上传文件.");
            return false;
        }

        $("#lawFirmForm").ajaxPost(AP_ROOT + "IPR/LawFirm/LawFirmCreateUpdate", function (response) {
            if (response.IsSuccess) {
                 
                $('#LawFirm_LawFirmId').val(response.Data.LawFirmId);
                $('#LawFirm_LawFirmNo').val(response.Data.LawFirmNo);
                $('#LawFirm_DefaultContacts_ContactsId').val(response.Data.DefaultContacts.ContactsId);
                $.showModalMessageBox("保存成功.");
                lawFirm.List();
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });

        return true;
    },

    /*关闭窗体*/
    Close: function () {
        $('#lawFirmModal').modal('hide');
    } ,
    
    License:
    {
        /*上传营业执照*/
        Open: function () {
            var data =
            {
                lawFirmId: $('#LawFirm_LawFirmId').val(),
                lawFirmNo: $('#LawFirm_LawFirmNo').val()
            };
             
            if ($('#LawFirm_LawFirmId').val() == '' || $('#LawFirm_LawFirmId').val() == "0") {
                $.showModalMessageBox("请先保存律所基本资料，再上传.");
                return false;
            }

            var url = AP_ROOT + "IPR/LawFirm/License";

            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#licenseModal').modal({ backdrop: 'static', keyboard: false });
                $('#licenseModal').on('hidden.bs.modal', function () {
                    $("#licenseModal").remove();
                });
            });
        },

        /*上传*/
        Upload: function () {
            $('#uploadingForm').ajaxSubmit({
                success: function (response) {
                    debugger
                    $("#imgLicense").attr("src", response.Data);
                    $.showModalMessageBox("保存成功.");
                    $('#licenseModal').modal('hide');
                }
            });
        },

        /*关闭律所窗体*/
        Close: function () {
            $('#licenseModal').modal('hide');
        }
    },
}

$(document).ready(function () {


    $(".lawFirmCreate").click(function () {
         
        lawFirm.Open();
    });

    $("#btnLawFirmCreate").click(function () {
        lawFirm.Open();
    });

    $("#btnCancle").die().live("click", function () {
         
        lawFirm.Close();
    });

    $("#btnClose").die().live("click", function () {
        lawFirm.Close();
    });

    $("#btnCreateUpdate").die().live("click", function () {
        lawFirm.CreateUpdate();
    });

    $("#flLicenseFile").die().live("change", function () {
        $("#txtLicenseFilePath").val($("#flLicenseFile").val());
    });

    //
    $("#btnLicenseUploading").die().live("click", function () {
        lawFirm.License.Open();
    });

    $("#btnUploadingCanel").die().live("click", function () {
        lawFirm.License.Close();
    });

    $("#btnUploadingClose").die().live("click", function () {
        lawFirm.License.Close();
    });

    $("#btnUploading").die().live("click", function () {
        lawFirm.License.Upload();
    });

    $("#btnLawFirmSearch").die().live("click", function () {
        lawFirm.List();
    });

});



function postValid() {

    //if (!CheckModifyTime()) return false;

    //判断必填项的项是否填写
    var flag = true;
    $("#tblLawFirm :text").each(function () {
        var value = $(this).val().trim();

        var desc;
        if ($(this).parent().prev().find("label")
            && $(this).parent().prev().find("label").html() != null) {
            desc = $(this).parent().prev().find("label").html().replace(":", "").replace("：", "");
        } else if ($(this).parent().parent().prev().find("label")
            && $(this).parent().parent().prev().find("label").html() != null) {
            desc = $(this).parent().parent().prev().find("label").html().replace(":", "").replace("：", "");
        }

        if ($(this).attr("required") == "required") {

            if (value == "") {
                flag = false;

                $.showModalMessageBox(desc + "不能为空");
                return false;
            }

            if ($(this).attr("func") && $(this).attr("func") != "") {
                var func = $(this).attr("func");

                var value = $(this).val();
                var that = $(this);
                var data = { func: func, value: value }

                $.ajaxSetup({
                    async: false
                });

                $.ajaxPost(AP_ROOT + "IntlFare/ValidAssociate", data, function (response) {
                    if (!response.IsSuccess) {

                        $.showModalMessageBox(desc + "不存在");

                        flag = false;
                        return false;
                    }
                });

                $.ajaxSetup({
                    async: true
                });
            }
        }
    });

    if (!flag) {
        return false;
    }

    if ($("#LawFirm_Email").val() != '') {
        var isEmail = /^\w+((-\w+)|(\.\w+))*\@[A-Za-z0-9]+((\.|-)[A-Za-z0-9]+)*\.[A-Za-z0-9]+$/;

        if (!isEmail.test($("#LawFirm_Email").val())) {
            $.showModalMessageBox("请填写正确律所邮箱.");
            return false;
        }
    }

    if ($("#LawFirm_ContactEmail").val() != '') {
        var isEmail = /^\w+((-\w+)|(\.\w+))*\@[A-Za-z0-9]+((\.|-)[A-Za-z0-9]+)*\.[A-Za-z0-9]+$/;

        if (!isEmail.test($("#LawFirm_ContactEmail").val())) {
            $.showModalMessageBox("请填写正确联系邮件.");
            return false;
        }
    }

    return true;
}


