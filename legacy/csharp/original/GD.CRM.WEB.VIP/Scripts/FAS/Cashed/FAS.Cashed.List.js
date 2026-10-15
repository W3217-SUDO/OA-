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
                        html += '<a href="javascript:void(0)" customerno=' + c.CustomerNo + ' >' + c.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("customerno"));
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
            "top": $(ctlname).position().top + 110,
            "z-index": 9999
        }).show();
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

var cashed = {

    /*到账信息*/
    Cashed: {
        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + "FAM/Cashed/List", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCashedList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.CashedList, function (i, c) {
                            $("tbody", "#tblCashedList").addRow(
                            c.CustomerNo,
                            c.CustomerName,
                            c.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.CashedDate)),
                            c.Amount,
                            c.PaymentModeName,
                            c.BillNo,
                             c.Remark,
                            "<a href='javascript:void(0)'; onclick='javascript:cashed.Cashed.Delete(" + c.CashedId + ");'>删除</a>"
                            );
                        });

                        $("tfoot", "#tblCashedList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.cashedlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: cashed.Cashed.List,
                            callBackArgs: null
                        });
                    } else {

                        $("tfoot", "#tblCashedList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },

        Delete: function (cashedId) {

            var data = {
                cashedId: cashedId,
            };

            $.ajaxPost(AP_ROOT + "FAM/Cashed/CashedDelete", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("删除成功.");
                    cashed.Cashed.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        }
    },

    /*登记到账*/
    CashedRegister: {
        Open: function() {
            var url = AP_ROOT + "FAM/Cashed/Register";
            var data = {};

            $.openLoading();
           
            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#cashedRegisterModal').modal({ backdrop: 'static', keyboard: false });
                $('#cashedRegisterModal').on('hidden.bs.modal', function () {
                    $("#cashedRegisterModal").remove();
                });

                //var caseFileType = new AssociateCaseFileType(
                //    $("#div_CaseFileTypeList"),
                //    $("#CaseFileTypeId"),
                //    $("#CaseFileTypeName"),
                //    $("#Case_CaseBasicInfo_CaseTypeId").val(),
                //    $("#IsTransformedFile").val() == 'true',
                //    caseInfo.CaseFile.ProcessFileTypeSelectedCallBack
                //);
            });
        },
        Close: function() {
            $('#cashedRegisterModal').modal('hide');
        },
    },
};
 

$(document).ready(function() {

    $(document).click(function() {

    });

    $("#btnCashedRegister").click(function () {
        cashed.CashedRegister.Open();
    });
 
    $("#btnSearch").die().live("click", function () {
        cashed.Cashed.List();
    });

});