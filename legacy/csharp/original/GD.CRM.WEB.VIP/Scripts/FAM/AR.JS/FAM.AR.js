function AssociateCustomer(div, ctlid, ctlname, ctlcustomername) {
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
                        html += '<a href="javascript:void(0)" customerno=' + c.CustomerBasic.CustomerNo + ' >' + c.CustomerBasic.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("customerNo"));
                        $(ctlname).val($(this).text());
                        $(ctlcustomername).val($(this).text());

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
            "left": $(ctlname).parents().position().left,
            "top": $(ctlname).parents().position().top + 30
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
                //$(this).val("");
            }
        }
        //        if (event.data.obj.GlobalName != "") {
        //            $(this).val(event.data.obj.GlobalName);
        //            $(ctlid).val(event.data.obj.GlobalID);
        //        }
    });

    return this;
}

 
var payment = {
    ResetSize: function() {
        if ($("#divContextList").length > 0) {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 22);
        }
    },

    Payment: {
        ViewContract: function(contractId) {
            var url =  AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractView?contractId=" + contractId;
            window.open(url);
        },

        Create: function (contractId) {
            var url =  AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentCreate?contractId=" + contractId;
            window.open(url);
        },
        View: function(paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentView?paymentId=" + paymentId;
            window.open(url);
        },
        Edit: function(paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentEdit/?paymentId=" + paymentId;
            window.open(url);
        },

        Apply: function (paymentId)
        {
            var url = AP_ROOT + "FAM/AR/PaymentApply/" + paymentId;
            window.open(url);
        },

        Applied: function (paymentId) {
            var url = AP_ROOT + "FAM/AR/PaymentApplied/" + paymentId;
            window.open(url);
        },

        Push: function (paymentId)
        {
            var url = AP_ROOT + "FAM/AR/PaymentPush/" + paymentId;
            window.open(url);
        },
        
        PaymentApply: function()
        {
            var dataIsNOk = false;

            var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
            if (caseFeeIds.length == 0) {
                $.showModalMessageBox("请选择未分配的费用信息.");
                return false;
            }

            var data = {};

            data["Payment.PaymentBasic.PaymentId"] = $("#Payment_PaymentBasic_PaymentId").val();

            var i = 0;

            $("#tblARObjectList>tbody>tr").each(function (j, e) {
                if ($(e).css("display") != 'none' && $(e).find("#chkCaseFeeId").length > 0) {
 
                    if ($(e).find("#chkCaseFeeId").attr("checked") == "checked" && $(e).find("#item_CaseFeePayAmount").val() == '0') {
                        dataIsNOk = true;
                        $.showModalMessageBox("第" + (j) + "行,请录入本次回款金额.");
                        return false;
                    }

                    if ($(e).find("#chkCaseFeeId").attr("checked") == "checked")
                    {
                        data["Payment.PaymentObjects[" + i + "].CaseId"] = $(e).find("#chkCaseFeeId").attr("caseId");
                        data["Payment.PaymentObjects[" + i + "].CaseNo"] = $(e).find("#chkCaseFeeId").attr("caseNo");
                        data["Payment.PaymentObjects[" + i + "].CaseFeeId"] = $(e).find("#chkCaseFeeId").attr("caseFeeId");
                        data["Payment.PaymentObjects[" + i + "].CaseFeePayAmount"] = $(e).find("#item_CaseFeePayAmount").val();

                        i++;
                    }
                }
            });

            if (dataIsNOk) return false;
            $.ajaxPost(AP_ROOT + "FAM/ReceivedPayment/PaymentApply", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("回款分配成功.");
                    payment.Payment.Objects.List();
                    $("#Payment_PaymentBasic_AppliedAmount").text(response.Data.PaymentBasic.AppliedAmount);
                    $("#Payment_PaymentBasic_UnAppliedAmount").text(response.Data.PaymentBasic.UnAppliedAmount);

                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
   
        },

        PaymentAppliedCancel: function () {
            var dataIsNOk = false;
            var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
            if (caseFeeIds.length == 0) {
                $.showModalMessageBox("请选择已分配的费用信息.");
                return false;
            }

            var data = {};
            data["Payment.PaymentBasic.PaymentId"] = $("#Payment_PaymentBasic_PaymentId").val();
            var i = 0;
            $("#tblARObjectList>tbody>tr").each(function (j, e) {
                if ($(e).css("display") != 'none' && $(e).find("#chkCaseFeeId").length > 0) {
 
                    if ($(e).find("#chkCaseFeeId").attr("checked") == "checked")
                    {
                        data["Payment.PaymentObjects[" + i + "].SeqId"] = $(e).find("#chkCaseFeeId").attr("seqId");
                        data["Payment.PaymentObjects[" + i + "].CaseId"] = $(e).find("#chkCaseFeeId").attr("caseId");
                        data["Payment.PaymentObjects[" + i + "].CaseNo"] = $(e).find("#chkCaseFeeId").attr("caseNo");
                        data["Payment.PaymentObjects[" + i + "].CaseFeeId"] = $(e).find("#chkCaseFeeId").attr("caseFeeId");
                        i++;
                    }
                }
            });

            if (dataIsNOk) return false;
            $.ajaxPost(AP_ROOT + "FAM/ReceivedPayment/PaymentAppliedCancel", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("回款取消分配成功.");
                    payment.Payment.Objects.AppliedList();
                    $("#Payment_PaymentBasic_AppliedAmount").text(response.Data.PaymentBasic.AppliedAmount);
                    $("#Payment_PaymentBasic_UnAppliedAmount").text(response.Data.PaymentBasic.UnAppliedAmount);

                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        TotalAmountSet: function() {
            var totalAmount = 0;
            $("input[name='item_CaseOfficeFeeCashAmount']").each(
                function() {
                    if ($(this).val() == '') {
                        $(this).val(0);
                    }
                    totalAmount += parseFloat($(this).val());
                }
            );
            $("input[name='item_CaseNonOfficeFeeCashAmount']").each(
                function() {
                    if ($(this).val() == '') {
                        $(this).val(0);
                    }
                    totalAmount += parseFloat($(this).val());
                }
            );
            $("input[name='item_CaseCommissionFeeCashAmount']").each(
                function() {
                    if ($(this).val() == '') {
                        $(this).val(0);
                    }
                    totalAmount += parseFloat($(this).val());
                }
            );

            var totalAmount = totalAmount + ($("#Payment_PaymentBasic_PrePaidAmount").val() == '' ? 0 : parseFloat($("#Payment_PaymentBasic_PrePaidAmount").val()));
           // $("#Payment_PaymentBasic_CashedAmount").val(totalAmount);

            $("input[name='Payment.PaymentBasic.CashedAmount']").each(
                function () {
                    $(this).val(totalAmount);
                }
            );

            //$("#Payment_PaymentBasic_TotalAmount").val(totalAmount);
        },

        Registration : {
            CreateUpdate: function(isCreateNextOne) {
                try {

                    if ($("#Payment_PaymentBasic_PayerName").val() == '') {
                        $.showModalMessageBox("请输入回款单位.");
                        return false;
                    }

                    if ($("#Payment_PaymentBasic_CashedAmount").val() == '' || parseFloat($("#Payment_PaymentBasic_CashedAmount").val()) == 0) {
                        $.showModalMessageBox("回款金额不能为零.");
                        return false;
                    }

                    if ($("#Payment_PaymentBasic_PaymentModeName").val() == '') {
                        $.showModalMessageBox("请输入回款方式.");
                        return false;
                    }

                    if ($("#Payment_PaymentBasic_InvoiceNo").val() == '') {
                        $.showModalMessageBox("请输入银行单号.");
                        return false;
                    }

                    var data = {};

                    data["Payment.PaymentBasic.PaymentId"] = $("#Payment_PaymentBasic_PaymentId").val();
                    data["Payment.PaymentBasic.PayerName"] = $("#Payment_PaymentBasic_PayerName").val();
                    data["Payment.PaymentBasic.SequenceNo"] = $("#Payment_PaymentBasic_SequenceNo").val();
                    data["Payment.PaymentBasic.CustomerNo"] = $("#Payment_PaymentBasic_CustomerNo").val();
                    data["Payment.PaymentBasic.CustomerName"] = $("#Payment_PaymentBasic_CustomerName").val();
                    data["Payment.PaymentBasic.CashedDate"] = $("#Payment_PaymentBasic_CashedDate").val();
                    data["Payment.PaymentBasic.CashedAmount"] = $("#Payment_PaymentBasic_CashedAmount").val();
                    data["Payment.PaymentBasic.PaymentMode"] = $("#Payment_PaymentBasic_PaymentMode").val();
                    data["Payment.PaymentBasic.PaymentModeName"] = $("#Payment_PaymentBasic_PaymentModeName").val();
                    data["Payment.PaymentBasic.InvoiceNo"] = $("#Payment_PaymentBasic_InvoiceNo").val();
                    data["Payment.PaymentBasic.ContractNo"] = $("#Payment_PaymentBasic_ContractNo").val();

                    data["Payment.PaymentBasic.Remark"] = $("#Payment_PaymentBasic_Remark").val();
 
                    $.ajaxPost(AP_ROOT + "FAM/ReceivedPayment/PaymentCreateUpdate", data, function (response) {
                        if (response.IsSuccess) {

                            $.showModalMessageBox("提交成功");

                            if (isCreateNextOne) {
                                window.location = AP_ROOT + "FAM/AR/PaymentCreate";
                            }
                            else {
                                window.location = AP_ROOT + "FAM/AR/PaymentList/5001002002";
                            }

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            Push: function () {
                try {

                    if ($("#Payment_PaymentBasic_CustomerName").val() == '') {
                        $.showModalMessageBox("请输入客户关键字,选取客户.");
                        return false;
                    }

                    if ($("#Payment_PaymentBasic_CustomerNo").val() == '') {
                        $.showModalMessageBox("请输入客户关键字,选取客户.");
                        return false;
                    }

                    $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentCreateUpdate", data, function(response) {

                    data["Payment.PaymentBasic.PaymentId"] = $("#Payment_PaymentBasic_PaymentId").val();
                    data["Payment.PaymentBasic.CustomerNo"] = $("#Payment_PaymentBasic_CustomerNo").val();
                    data["Payment.PaymentBasic.ContractNo"] = $("#Payment_PaymentBasic_ContractNo").val();
                    data["Payment.PaymentBasic.CustomerName"] = $("#Payment_PaymentBasic_CustomerName").val();
                    data["Payment.PaymentBasic.ReceivedRemark"] = $("#Payment_PaymentBasic_ReceivedRemark").val();

                    $.ajaxPost(AP_ROOT + "FAM/ReceivedPayment/PaymentPush", data, function (response) {
                        if (response.IsSuccess) {
                            $.showModalMessageBox("提交成功.");
                            window.location = AP_ROOT + "FAM/AR/PaymentApply/" + $("#Payment_PaymentBasic_PaymentId").val();
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            CreateUpdateCallBack: function(isSubmit) {
                    window.location = AP_ROOT + "5001002002/FAM/AR/PaymentList";
             },
       },

        Objects: {
            List : function()
            {
                $("#postForm").ajaxPost(AP_ROOT + "FAM/AR/PaymentObjectList", function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: parseInt($("#TotalCount").val()),
                            pageNo: parseInt($("#PageNo").val()),
                            pageSize: parseInt($("#PageSize").val()),
                            callBack: payment.Payment.Objects.List,
                            callBackArgs: null
                        });

                        var totalCount = parseInt($("#TotalCount").val());

                        if (totalCount > 0) {
                            $("tfoot", "#tblARObjectList").show();
                            $(".simple-grid-none-data-wrap").hide();
                        } else {
                    window.location = AP_ROOT + "5001002002/FAM/AR/PaymentList";
                            $(".simple-grid-none-data-wrap").show();
                        }

                        $.closeLoading();
                    }
                }, true);
            },

            AppliedList: function () {
                $("#postForm").ajaxPost(AP_ROOT + "FAM/AR/PaymentObjectAppliedList", function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: parseInt($("#TotalCount").val()),
                            pageNo: parseInt($("#PageNo").val()),
                            pageSize: parseInt($("#PageSize").val()),
                            callBack: payment.Payment.Objects.AppliedList,
                            callBackArgs: null
                        });

                        var totalCount = parseInt($("#TotalCount").val());

                        if (totalCount > 0) {
                            $("tfoot", "#tblARObjectList").show();
                            $(".simple-grid-none-data-wrap").hide();
                        } else {
                            $("tfoot", "#tblARObjectList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }

                        $.closeLoading();
                    }
                }, true);
            },

            ObjectItem: {
                Selected: function (e) {
                    if ($(e).attr("checked") == "checked") {
                        $.checkbox.all("chkCaseFeeId");
                    } else {
                        $.checkbox.not("chkCaseFeeId");
                    }
                },

                Apply: function (e) {
                    var caseFeePayAmount = $(e).parents("tr").find("#item_CaseFeePayAmount");
                    if ($(e).attr("checked") == "checked") {
                        $(caseFeePayAmount).val($(caseFeePayAmount).attr("casefeeuncashedamount") == undefined ? "0" : $(caseFeePayAmount).attr("casefeeuncashedamount"));
                     } else {
                        $(caseFeePayAmount).val(0);
                     }
                }
            }
        },

        //生成单据号
        GenerateInvoiceNo : function()
        {
            var date = new Date().Format("yyMMdd");
            var r = parseInt(Math.random() * (99999 - 10000 + 1) + 10000, 10);

            return date + "-" + r;
        },
 
    },

                var url =  AP_ROOT + AP_PAGE_ID + "/FAM/PaymentType/PaymentTypeList";
      
        //登记
      PaymentList: function() {
          $("#postForm").ajaxPost(AP_ROOT + "FAM/ReceivedPayment/PaymentList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.PaymentList, function (i, c) {
                            $("tbody", "#tblPaymentList").addRow(
                                "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Edit(\"" + c.PaymentBasic.PaymentId + "\")'>编辑</a> &nbsp; ",
                                c.PaymentBasic.SequenceNo,
                                c.PaymentBasic.ContractNo,
                                c.PaymentBasic.CustomerName,
                                c.PaymentBasic.PayerName,
                                c.PaymentBasic.RegistrantName,
                                c.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.CashedDate)),
                                c.PaymentBasic.CashedAmount,
                                c.PaymentBasic.AppliedAmount,
                                c.PaymentBasic.UnAppliedAmount,
                                c.PaymentBasic.PaymentModeName,
                                c.PaymentBasic.InvoiceNo
                            );
                        });

                        $("tfoot", "#tblPaymentList").show();
                        $(".simple-grid-none-data-wrap").hide();

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/FAM/PaymentType/PaymentTypes", null, function (response) {
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: payment.List.PaymentList,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblPaymentList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
      },
        //公海领取
      PaymentPublicList: function () {
          $("#postForm").ajaxPost(AP_ROOT + "FAM/ReceivedPayment/PaymentPublicList", function (response) {
              if (response.IsSuccess) {
                  $("tbody", "#tblPaymentList").clearRow();
                  if (response.Data.TotalItemCount > 0) {
                      $(".info_inall.layoutfix").show();
                      $.each(response.Data.PaymentList, function (i, c) {
                          $("tbody", "#tblPaymentList").addRow(
                              "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Push(\"" + c.PaymentBasic.PaymentId + "\")'>领取</a> &nbsp; ",
                              c.PaymentBasic.SequenceNo,
                              c.PaymentBasic.ContractNo,
                              c.PaymentBasic.CustomerName,
                              c.PaymentBasic.PayerName,
                              c.PaymentBasic.RegistrantName,
                              c.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.CashedDate)),
                              c.PaymentBasic.CashedAmount,
                              c.PaymentBasic.AppliedAmount,
                              c.PaymentBasic.UnAppliedAmount,
                              c.PaymentBasic.PaymentModeName,
                              c.PaymentBasic.InvoiceNo
                          );
                      });

                      $("tfoot", "#tblPaymentList").show();
                      $(".simple-grid-none-data-wrap").hide();

                      $(".pull-right.page-box.paymentList").cPaging({
                          totalCount: response.Data.TotalItemCount,
                          pageNo: response.Data.PageNo,
                          pageSize: response.Data.PageSize,
                          callBack: payment.List.PaymentList,
                          callBackArgs: null
                      });
                  } else {
                      $("tfoot", "#tblPaymentList").hide();
                      $(".simple-grid-none-data-wrap").show();
                  }
              }
          });
      },
        //待分配
      PaymentApplyList: function () {
          $("#postForm").ajaxPost(AP_ROOT + "FAM/ReceivedPayment/PaymentApplyList", function (response) {
                if ($(e).length > 0) {
                    $("#Payment_PaymentType_PaymentTypeId").val($(e).val());
                    $("#Payment_PaymentType_PaymentTypeName").val($(e).attr("paymenttypername"));
                    $("#Payment_PaymentType_OrganizationName").val($(e).attr("organizationname"));
                    $("#Payment_PaymentType_Account").val($(e).attr("account"));
                }

                payment.Payment.PaymentType.Close();
            }
        },
    },

    List: {
      PaymentList: function() {
            $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentList", function (response) {
              if (response.IsSuccess) {
                  $("tbody", "#tblPaymentList").clearRow();
                  if (response.Data.TotalItemCount > 0) {
                      $(".info_inall.layoutfix").show();


                        $.each(response.Data.PaymentList, function (i, c) {
                            var operatorHtml = 
                              "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Apply(\"" + c.PaymentBasic.PaymentId + "\")'>分配</a> &nbsp; "
                                "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Edit(\"" + c.PaymentBasic.PaymentId + "\")'>编辑</a> &nbsp; ";

                            if ($("#SearchCondition_PageId").val() == '5001002002') {
                                  operatorHtml = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.View(\"" + c.PaymentBasic.PaymentId + "\")'>查看</a> &nbsp; ";
                            }

                            $("tbody", "#tblPaymentList").addRow(
                                operatorHtml,                       
                              c.PaymentBasic.SequenceNo,
                              c.PaymentBasic.ContractNo,
                              c.PaymentBasic.CustomerName,
                              c.PaymentBasic.PayerName,
                              c.PaymentBasic.RegistrantName,
                              c.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.CashedDate)),
                              c.PaymentBasic.CashedAmount,
                              c.PaymentBasic.AppliedAmount,
                              c.PaymentBasic.UnAppliedAmount,
                              c.PaymentBasic.PaymentModeName,
                              c.PaymentBasic.InvoiceNo
                          );
                      });

                      $("tfoot", "#tblPaymentList").show();
                      $(".simple-grid-none-data-wrap").hide();

                      $(".pull-right.page-box.paymentList").cPaging({
                          totalCount: response.Data.TotalItemCount,
                          pageNo: response.Data.PageNo,
                          pageSize: response.Data.PageSize,
                          callBack: payment.List.PaymentList,
                          callBackArgs: null
                      });
                  } else {
                      $("tfoot", "#tblPaymentList").hide();
                      $(".simple-grid-none-data-wrap").show();
                  }
              }
          });
      },
    }
}

var contract = {
    List: {
        ContractList: function () {
            $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/FCM/Contract/List", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            $("tbody", "#tblContractList").addRow(
                                "<a href='javascript:void(0);' onclick='javascript:payment.Payment.Create(" + c.ContractBasicInfo.ContractId + ")'>新增回款</a>&nbsp;&nbsp;",
                                c.ContractBasicInfo.ContractNo,
                                c.ContractBasicInfo.ContractName,
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.TotalAmount,
                                c.ContractBasicInfo.CashedAmount,
                                c.ContractBasicInfo.ARAmount,
                                c.ContractBasicInfo.BusinessOwnerName,
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.CustomerNo,
                                c.ContractBasicInfo.CustomerName
                            );
                        });

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.List.ContractList,
                            callBackArgs: null
                        });


                    } else {
                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
    }
}

$(document).ready(function () {
    $(window).resize(function () {
        payment.ResetSize();
    });

    payment.ResetSize();

    $(document).click(function () {
        $("#divUserList").die().hide();
        $("#divPaymentTypeList").die().hide();
        $("#divAssociateUserList").die().hide();
        $("#divCasePhaseCheckBoxList").die().hide();
        $("#divCaseTypeCheckBoxList").die().hide();
        $("#divCaseFeeTypeCheckBoxList").die().hide();
    });

    var businessOwner = new AssociateUser(
        $("#divAssociateUserList"),
        $("#SearchCondition_BusinessOwner"),
        $("#SearchCondition_BusinessOwnerName"),
        null
    );

    var customter = new AssociateCustomer(
        $("#div_customer"),
        $("#Payment_PaymentBasic_CustomerNo"),
        $("#Payment_PaymentBasic_PayerName"),
        $("#Payment_PaymentBasic_CustomerName")
    );

    var customter = new AssociateCustomer(
        $("#div_customer"),
        $("#Payment_PaymentBasic_CustomerNo"),
        $("#Payment_PaymentBasic_CustomerName"),
        $("#Payment_PaymentBasic_CustomerName")
    );

    $("#divPaymentTypeList").find("li").die().live("click", function () {
        var paymentTypeName = $(this).find("a").attr("name");
        var paymentTypeId = $(this).find("a").attr("paymenttypeid");
        var currentSelectedControl = $("#hidPaymentTypeName").val();
        var currentSelectedControlId = $("#hidPaymentTypeId").val();

        $("#" + currentSelectedControl).val(paymentTypeName);
        $("#" + currentSelectedControlId).val(paymentTypeId);

        $("#divPaymentTypeList").hide();
    });

    $("#Payment_PaymentBasic_PaymentModeName").die().live("click", function () {
        $("#hidPaymentTypeName").val("Payment_PaymentBasic_PaymentModeName");
        $("#hidPaymentTypeId").val("Payment_PaymentBasic_PaymentMode");
        
        $("#divPaymentTypeList").die().css({
            "position": "absolute",
            "left": $("#Payment_PaymentBasic_PaymentModeName").parents().position().left + 0,
            "top": $("#Payment_PaymentBasic_PaymentModeName").parents().position().top + 30,
            "z-index": 1200
        }).show();
        return false;
    });

    $("#SearchCondition_BusinessOwnerName").die().live("click", function () {
        $("#hidUserId").val("SearchCondition_BusinessOwner");
        $("#hidUserName").val("SearchCondition_BusinessOwnerName");
        $("#divUserList").css({
            "position": "absolute",
            "left": $("#SearchCondition_BusinessOwnerName").position().left + 16,
            "top": $("#SearchCondition_BusinessOwnerName").position().top + 70,
            "z-index": 1200
        }).toggle();
        return false;
    });

    $("#divUserList").find("li").die().live("click", function (e) {
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();
        if ($(this).attr("id") == 'btnClear') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        $("#" + currentSelectedControl).val(userName);
        $("#" + currentSelectedIdControl).val(userId);
        $("#divUserList").hide();
        return false;
    });

    $("#divPaymentTypeList").find("li").die().live("click", function () {
        var paymentTypeName = $(this).find("a").attr("name");
        var currentSelectedControl = $("#hidPaymentTypeName").val();
        $("#" + currentSelectedControl).val(paymentTypeName);
        $("#divPaymentTypeList").hide();
    });

    $("#Payment_PaymentBasic_PaymentModeName").die().live("click", function () {
        $("#hidPaymentTypeName").val("Payment_PaymentBasic_PaymentModeName");
        $("#divPaymentTypeList").die().css({
            "position": "absolute",
            "left": $("#Payment_PaymentBasic_PaymentModeName").position().left + 1,
            "top": $("#Payment_PaymentBasic_PaymentModeName").position().top + 28,
            "z-index": 1200
        }).show();
        return false;
    });

    $("#lblPaymentType").die().live("click", function () {
        payment.Payment.PaymentType.Open();
    });

    $("#lblInvoiceNo").die().live("click", function () {

        if ($("#Payment_PaymentBasic_InvoiceNo").val() == '')
        {
            var invoiceNo = payment.Payment.GenerateInvoiceNo();
            $("#Payment_PaymentBasic_InvoiceNo").val(invoiceNo);
        }
    });

    $("#btnPaymentTypeCancel,#btnPaymentTypeClose").die().live("click", function () {
        payment.Payment.PaymentType.Close();
    });
    
    $("#btnPaymentTypeSelected").die().live("click", function () {
        payment.Payment.PaymentType.Selected();
    });

    $("input[name='chkPaymentTypeId']").die().live("click", function () {
        payment.Payment.PaymentType.Select(this);
    });

    $("input[name='item_PaymentApply']").die().live("click", function () {
        payment.Payment.Objects.ObjectItem.Apply(this);
        payment.Payment.TotalAmountSet();
    });

    $("#Payment_PaymentBasic_PrePaidAmount").die().live("change", function () {

        if ($(this).val() == '') {
            $(this).val(0);
        }

        var prePaidAmount = parseFloat($("#Customer_CustomerBasic_PrePaidAmount").attr("prepaidamount")) + parseFloat($("#Payment_PaymentBasic_PrePaidAmount").val());
        $("#Customer_CustomerBasic_PrePaidAmount").val(prePaidAmount);

        payment.Payment.TotalAmountSet();
    });
 
    $("#btnPaymentListSearch").die().live("click", function () {
        payment.List.PaymentList();
    });
    $("#btnPaymentPublicListSearch").die().live("click", function () {
        payment.List.PaymentPublicList();
    });
    $("#btnPaymentApplyListSearch").die().live("click", function () {
        payment.List.PaymentApplyList();
    });

    $("#btnPaymentObjectSearch").die().live("click", function () {
        payment.Payment.Objects.List();
    });

    $("#btnPaymentObjectAppliedSearch").die().live("click", function () {
        payment.Payment.Objects.AppliedList();
    });

    $("#btnPaymentCreateUpdate").die().live("click", function () {
        payment.Payment.Registration.CreateUpdate(false);
    });

    $("#btnPaymentCreateAndNextOne").die().live("click", function () {
        payment.Payment.Registration.CreateUpdate(true);
    });

    $("#btnPaymentPush").die().live("click", function () {
        payment.Payment.Registration.Push();
    });

    $("#chkCaseFeeAll").die().live("click", function () {
        payment.Payment.Objects.ObjectItem.Selected(this);
    });
     
    $("#SearchCondition_CasePhaseName").die().live("click", function () {
        var tirgger = this;
        var html = $.lsCasePhase.getCasePhaseCheckBoxListHtml();
        $(".divcaseconditioncasephases").html(html);
        $("#hidCasePhaseId").val("SearchCondition_CasePhaseId");
        $("#hidCasePhaseName").val("SearchCondition_CasePhaseName");
        $("#divCasePhaseCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 0,
            "top": $(tirgger).position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
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
        payment.Payment.TotalAmountSet();
    });

        $("#" + currentSelectedControl).val(casePhaseNames.substring(0, casePhaseNames.length - 1));
        $("#" + currentSelectedIdControl).val(casePhaseIds.substring(0, casePhaseIds.length - 1));

        e.stopPropagation();

        return true;
    });
    $("#SearchCondition_CaseTypeName").die().live("click", function () {
        var tirgger = this;
        var html = $.lsCaseType.getCaseTypeCheckBoxListHtml();
        $(".divcaseconditioncasetypes").html(html);
        $("#hidCaseTypeId").val("SearchCondition_CaseTypeId");
        $("#hidCaseTypeName").val($(tirgger).attr("id"));
        $("#divCaseTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 0,
            "top": $(tirgger).position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
    });
    $("#divCaseTypeCheckBoxList").find("li").die().live("click", function (e) {

        if ($(e.target).is("lable")) {
            e.stopPropagation();
            return false;
        }

        var currentSelectedControl = $("#hidCaseTypeName").val();
        var currentSelectedIdControl = $("#hidCaseTypeId").val();

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

        var caseTypeNames = '';
        var caseTypeIds = '';

        $("#divCaseTypeCheckBoxList").find("input:checkbox").each(function () {
            if ($(this).attr("checked") == 'checked') {
                caseTypeNames += $(this).attr("casetypename") + ",";
                caseTypeIds += $(this).attr("casetypeid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(caseTypeNames.substring(0, caseTypeNames.length - 1));
        $("#" + currentSelectedIdControl).val(caseTypeIds.substring(0, caseTypeIds.length - 1));

        e.stopPropagation();

        return true;
    });
    $("#divCaseFeeTypeCheckBoxList").find("li").die().live("click", function (e) {

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
    $("#SearchCondition_CaseFeeTypeName").die().live("click", function () {
        var tirgger = this;
        var html = $.lsCaseFeeType.getCaseFeeTypeCheckBoxListHtml();
        $(".divcaseconditioncasefeetypes").html(html);
        $("#hidCaseFeeTypeId").val("SearchCondition_CaseFeeTypeId");
        $("#hidCaseFeeTypeName").val($(tirgger).attr("id"));
        $("#divCaseFeeTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 0,
            "top": $(tirgger).position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $("#btnPaymentApply").die().live("click", function () {
        payment.Payment.PaymentApply();
    });

    $("#btnPaymentAppliedCancel").die().live("click", function () {
        payment.Payment.PaymentAppliedCancel();
    });

    $("#btnPaymentSearchClear").die().live("click", function () {
        $("#SearchCondition_CustomerName").val('');
        $("#SearchCondition_ContractNo").val('');
        $("#SearchCondition_CaseNo").val('');
        $("#SearchCondition_CaseTypeName").val('');
        $("#SearchCondition_CaseTypeId").val('');
        $("#SearchCondition_CasePhaseName").val('');
        $("#SearchCondition_CasePhaseId").val('');
        $("#SearchCondition_CaseFeeTypeName").val('');
        $("#SearchCondition_CaseFeeTypeId").val('');
    });

});