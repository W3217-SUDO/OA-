$(document).ready(function () {
    investigation.Investigations.List();


    $(document).off('click', '#btnInvestigationListEdit').on('click', '#btnInvestigationListEdit', function () {
        /*列表选中修改*/
        var investigationNos = $.checkbox.vals("chkInvestigationId");
        if (investigationNos.length == 0) {
            $.showModalMessageBox("请选择调查任务.");
            return false;
        }
        var investigationNo = investigationNos[0];
        investigation.Investigations.Investigation.Edit(investigationNo);
    });
    $(document).off('click', '#btnInvestigationListFileCreate').on('click', '#btnInvestigationListFileCreate', function () {
        var investigationNos = $.checkbox.vals("chkInvestigationId");
        if (investigationNos.length == 0) {
            $.showModalMessageBox("请选择调查任务.");
            return false;
        }

        var investigationGuids = [];
        $("input[name=chkInvestigationId]:checked").each(
            function (i) {
                investigationGuids[i] = $(this).attr("investigationguid");
            }
        );
        var investigationGuid = investigationGuids[0];
        investigation.Investigations.Investigation.Files.File.Open(investigationGuid);
    });

    $(document).off('click', '#btnInvestigationListTaskCreate').on('click', '#btnInvestigationListTaskCreate', function () {
        /*列表选中修改*/
        var investigationNos = $.checkbox.vals("chkInvestigationId");
        if (investigationNos.length == 0) {
            $.showModalMessageBox("请选择调查任务.");
            return false;
        }
        var investigationNo = investigationNos[0];
        var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationTask/Create?InvestigationNo=" + investigationNo;

        window.open(url, 'InvestigationTask');
    });

});
