$(document).ready(function () {
    $("#btnUploadingLicense").click(function () {
        var url =  AP_ROOT + AP_PAGE_ID + "/CRM/Customer/UploadingLicense";
        $('.uploadingLicense').load(url, function (result) {
            $('#uploadingLicenseModal').modal({ backdrop: 'static', keyboard: false });
        });
    });

    $("#btnCancle").click(function() {
        $('#myModal').modal('hide');
    });

    $("#btnClose").click(function() {
        $('#myModal').modal('hide');
    });

    $("#btnCreateUpdate").click(function () {
        if (!postValid()) {
            return false;
        }
        $("#contactListAddForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CreateUpdate", function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                //window.location =  AP_ROOT + AP_PAGE_ID + "/InternalFlight/Edit/" + response.Data;
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });
    });
});

function postValid() {

    //if (!CheckModifyTime()) return false;

    //判断必填项的项是否填写
    var flag = true;
    $("#tblCustomer :text").each(function () {
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

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IntlFare/ValidAssociate", data, function (response) {
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
    return true;
}


//<div style="display: ; position: absolute; width: 180px; top: 28px; left: 57px;" class="ac_results"><ul style="max-height: 180px; overflow: auto;"><li class="ac_even">BI<strong>PKG</strong>ReportDB</li><li class="ac_odd">DIYRef<strong>Pkg</strong>CommentDB</li><li class="ac_even">DIYRef<strong>Pkg</strong>ControlDB</li><li class="ac_odd">diyref<strong>pkg</strong>productdb</li><li class="ac_even">HH<strong>Pkg</strong>DB</li><li class="ac_odd"><strong>Pkg</strong>AnalysisDB</li><li class="ac_even"><strong>Pkg</strong>BizLogDB</li><li class="ac_odd"><strong>Pkg</strong>CommunicationDB</li><li class="ac_even"><strong>Pkg</strong>ControlDB</li><li class="ac_odd"><strong>Pkg</strong>InputDB</li><li class="ac_even"><strong>Pkg</strong>InsBizLogDB</li><li class="ac_odd"><strong>Pkg</strong>InterfaceDB</li><li class="ac_even"><strong>Pkg</strong>InvoiceDB</li><li class="ac_odd"><strong>Pkg</strong>InvoiceLogDB</li><li class="ac_even"><strong>pkg</strong>MessageBakDB</li><li class="ac_odd"><strong>pkg</strong>MessageDB</li><li class="ac_even"><strong>Pkg</strong>MyOrderControlDB</li><li class="ac_odd"><strong>Pkg</strong>MyOrderLogDB</li><li class="ac_even"><strong>Pkg</strong>OnlineDB</li><li class="ac_odd"><strong>Pkg</strong>OnlineOrderDB</li><li class="ac_even"><strong>Pkg</strong>OrderbakDB</li><li class="ac_odd"><strong>Pkg</strong>OrderDB</li><li class="ac_even"><strong>Pkg</strong>OrderDB_DelOutPut</li><li class="ac_odd"><strong>Pkg</strong>orderIDDB</li><li class="ac_even"><strong>Pkg</strong>OrderTrackDB</li><li class="ac_odd"><strong>Pkg</strong>ProductDB</li><li class="ac_even"><strong>Pkg</strong>ProductLogDB</li><li class="ac_odd"><strong>Pkg</strong>ProductMetaDB</li><li class="ac_even"><strong>Pkg</strong>PromotionDB</li><li class="ac_odd"><strong>Pkg</strong>PubDB</li><li class="ac_even"><strong>Pkg</strong>RealDB</li><li class="ac_odd"><strong>Pkg</strong>RealSourceDB</li><li class="ac_even"><strong>Pkg</strong>ReplDB</li><li class="ac_odd"><strong>Pkg</strong>SettlementDB</li><li class="ac_even"><strong>Pkg</strong>SupportDB</li><li class="ac_odd"><strong>Pkg</strong>TourDB</li></ul></div>







