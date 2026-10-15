/*案件类型*/
var casePhase = {
    List: function () {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CasePahseList", function (response) {
            
            if (response.IsSuccess) {
                $("tbody", "#tblCasePhaseList").clearRow();
                if (response.Data.TotalItemCount > 0) {

                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CasePhases, function (i, c) {
                        
                        $("tbody", "#tblCasePhaseList").addRow(c.CasePhaseId, c.CasePhaseName,
                                        "<a href='javascript:void(0)' onclick='javascript:casePhase.Open(" + c.CasePhaseId + ")'>修改</a>");

                    });
                    
                    $("tfoot", "#tblCasePhaseList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.casephase").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: casePhase.List,
                        callBackArgs: null
                    });
                } else {
                    
                    $("tfoot", "#tblCasePhaseList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    Close: function () {
        $('#CasePhaseModal').modal('hide');
    },

    /*创建案件阶段*/
    Open: function (casePahseId) {
        var data = {
            casePhaseId: casePahseId,
        }

        var url =  AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CasePhase";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#CasePhaseModal').modal({ backdrop: 'static', keyboard: false });
            $('#CasePhaseModal').on('hidden.bs.modal', function () {
                $("#CasePhaseModal").remove();
            });
        });

        //$('.casephase').load(url,data, function (result) {
        //    $.closeLoading();
        //    $('#CasePhaseModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },
  

    /* 保存 阶段名称*/
    CreateUpdate: function () {

        if ($("#CasePhase_CasePhaseName").val() == '') {
            $.showModalMessageBox("请输入阶段名称.");
            return false;
        }

        $("#CasePhase").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CasePhaseCreateUpdate", function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                $('#CasePhaseModal').modal('hide');
                casePhase.List();
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });
    }
}

$(document).ready(function () {

    //casePhase.List();

    $(document).off('click', '#btnCasePhase').on('click', '#btnCasePhase', function () {
        casePhase.CreateUpdate();
    });

    $(document).off('click', '.CasePhaseCreate').on('click', '.CasePhaseCreate', function () {
        casePhase.Open();
    });

    $(document).off('click', '#btnCasePhaseCreate').on('click', '#btnCasePhaseCreate', function () {
        casePhase.Open();
    });

    $(document).off('click', '#btnCasePhaseClose').on('click', '#btnCasePhaseClose', function () {
        casePhase.Close();
    });

    $(document).off('click', '#btnCasePhaseCancel').on('click', '#btnCasePhaseCancel', function () {
        casePhase.Close();
    });

    $(document).off('click', '#btnCasePhaseSearch').on('click', '#btnCasePhaseSearch', function () {
        casePhase.List();
    });

});


