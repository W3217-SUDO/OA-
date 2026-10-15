
var gl = {
    Init: function () {
        gl.AR.List();
    },

    ResetSize: function () {
        if ($("#divContextList").length > 0) {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 22);
        }
     },
 
    /*应收费用列表*/
    AR: {
        List: function () {
            var data = {
                contractId: $("#Contract_ContractBasicInfo_ContractId").val(),
                pageNo: $("#PageNo").val(),
                pageSize: $("#PageSize").val()
            };

            $.ajaxPost(AP_ROOT + "FCM/GL/ARCaseFeeList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#dv_List").empty();
                    $("#dv_List").html(response.Data);

                    $(".pull-right.page-box.arcasefeelist").cPaging({
                        totalCount: parseInt($("#TotalCount").val()),
                        pageNo: parseInt($("#PageNo").val()),
                        pageSize: parseInt($("#PageSize").val()),
                        callBack: gl.AR.List,
                        callBackArgs: null
                    });

                    var totalCount = parseInt($("#TotalCount").val());
                   
                    if (totalCount > 0) {
                        $("tfoot", "#tblARCaseFeeList").show();
                        $(".simple-grid-none-data-wrap").hide();
                    } else {
                        $("tfoot", "#tblARCaseFeeList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }

                    gl.ResetSize();

                    $.closeLoading();
                }
            }, true);
        },

        Invoice: {

            Open: function (caseFeeGuid) {
                var data = {
                    caseFeeGuid: caseFeeGuid,
                };

                var url = AP_ROOT + "FAM/InvoiceFile/List";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#invoiceFileListModal').modal({ backdrop: 'static', keyboard: false });
                    $('#invoiceFileListModal').on('hidden.bs.modal', function () {
                        $("#invoiceFileListModal").remove();
                    });
                });
            },
        },
    },

    /*应付费用列表*/
    AP: {

        Selected: function (e) {

            if ($(e).attr("checked") == "checked") {
                $.checkbox.all("chkCaseFeeId");
            } else {
                $.checkbox.not("chkCaseFeeId");
            }
        },

        List: function () {
            var data = {
                contractId: $("#Contract_ContractBasicInfo_ContractId").val(),
                pageNo: $("#PageNo").val(),
                pageSize: $("#PageSize").val()
            };

            $.ajaxPost(AP_ROOT + "FCM/GL/APCaseFeeList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#dv_List").empty();
                    $("#dv_List").html(response.Data);

                    $(".pull-right.page-box.apcasefeelist").cPaging({
                        totalCount: parseInt($("#TotalCount").val()),
                        pageNo: parseInt($("#PageNo").val()),
                        pageSize: parseInt($("#PageSize").val()),
                        callBack: gl.AP.List,
                        callBackArgs: null
                    });

                    var totalCount = parseInt($("#TotalCount").val());

                    if (totalCount > 0) {
                        $("tfoot", "#tblAPCaseFeeList").show();
                        $(".simple-grid-none-data-wrap").hide();
                    } else {
                        $("tfoot", "#tblAPCaseFeeList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }

                    gl.AP.BindMenu();

                    gl.ResetSize();

                    $.closeLoading();
                }
            }, true);
        },

        BindMenu: function () {
            $('#casegridSection').contextMenu('feeMenu', {
                menuStyle: {
                    width: '152px'
                },
                itemStyle: {
                    width: '150px'
                },
                bindings: {
                    'invoiceConfirm': function (t, e) {
                        gl.AP.Invoice.Open();
                    },
                    'view': function (t, e) {
                        debugger
                        var caseFeeId = $(e).find("span").text();
                        if (caseFeeId == '') {
                            $.showModalMessageBox("请选择查看的付款凭证文件.");
                            return false;
                        }

                        var caseFileName = $(e).find("lable").text();
                        if (caseFileName == '') {
                            $.showModalMessageBox("无付款凭证文件.");
                            return false;
                        }

                        var caseno = $(e).find("div").text();

                        var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                        var picfiles = new Array('jpg', 'tif', 'pdf');
                        var extName = caseFileName.substring(caseFileName.lastIndexOf('.') + 1, caseFileName.length);

                        if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                            var path = GV_IPR.OfficeOnlineUrl + GV_IPR.IPROnlineUrl + "CaseFeeFiles/" + caseno + "/" + caseFileName;
                            window.open(path);
                        }
                        else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                            var path = GV_IPR.IPROnlineUrl + "CaseFeeFiles/" + caseno + "/" + caseFileName;
                            window.open(path);
                        } else {
                            gl.AP.Invoice.Download(caseFeeId);
                        }

                        return true;
                    },
                    'download': function (t, e) {

                        var caseFileName = $(e).find("lable").text();
                        if (caseFileName == '') {
                            $.showModalMessageBox("无付款凭证文件.");
                            return false;
                        }

                        var feeId = $(e).find("span").html();
                        gl.AP.Invoice.Download(feeId);
                    },
                    'refresh': function (t, e) {
                        gl.AP.List();
                    },
                    'paymentapply': function (t, e) {
                        gl.AP.PaymentApply.Open();
                    }
                },
                onContextMenu: function (e) {
                    return true;
                },
                onShowMenu: function (e, menu) {
                    if ($(e.target).parents("tr").find(".feeId").hasClass("feeId")) {
                        var feeId = $(e.target).parents("tr").find("#item_CaseFeeId").val();
                        var feeGuid = $(e.target).parents("tr").find("#item_CaseFeeGuid").val();
                        var caseNo = $(e.target).parents("tr").find("#item_CaseNo").val();
                        var fileName = $(e.target).parents("tr").find("#item_Invoice_InvoiceFileName").val();

                        $('#invoiceConfirm', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#view', menu).append("<span style='display:none'>" + feeId + "</span><lable style='display:none'>" + fileName + "</lable><div style='display:none'>" + caseNo + "</div>");
                        $('#download', menu).append("<span style='display:none'>" + feeId + "</span><lable style='display:none'>" + fileName + "</lable><div style='display:none'>" + caseNo + "</div>");
                        $('#paymentapply', menu).append("<span style='display:none'>" + feeId + "</span>");


                    } else {
                        $('#view,#download', menu).remove();
                        $('#invoiceConfirm', menu).remove();
                        $('#paymentapply', menu).remove();
                    }
                    return menu;
                }
            });
        },

        Invoice: {

            /*案件票据确认*/
            Open: function () {

                if (parseInt($("#CaseId").val()) == 0) {
                    $.showModalMessageBox("请先保存案件基本资料.");
                    return false;
                }
                var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
                if (caseFeeIds.length == 0) {
                    $.showModalMessageBox("请选择需要确认的应付款.");
                    return false;
                }


                var caseTypeIds = new Array('4');

                if ($.inArray($("#Case_CaseBasicInfo_CaseTypeId").val(), caseTypeIds) > -1) {

                    var caseFeeTypeIds = new Array('51', '52', '53');
                    var caseTypeName = $("#Case_CaseBasicInfo_CaseTypeId").find("option:selected").text();

                    var result = true;
                    $("input[name='chkCaseFeeId']:checked").each(
                        function (i) {
                            if ($.inArray($(this).attr("casefeetypeid"), caseFeeTypeIds) <= -1) {
                                $.showModalMessageBox(caseTypeName + "案件不允上传" + $(this).attr("casefeetypename") + "的付款凭证.");
                                result = false;
                                return false;
                            }
                        }
                    );

                    if (!result) return false;
                }


                var data =
                {
                    caseId: $("#CaseId").val(),
                    caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
                    caseTypeId: $("#Case_CaseBasicInfo_CaseTypeId").val(),
                    caseFeeIds: caseFeeIds
                };

                var url = AP_ROOT + "IPR/APCaseFee/CaseFeeInvoiceConfirm";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#caseFeeInvoiceConfirmModal').modal({ backdrop: 'static', keyboard: false });
                    $('#caseFeeInvoiceConfirmModal').on('hidden.bs.modal', function () {
                        $("#caseFeeInvoiceConfirmModal").remove();
                    });
                });

            },

            Close: function () {
                $('#caseFeeInvoiceConfirmModal').modal('hide');
            },

            CreateUpdate: function () {

                if ($("#DefaultCaseFee_InvoiceNo").val() == '') {
                    $.showModalMessageBox("请输入付款票据号.");
                    return false;
                }

                if ($("#DefaultCaseFee_InvoiceAmount").val() == '') {
                    $.showModalMessageBox("请输入付款金额.");
                    return false;
                }

                if ($("#DefaultCaseFee_InvoiceDate").val() == '') {
                    $.showModalMessageBox("请输入付款日期.");
                    return false;
                }

                if ($("#flInvoiceFile").val() == '') {
                    $.showModalMessageBox("请选择付款凭证文件.");
                    return false;
                }

                $.openLoading();
                $('#caseFeeInvoiceConfirm').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $.showModalMessageBox("保存成功.");
                            $('#caseFeeInvoiceConfirmModal').modal('hide');

                            gl.AP.List();
                            caseInfo.CaseEvent.List();

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    }
                });
            },

            View: function () {

            },

            Download: function (caseFeeId) {
                window.open(AP_ROOT + "IPR/CaseFileCenter/APCaseFeeFileDownload?caseFeeId=" + caseFeeId);
                return true;
            },
        },

        PaymentApply: {
            /*垫付款申请*/
            Open: function () {

                var caseFeeIds = $.checkbox.vals("chkCaseFeeId");

                if (caseFeeIds.length == 0) {
                    $.showModalMessageBox("请选择付款记录.");
                    return false;
                }
                var data =
                {
                    caseFeeIds: $.checkbox.vals("chkCaseFeeId")
                };

                var url = AP_ROOT + "IPR/APCaseFee/PaymentApply";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#paymentApplyModal').modal({ backdrop: 'static', keyboard: false });
                    $('#paymentApplyModal').on('hidden.bs.modal', function () {
                        $("#paymentApplyModal").remove();
                    });
                });
            },

            Close: function () {
                $('#paymentApplyModal').modal('hide');
            },

            Apply: function () {
                /*垫付款申请*/

                var data =
                {
                    caseFeeIds: $.checkbox.vals("chkCaseFeeId"),
                    remark: $("#Remark").val()
                };
                $.ajaxPost(AP_ROOT + "IPR/APCaseFee/PaymentApplyCreate", data, function (response) {
                    if (response.IsSuccess) {
                        gl.AP.List();
                        gl.AP.PaymentApply.Close();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },

            Cancel: function () {

            },

            Audit: {
                Open: function (applicationId) {
                    var data =
                    {
                        applicationId: applicationId,
                    };

                    var url = AP_ROOT + "FAM/AP/CaseFeeApplicationAuditList";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#caseFeeApplicationAuditListModal').modal({ backdrop: 'static', keyboard: false });
                        $('#caseFeeApplicationAuditListModal').on('hidden.bs.modal', function () {
                            $("#caseFeeApplicationAuditListModal").remove();
                        });
                    });
                },
                Close: function () {
                    $('#caseFeeApplicationAuditListModal').modal('hide');
                },
            }
        }

    },
};
 

$(document).ready(function() {

    $(window).resize(function () {
        gl.ResetSize();
    });

    $(document).click(function() {

    });

    $("#chkCaseAPListAll").die().live("click", function () {
        gl.AP.Selected(this);
    });

    $(function() {
        $('.viewFramework-product-body').slimScroll({
            height: '100%'
        });
    });

    $("#btnARCaseFeeList").click(function () {

        $("#liARCaseFeeList").removeClass("active");
        $("#liAPCaseFeeList").removeClass("active");
        $("#liCaseFeeInvoiceList").removeClass("active");

        $("#liARCaseFeeList").addClass("active");

        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(15);
        }

        gl.AR.List();
    });

    $("#btnAPCaseFeeList").click(function () {

        $("#liARCaseFeeList").removeClass("active");
        $("#liAPCaseFeeList").removeClass("active");
        $("#liCaseFeeInvoiceList").removeClass("active");

        $("#liAPCaseFeeList").addClass("active");

        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(15);
        }

        gl.AP.List();
    });

    $("#btnCaseFeeInvoiceList").click(function () {

        $("#liARCaseFeeList").removeClass("active");
        $("#liAPCaseFeeList").removeClass("active");
        $("#liCaseFeeInvoiceList").removeClass("active");

        $("#liCaseFeeInvoiceList").addClass("active");

        //if ($("#PageNo").length) {
        //    $("#PageNo").val(1);
        //    $("#PageSize").val(15);
        //}

        gl.Invoice.List();

    });

    //预付款申请
    $("#btnPaymentApply").die().live("click", function () {
        gl.AP.PaymentApply.Apply();
    });

    $("#btnPaymentApplyClose,#btnPaymentApplyCancel").die().live("click", function () {
        gl.AP.PaymentApply.Close();
    });

    $("#btnCaseFeeApplicationAuditListCancel,#btnCaseFeeApplicationAuditListClose").die().live("click", function () {
        gl.AP.PaymentApply.Audit.Close();
    });

    gl.Init();
});