/*案件批量处理*/

function AssociateCustomer(div, ctlid, ctlname) {
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;

    this.Customer = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }
        var curobj = new Object();
        curobj.keyword = name;
        $.ajaxPost(AP_ROOT + "CRM/Customer/CustomerList", curobj, function (response) {
            $(div).find(".i_common_list").empty();
            if (response.IsSuccess) {
                if (response.Data) {
                    var html = "";
                    $.each(response.Data.Customers, function (i, c) {
                        html += '<a href="javascript:void(0)" customerid=' + c.CustomerId + ' >' + c.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("customerId"));
                        $(ctlname).val($(this).text());
                        $(div).hide();
                    });
                }
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        }, false);

        $(div).css({
            "position": "absolute",
            "left": $(ctlname).position().left + 15,
            "top": $(ctlname).position().top + 110
        }).toggle();
    }

    $(ctlname).bind('keyup', { obj: this }, function (event) {
        if (event.keyCode == 38) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).prev().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).prev().addClass("hover");
                        $(hover).prev().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 40) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).next().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).next().addClass("hover");
                        $(hover).next().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 13) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    $(hover).click();
                }
            }
        } else {
            clearTimeout(event.data.obj.Event);
            event.data.obj.Event = setTimeout(function () { event.data.obj.Customer(event.data.obj); }, 500);
        }
    });

    $(ctlname).bind('blur', { obj: this }, function (event) {
        if ($(this).val() == "" || ($(this).val() == $(this).attr("mod-notice-tip"))) {
            event.data.obj.GlobalName = "";
            $(ctlid).val("");
        }
        if ($(ctlid).val() == "") {
            if ($(this).attr("mod-notice-tip")) {
                $(this).val($(this).attr("mod-notice-tip"));
            } else {
                $(this).val("");
            }
        }
        //        if (event.data.obj.GlobalName != "") {
        //            $(this).val(event.data.obj.GlobalName);
        //            $(ctlid).val(event.data.obj.GlobalID);
        //        }
    });

    return this;
}

var caseFeeList = {

    Open: function (caseId) {
        if (caseId == undefined) {
            var url = AP_ROOT + "IPR/Case/CreateUpdate?typeId=1";
            window.location = url;
        } else {
            var url = AP_ROOT + "IPR/Case/CreateUpdate?CaseId=" + caseId;
            window.open(url);
        }
    },

    List: function() {
        $("#postForm").ajaxPost(AP_ROOT + "IPR/CaseFee/CaseFees", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseFeeList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseFeeList, function (i, c) {

                        $("tbody", "#tblCaseFeeList").addRow(
                            "<input type='checkbox' name='chkCaseFeeItemId' class='ng-pristine ng-valid' value='" + c.FeeItemId + "'>",
                            "<a href='javascript:void(0)' onclick='javascript:caseFeeList.Open(" + c.CaseId + ")'>" + c.CaseNo + "</a>",
                            c.CaseRequestNo,
                            c.FeeTypeName,
                            c.IsFeeMitigation ? '是' : '否',
                            c.Amount,
                            c.RequestUserName,
                            c.ResponseUserName,
                            c.InformDate == null ? '' : getDate(convertJsonDateToJSDate(c.InformDate)),
                            c.BillDate == null ? '' : getDate(convertJsonDateToJSDate(c.BillDate)),
                            c.GainedDate == null ? '' : getDate(convertJsonDateToJSDate(c.GainedDate)),
                            c.BillNo,
                            c.PaymentBank);
                    });

                    $("tfoot", "#tblCaseFeeList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.caseFeeList").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseFeeList.List,
                        callBackArgs: null
                    });


                } else {
                    $("tfoot", "#tblCaseFeeList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    Selected: function(e) {

        if ($(e).attr("checked") == "checked") {
            $.checkbox.all("chkCaseFeeItemId");
        } else {
            $.checkbox.not("chkCaseFeeItemId");
        }
    },

    /*批量导入open*/
    CaseFeeListBillConfirm: function () {
        var caseFeeItemIds = $.checkbox.vals("chkCaseFeeItemId");
        if (caseFeeItemIds.length == 0) {
            $.showModalMessageBox("请选择费用记录.");
            return false;
        }

        var data =
        {
            caseFeeItemIds: caseFeeItemIds
        };

        var url = AP_ROOT + "IPR/CaseFee/CaseFeeListBillConfirm";
        $.openLoading();

        $("<div></div>").load(url, data, function(result) {
            $.closeLoading();
            $(document.body).append(result);
            $('#caseFeeListBillConfirmModal').modal({ backdrop: 'static', keyboard: false });
            $('#caseFeeListBillConfirmModal').on('hidden.bs.modal', function () {
                $("#caseFeeListBillConfirmModal").remove();
            });
        });
    },

    /*批量导入关闭*/
    CaseFeeListBillConfirmClose: function () {
        $('#caseFeeListBillConfirmModal').modal('hide');
    },

    /*批量导入*/
    CaseFeeListBillConfirmCreate: function () {

        if ($("#BillNo").val() == '') {
            $.showModalMessageBox("请输入票据编号.");
            return false;
        }

        //if ($("#BillAmount").val() == '') {
        //    $.showModalMessageBox("请输入票据金额.");
        //    return false;
        //}

        if ($("#BillDate").val() == '') {
            $.showModalMessageBox("请输入票据日期.");
            return false;
        }

        if ($("#flBillFile").val() == '') {
            $.showModalMessageBox("请选择上传文件.");
            return false;
        }

        $.openLoading();
        $('#caseFeeListBillConfirm').ajaxSubmit({
            success: function (response) {
                $.closeLoading();
                if (response.IsSuccess) {
                    $.showModalMessageBox("费用确认成功.");
                    $('#caseFeeListBillConfirmModal').modal('hide');
                    caseFeeList.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            }
        });
    },
}

$(document).ready(function () {

    $(document).click(function (e) {
        $("#divCasePhaseCheckBoxList").die().hide();
        $("#divUserList").die().hide();
    });

    $("#chkCaseFeeItemAll").die().live("click", function () {
        caseFeeList.Selected(this);
    });

    $("#btnCaseFeeSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(30);

        caseFeeList.List();
    });

    $("#SearchCondition_CasePhaseName").die().live("click", function () {
        var tirgger = this;
        var html = $.casePhase.getCasePhaseCheckBoxListHtml();
        $(".divcaseconditioncasephases").html(html);
        $("#hidCasePhaseId").val("SearchCondition_CasePhaseId");
        $("#hidCasePhaseName").val($(tirgger).attr("id"));
        $("#divCasePhaseCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 15,
            "top": $(tirgger).position().top + 110
        }).toggle();

        return false;
    });

    $("#btnCaseFeeListBillConfirmCancel,#btnCaseFeeListBillConfirmClose").die().live("click", function () {
        caseFeeList.CaseFeeListBillConfirmClose();
    });

    $("#btnCaseFeeListBillConfirmCreate").die().live("click", function () {
        caseFeeList.CaseFeeListBillConfirmCreate();
    });

    $("#btnCaseFeeListBillConfirm").die().live("click", function () {
        caseFeeList.CaseFeeListBillConfirm();
    });

    $("#divCasePhaseCheckBoxList").find("li").die().live("click", function (e) {

        if ($(e.target).is("lable")) {
            e.stopPropagation();
            return false;
        }

        var currentSelectedControl = $("#hidCasePhaseName").val();
        var currentSelectedIdControl = $("#hidCasePhaseId").val();

        if ($(this).attr("id") == 'btnAllUnSelected') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }
        else if ($(this).attr("id") == 'btnAllSelected') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }

        $("#" + currentSelectedControl).val('');
        $("#" + currentSelectedIdControl).val('');

        var casePhaseNames = '';
        var casePhaseIds = '';

        $("#divCasePhaseCheckBoxList").find("input:checkbox").each(function () {
            if ($(this).attr("checked") == 'checked') {
                casePhaseNames += $(this).attr("casephasename") + ",";
                casePhaseIds += $(this).attr("casephaseid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(casePhaseNames.substring(0, casePhaseNames.length - 1));
        $("#" + currentSelectedIdControl).val(casePhaseIds.substring(0, casePhaseIds.length - 1));

        e.stopPropagation();

        return true;
    });

    $("#flBillFile").die().live("change", function () {
        $("#txtBillFilePath").val($("#flBillFile").val());
    });

});


