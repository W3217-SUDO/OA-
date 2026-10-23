function AssociateCustomer(div, ctlid, ctlname) {
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;

    this.Customer = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }
        var curobj = new Object();
        curobj.keyword = name;
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CustomerList", curobj, function (response) {
            $(div).find(".i_common_list").empty();
            if (response.IsSuccess) {
                if (response.Data) {
                    var html = "";
                    $.each(response.Data.Customers, function (i, c) {
                        html += '<a href="javascript:void(0)" customerid=' + c.CustomerBasic.CustomerId + ' >' + c.CustomerBasic.CustomerName + '</a>';
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

var caseFee = {

    Open: function (caseId, caseNo) {

        var search = {};

        search.CaseId = 0;
        search.PageId = 1;
        search.PageNo = 1;
        search.PageSize = 100;
        search.PageName = "案件查看";
        search.Keyword = caseNo;

        var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CreateUpdate?typeId=1&caseId=" + caseId + "&k=" + escape(JSON.stringify(search));

        window.open(url);
    },

    List: function() {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFee/CaseFees", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseFeeList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseFeeList, function(i, c) {

                        $("tbody", "#tblCaseFeeList").addRow(
                            "<input type='checkbox' name='chkCaseFeeId' customerid='" + + c.CustomerId + "' value='" + c.CaseFeeId + "'>",
                            "<a href='javascript:void(0)' onclick='javascript:caseFee.Open(" + c.CaseId + ",\"" + c.CaseNo + "\")'>" + c.CaseNo + "</a>",
                            c.CaseRequestNo,
                            c.CustomerName,
                            c.CaseFeeTypeName,
                            c.Amount,
                            c.RequestUserName,
                            c.InformDate == null ? '' : getDate(convertJsonDateToJSDate(c.InformDate)),
                            c.CashedResponseUserName,
                            c.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.CashedDate)),
                            c.PaymentModeName);
                    });

                    $("tfoot", "#tblCaseFeeList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.caseFeeList").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseFee.List,
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

        if ($(e).prop("checked") == true) {
            $.checkbox.all("chkCaseFeeId");
        } else {
            $.checkbox.not("chkCaseFeeId");
        }
    },

    InvoiceFile:
    {
        /*批量导入open*/
        Open: function () {

            var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
            if (caseFeeIds.length == 0) {
                $.showModalMessageBox("请选择费用记录.");
                return false;
            }

            var customerIds = new Array();

            $("input[name='chkCaseFeeId']:checked").each(
                function () {
                    if ($.inArray($(this).attr("customerid"), customerIds) > -1) {
                    } else {
                        customerIds.push($(this).attr("customerid"));
                    }
                }
            );

            if (customerIds.length > 1) {
                $.showModalMessageBox("客户不一致.");
                return false;
            }

            var data =
            {
                caseFeeIds: caseFeeIds,
                caseClassType: $("#SearchCondition_CaseClassType").val(),
                invoiceType: $("#SearchCondition_InvoiceType").val()
            };

            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/InvoiceFile/CaseFeeInvoiceConfirm";
            $.openLoading();

            $("<div></div>").load(url, data, function(result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseFeeInvoiceConfirmModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseFeeInvoiceConfirmModal').on('hidden.bs.modal', function () {
                    $("#caseFeeInvoiceConfirmModal").remove();
                });
            });
        },

        /*批量导入关闭*/
        Close: function() {
            $('#caseFeeInvoiceConfirmModal').modal('hide');
        },

        /*批量导入*/
        Confirm: function() {
            if ($("#Invoice_InvoiceNo").val() == '') {
                $.showModalMessageBox("请输入票据编号.");
                return false;
            }

            if ($("#Invoice_InvoiceDate").val() == '') {
                $.showModalMessageBox("请输入票据日期.");
                return false;
            }

            if ($("#flInvoiceFile").val() == '') {
                $.showModalMessageBox("请选择上传文件.");
                return false;
            }

            ////专利发票不需要付款方式,付款人
            //if ($("#CaseClassType").val() == 'Patent' && $("#InvoiceType").val() == 'Invoice') {

            //} else {
            //    if ($("#PaymentMode").val() == '') {
            //        $.showModalMessageBox("付款方式.");
            //        return false;
            //    }

            //    if ($("#PayerName").val() == '') {
            //        $.showModalMessageBox("付款人.");
            //        return false;
            //    }
            //}

            $.openLoading();
            $('#caseFeeInvoiceConfirm').ajaxSubmit({
                success: function(response) {
                    $.closeLoading();
                    if (response.IsSuccess) {
                        $.showModalMessageBox("票据确认成功.");
                        $('#caseFeeInvoiceConfirmModal').modal('hide');
                        caseFee.List();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                }
            });
        },
    },
}

$(document).ready(function () {

    $(document).click(function (e) {
        $("#divCasePhaseCheckBoxList").off().hide();
        $("#divCaseFeeTypeCheckBoxList").off().hide();
        $("#divUserList").off().hide();
    });

    $("#chkCaseFeeAll").off().on("click", function () {
        caseFee.Selected(this);
    });

    $("#btnCaseFeeSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(30);

        caseFee.List();
    });

    $("#divUsers").find("li").off().on("click", function () {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();
        $("#" + currentSelectedControl).val(userName);
        $("#" + currentSelectedIdControl).val(userId);
        $("#divUsers").hide();
    });

    $("#PayerName").off().on("click", function () {
        $("#hidUserId").val("Payer");
        $("#hidUserName").val("PayerName");

        $("#divUsers").css({
            "position": "absolute",
            "left": $("#PayerName").offsetParent().position().left + 15,
            "top": $("#PayerName").offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        return false;
    });

    $("#SearchCondition_CasePhaseName").off().on("click", function () {
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

    $("#btnCaseFeeInvoiceConfirmCancel,#btnCaseFeeInvoiceConfirmClose").off().on("click", function () {
        caseFee.InvoiceFile.Close();
    });

    $("#btnCaseFeeInvoiceConfirmCreate").off().on("click", function () {
        caseFee.InvoiceFile.Confirm();
    });

    $("#btnCaseFeeInvoiceConfirm").off().on("click", function () {
        caseFee.InvoiceFile.Open();
    });

    $("#divCasePhaseCheckBoxList").find("li").off().on("click", function (e) {

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

    $("#flInvoiceFile").off().on("change", function () {
        $("#txtInvoiceFilePath").val($("#flInvoiceFile").val());
    });

    $("#divCaseFeeTypeCheckBoxList").find("li").off().on("click", function (e) {

        if ($(e.target).is("lable")) {
            e.stopPropagation();
            return false;
        }

        var currentSelectedControl = $("#hidCaseFeeTypeName").val();
        var currentSelectedIdControl = $("#hidCaseFeeTypeId").val();

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

        var caseFeeTypeNames = '';
        var caseFeeTypeIds = '';

        $("#divCaseFeeTypeCheckBoxList").find("input:checkbox").each(function () {
            if ($(this).attr("checked") == 'checked') {
                caseFeeTypeNames += $(this).attr("casefeetypename") + ",";
                caseFeeTypeIds += $(this).attr("casefeetypeid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(caseFeeTypeNames.substring(0, caseFeeTypeNames.length - 1));
        $("#" + currentSelectedIdControl).val(caseFeeTypeIds.substring(0, caseFeeTypeIds.length - 1));

        e.stopPropagation();

        return true;
    });

    $("#SearchCondition_CaseFeeTypeName").off().on("click", function () {
        var tirgger = this;
        var html = $.caseFeeType.getCaseFeeTypeCheckBoxListHtml();
        $(".divcaseconditioncasefeetypes").html(html);
        $("#hidCaseFeeTypeId").val("SearchCondition_CaseFeeTypeId");
        $("#hidCaseFeeTypeName").val($(tirgger).attr("id"));
        $("#divCaseFeeTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 15,
            "top": $(tirgger).position().top + 110
        }).toggle();

        return false;
    });

});


